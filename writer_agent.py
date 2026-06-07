import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
from prompt_lib import WORLD_VIEW_PROMPTS, STYLE_PROMPTS, calculate_drive_prompt, calculate_action_prompt

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), 
    base_url=os.getenv("DEEPSEEK_BASE_URL")
)

def auto_detect_config(novel_text):
    """
    真正的智能侦测：通过 LLM 分析小说文本，返回最匹配的基础世界观和附加滤镜。
    """
    print("[Auto Detect] 正在启动 AI 智能侦测世界观与风格...")
    
    sample_text = novel_text[:2000]
    
    valid_worlds = list(WORLD_VIEW_PROMPTS.keys())
    valid_styles = list(STYLE_PROMPTS.keys())
    
    prompt = f"""你是一个专业的影视剧本评估专家。请阅读以下小说片段，并为其匹配最合适的世界观和风格。

可选的世界观列表：{valid_worlds}
可选的风格列表：{valid_styles}

请严格以纯 JSON 格式输出，不要包含任何 markdown 代码块或其他解释性文字。格式如下：
{{
  "world": "选出的世界观",
  "style": "选出的风格"
}}

小说片段：
{sample_text}
"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 
        )
        
        result = response.choices[0].message.content.strip()
        result = result.replace("```json", "").replace("```", "").strip()
        detected_data = json.loads(result)
        
        world = detected_data.get("world", "仙侠")
        style = detected_data.get("style", "传统正剧")
        
        if world not in valid_worlds:
            world = "仙侠"
        if style not in valid_styles:
            style = "传统正剧"
            
        print(f"[Auto Detect] 侦测完成 -> 世界观: {world}, 风格: {style}")
        return world, style
        
    except Exception as e:
        print(f"[Error] 智能侦测失败，使用默认配置: {str(e)}")
        return "仙侠", "传统正剧"


SCHEMA_MOVIE = """
- 章节标题: string
  元数据: {类型: string, 基调: string}
  场景列表:
    - 场景编号: integer
      场景标题: string
      环境氛围: string
      节奏要求: string
      出场角色: array
      分镜序列:
        - 镜头规格: string
          运镜指令: string
          动作描写: string
          对话内容: "string"
          音效提示: string
          光影指令: string
"""

SCHEMA_TV = """
- 章节标题: string
  元数据: {类型: string, 基调: string}
  场景列表:
    - 场景编号: integer
      场景标题: string
      场景时间: string
      环境氛围: string
      人物出场: array
      剧本正文:
        - 动作: string
        - 台词: {角色: string, 语气: string, 内容: string}
        - 动作: string
        - OS: {角色: string, 内容: string}
"""

def generate_script(novel_text, world_tag, style_tag, drive_slider, action_slider, enable_custom, mode="movie"):
    if not enable_custom:
        from writer_agent import auto_detect_config
        world_tag, style_tag = auto_detect_config(novel_text)
        drive_slider, action_slider = 5.0, 5.0
    
    final_config = {"world": world_tag, "style": style_tag, "drive": drive_slider, "action": action_slider}
    
    if mode == "tv":
        mode_instruction = f"""
【电视剧文学剧本模式】
你是一名专注长线叙事的电视剧编剧。你的剧本必须严格按照时间顺序，将动作与台词交织在一起。
1. 序列化叙事：在“剧本正文”中，必须使用数组列表（- 动作: / - 台词: / - OS:）来表现剧情的先后顺序。动作和台词要交替出现。
2. 台词结构化：台词必须拆分为独立的对象，包含“角色”、“语气”（可选，如：冷笑、叹气）和“内容”。
3. 文学描写：动作描写必须融入人物情绪（例如：不仅写“下雨”，要写“雨水淋湿了韩立那件发白的旧棉袄，也冲刷着他心头那份不安”）。
4. 结构模板：{SCHEMA_TV}
"""
    else:
        mode_instruction = f"""
【电影工业级分镜模式】
你是一名追求极致视听效果的电影导演。你的剧本必须精确到每一个镜头的物理控制。
1. 镜头拆解：严格遵循镜头规格（全/中/近/特）、运镜逻辑（推/拉/摇/移）和光影布局。
2. 物理动作：动作描写必须是可见的动作，严禁出现心理描写，通过动作和微表情表现人物内心。
3. 视听沉浸：音效和光影指令必须具备电影质感（例如：光影不仅仅是亮暗，而是“冷色调侧逆光勾勒人物轮廓”）。
4. 结构模板：{SCHEMA_MOVIE}
"""

    
    system_instruction = f"""你是一名顶级编剧。请将小说章节转换为结构化剧本。

【编剧法则】
- [冲突原则]：没有冲突的戏，就是无用的戏。每场戏必须明确“主角的目的”和“当前的障碍”。
- [潜台词法则]：人物的话永远不要直接说透，要通过动作、眼神或反讽来表现。
- [动态排版]：每个场景之间必须空出一行，方便审阅。

【设定】
1. 世界观：{WORLD_VIEW_PROMPTS.get(world_tag, "")}
2. 风格：{STYLE_PROMPTS.get(style_tag, "")}
3. {calculate_drive_prompt(drive_slider)}
4. {calculate_action_prompt(action_slider)}

【强制规范】
{mode_instruction}
1. YAML 键值对分隔符必须使用【英文半角冒号加空格】(: )。
2. 对话必须使用双引号包裹，内部引用用中文单引号（例如：对话内容: "食客甲: ‘老韩，谁？’"）。
3. 禁止输出 Markdown 符号 (如 ```yaml)。
"""
    
    raw_chunks = re.split(r'(?=--- 第.+?章)', novel_text)
    chapters = [c.strip() for c in raw_chunks if c.strip()]
    combined_yaml = "剧本内容:\n"
    
    def process_single_chapter(index, chapter_content):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": chapter_content}],
                temperature=0.2, max_tokens=4000
            )
            result = response.choices[0].message.content.replace("```yaml", "").replace("```", "").strip()
            result = re.sub(r'\n(\s*-\s*场景编号:)', r'\n\n\1', result)
            indented = "\n".join(["  " + line for line in result.split("\n")])
            return index, indented + "\n\n\n"
        except Exception as e:
            return index, f"  # [Error] 编译失败: {str(e)}\n\n"

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_single_chapter, i, chap): i for i, chap in enumerate(chapters)}
        results = sorted([f.result() for f in as_completed(futures)], key=lambda x: x[0])
    
    for _, yaml_part in results:
        combined_yaml += yaml_part
        
    return combined_yaml.strip(), final_config