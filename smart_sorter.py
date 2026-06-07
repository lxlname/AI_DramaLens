import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), 
    base_url=os.getenv("DEEPSEEK_BASE_URL")
)

def sort_and_merge_chunks(parsed_chunks):
    if not parsed_chunks:
        return ""
    
    print("[Sorter] 提取语义接口，准备执行硬核拼接...")
    
    chunk_metadata = []
    content_map = {}
    for chunk in parsed_chunks:
        fname = chunk['filename']
        content = chunk['content'].strip()
        content_map[fname] = content
        
        start_text = content[:150].replace('\n', ' ')
        end_text = content[-150:].replace('\n', ' ') if len(content) > 150 else start_text
        
        chunk_metadata.append({
            "filename": fname,
            "start_text": start_text,
            "end_text": end_text
        })
        
    prompt = f"""你是一个高级的文学逻辑拼接引擎。我将提供一组完全打乱的小说文件片段的首尾特征。
任务：
1. 寻找语义断点：分析哪个片段的 end_text 能和另一个片段的 start_text 在语义上完美接续（例如半句话断开，或者动作连贯）。
2. 识别章节起始：部分片段的 start_text 会明确标有“第X章”，这是新章节的锚点。
3. 全局排序：将那些没有章节号的残页（如图片OCR文本），依据上下文情节，正确地插入到对应的章节序列中。

必须严格以纯 JSON 数组格式输出，不要包含任何 markdown 代码块！格式如下：
[
  {{
    "chapter_title": "第X章", 
    "filenames": ["带有第X章标题的文件.txt", "接续的残页1.png", "接续的残页2.jpg"]
  }}
]

待拼接的碎片数据：
{json.dumps(chunk_metadata, ensure_ascii=False, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        result = result.replace("```json", "").replace("```", "").strip()
        sorted_plan = json.loads(result)
        
        merged_text = []
        for chapter in sorted_plan:
            title = chapter.get("chapter_title", "未知章节")

            merged_text.append(f"\n\n--- {title} ---\n\n")
            
            for fname in chapter.get("filenames", []):
                if fname in content_map:
                    merged_text.append(content_map[fname])
                    merged_text.append("\n")
                    
        print("[Sorter] 语义拼接完成，文本已熔接！")
        return "".join(merged_text)
        
    except Exception as e:
        print(f"[Error] 语义拼接失败: {str(e)}")
        return "\n\n--- 未知章节 ---\n\n".join([c['content'] for c in parsed_chunks])