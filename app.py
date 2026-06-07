import gradio as gr
import time
import datetime
import os
import glob
from omni_parser import route_and_parse
from smart_sorter import sort_and_merge_chunks
from writer_agent import generate_script

def get_history_files():
    files = glob.glob("script_*.yaml")
    files.sort(reverse=True, key=os.path.getmtime)
    return files

def load_history_content(filepath):
    if not filepath or not os.path.exists(filepath):
        return "", None
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return content, filepath

def force_refresh_history():
    files = get_history_files()
    if files:
        content, path = load_history_content(files[0])
        return gr.Dropdown(choices=files, value=files[0]), content, path
    return gr.Dropdown(choices=[], value=None), "暂无历史记录", None

def process_input(text_content, file_objs, enable_custom, world_tag, style_tag, drive_slider, action_slider, mode):
    
    pen_animation_html = """
    <div class="pen-container">
        <div class="pen-track"></div>
        <div class="pen-icon">✍️</div>
        <div class="pen-text">剧本智能生成中...</div>
    </div>
    """
    yield pen_animation_html, "", None, gr.Dropdown()

    try:
        parsed_chunks = []
        if text_content and text_content.strip():
            parsed_chunks.append({"filename": "text_input", "content": text_content.strip()})

        if file_objs:
            file_data_list = route_and_parse(file_objs)
            parsed_chunks.extend(file_data_list)

        if not parsed_chunks:
            yield "<div class='pen-finish' style='color: red;'>⚠️ 未检测到有效输入文档</div>", "", None, gr.Dropdown()
            return

        combined_text = sort_and_merge_chunks(parsed_chunks)
        
        yaml_result, final_config = generate_script(
            combined_text, 
            world_tag, 
            style_tag, 
            float(drive_slider), 
            float(action_slider), 
            enable_custom,
            mode
        )
        
        
        exec_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"# ==========================================\n"
            f"# AI DramaLens 生成报告\n"
            f"# 时间: {exec_time}\n"
            f"# 模式: {'[自定义配置]' if enable_custom else '[智能侦测]'}\n"
            f"# 世界观: {final_config.get('world', '')}\n"
            f"# 风格: {final_config.get('style', '')}\n"
            f"# 情节比重: {final_config.get('drive', 5.0)}/10 | 动作比重: {final_config.get('action', 5.0)}/10\n"
            f"# ==========================================\n\n"
        )
        final_yaml_content = header + yaml_result
        
        
        timestamp_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_world = str(final_config.get('world', 'default'))
        script_path = f"script_{safe_world}_{timestamp_file}.yaml" 
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(final_yaml_content)
            
        yield "<div class='pen-finish'>✨ 剧本生成完毕</div>", final_yaml_content, script_path, gr.Dropdown(choices=get_history_files(), value=script_path)
    
    except Exception as e:
        yield f"<div class='pen-finish' style='color: red;'>❌ 执行出错: {str(e)}</div>", "", None, gr.Dropdown()

def confirm_settings_action(world, style, drive, action):
    gr.Info(f"配置已锁定：{world} | {style}")
    return "✅ 配置参数已写入引擎。"

custom_css = """
.gradio-container { max-width: 1400px !important; margin: 0 auto !important; }

#main-row, #history-row {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important; 
    gap: 20px !important;
    align-items: stretch !important;
    width: 100% !important;
}

#main-row > *, #history-row > * {
    min-width: 0 !important; 
}

.mod-box {
    border-radius: 12px !important; 
    padding: 20px !important; 
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    box-sizing: border-box !important;
}

#mod-1 { border: 2px solid #3b82f6 !important; background-color: #eff6ff !important; }
#mod-2 { border: 2px solid #10b981 !important; background-color: #ecfdf5 !important; }
#mod-3 { border: 2px solid #8b5cf6 !important; background-color: #f5f3ff !important; }
#mod-4 { border: 2px solid #f59e0b !important; background-color: #fffbeb !important; }
#mod-5 { border: 2px solid #06b6d4 !important; background-color: #ecfeff !important; }

#mod-5 .gradio-textbox, #mod-5 .gr-input { height: 100% !important; flex-grow: 1 !important; }
#mod-5 textarea { height: 100% !important; min-height: 450px !important; }

.pen-container { 
    display: flex; 
    align-items: center; 
    gap: 10px; 
    padding: 15px 10px; 
}
.pen-icon { 
    font-size: 28px; 
    display: inline-block; 
    animation: pen-bounce 0.5s infinite alternate ease-in-out; 
    transform-origin: bottom left; 
}
.pen-text { 
    font-size: 16px; 
    font-weight: bold; 
    color: #f59e0b; 
    animation: text-pulse 1s infinite alternate; 
}
@keyframes pen-bounce {
    0% { transform: translateY(0) rotate(0deg); }
    100% { transform: translateY(-12px) rotate(-25deg); }
}
@keyframes text-pulse {
    0% { opacity: 0.6; }
    100% { opacity: 1; }
}

#mod-3 .gradio-textbox { height: 100% !important; flex-grow: 1 !important; display: flex !important; flex-direction: column !important; }
#mod-3 textarea { height: 100% !important; flex-grow: 1 !important; }
"""

with gr.Blocks(title="AI DramaLens", css=custom_css) as demo:
    gr.HTML("""<h2 style="text-align: center; color: #333; margin-bottom: 20px;">🎬 AI DramaLens 灵镜工厂</h2>""")
    
    with gr.Tabs():
        with gr.Tab("🎛️ 灵镜工厂"):
            with gr.Row(elem_id="main-row"):
                
                
                with gr.Column(scale=1, min_width=0):
                    with gr.Row():
                        with gr.Column(elem_id="mod-1", elem_classes=["mod-box"]):
                            gr.Markdown("### 🗂️ 模块一：文本队列")
                            text_input = gr.Textbox(lines=14, max_lines=25, label="小说正文输入")
                            file_input = gr.File(label="文档上传", file_count="multiple", file_types=[".txt", ".docx", ".pdf", "image"])
                    
                    
                    with gr.Row():
                        with gr.Column(elem_id="mod-2", elem_classes=["mod-box"]):
                            gr.Markdown("### 🎛️ 模块二：参数配置")
                            enable_custom = gr.Checkbox(label="⚙️ 开启自定义配置", value=False)
                            with gr.Accordion("🔧 高级参数板", visible=False, open=True) as advanced_settings:
                                world_tag = gr.Dropdown(choices=["仙侠", "玄幻", "奇幻", "武侠", "都市", "历史", "军事", "游戏", "体育", "科幻", "悬疑", "灵异", "轻小说", "诸天无限", "言情"], label="基础世界观", value="仙侠")
                                style_tag = gr.Dropdown(choices=["传统正剧", "克苏鲁", "轻松搞笑", "抽象玩梗", "虐恋苦情"], label="附加滤镜", value="传统正剧")
                                drive_slider = gr.Slider(minimum=0, maximum=10, value=5.0, step=0.1, label="🔥 情节比重 (低=重情感，高=重事件)")
                                action_slider = gr.Slider(minimum=0, maximum=10, value=5.0, step=0.1, label="⚔️ 动作比重 (低=重文戏，高=重武戏)")
                                confirm_btn = gr.Button("💾 锁定配置", variant="secondary")
                                confirm_status = gr.Markdown("")
                
                with gr.Column(scale=1, min_width=0):
                    with gr.Column(elem_id="mod-3", elem_classes=["mod-box"]):
                        gr.Markdown("### 🖌️ 模块三：剧本生成")
                        with gr.Row():
                            btn_movie = gr.Button("🎬 电影剧本（分镜）", variant="primary")
                            btn_tv = gr.Button("📺 电视剧本（文学）", variant="secondary")
                        
                        mode_state = gr.State("movie") 
                        
                        def select_mode(mode):
                            if mode == "movie":
                                return gr.update(variant="primary"), gr.update(variant="secondary"), "movie"
                            else:
                                return gr.update(variant="secondary"), gr.update(variant="primary"), "tv"

                        btn_movie.click(fn=select_mode, inputs=[gr.State("movie")], outputs=[btn_movie, btn_tv, mode_state])
                        btn_tv.click(fn=select_mode, inputs=[gr.State("tv")], outputs=[btn_movie, btn_tv, mode_state])
                        
                        submit_btn = gr.Button("🖌️ 启动生成", variant="primary", size="lg")
                        download_file = gr.File(label="📥 导出结果", interactive=False)
                        visual_loader = gr.HTML("<div style='height: 60px;'></div>")
                        output_display = gr.Textbox(lines=16, label="终端输出")
                        
        
        with gr.Tab("🗄️ 剧本库"):
            gr.Markdown("### 📂 历史剧本")
            with gr.Row(elem_id="history-row"):
                with gr.Column(scale=1, min_width=0):
                    with gr.Column(elem_id="mod-4", elem_classes=["mod-box"]):
                        gr.Markdown("#### 🔍 检索")
                        history_dropdown = gr.Dropdown(choices=[], label="历史记录", interactive=True)
                        refresh_btn = gr.Button("🔄 刷新列表")
                        history_download = gr.File(label="📥 导出", interactive=False)
                
                with gr.Column(scale=1, min_width=0):
                    with gr.Column(elem_id="mod-5", elem_classes=["mod-box"]):
                        gr.Markdown("#### 📄 预览")
                        history_preview = gr.Textbox(lines=25, label="")

    demo.load(fn=force_refresh_history, inputs=None, outputs=[history_dropdown, history_preview, history_download])
    
    text_input.change(fn=lambda text: gr.update(label=f"小说正文输入 ({len(text)} 字)"), inputs=text_input, outputs=text_input)
    enable_custom.change(fn=lambda is_en: gr.update(visible=is_en), inputs=enable_custom, outputs=advanced_settings)
    confirm_btn.click(fn=confirm_settings_action, inputs=[world_tag, style_tag, drive_slider, action_slider], outputs=confirm_status)
    
    submit_btn.click(
        fn=process_input, 
        inputs=[text_input, file_input, enable_custom, world_tag, style_tag, drive_slider, action_slider, mode_state], 
        outputs=[visual_loader, output_display, download_file, history_dropdown],
        show_progress="hidden" 
    )
    
    refresh_btn.click(fn=force_refresh_history, inputs=None, outputs=[history_dropdown, history_preview, history_download])
    history_dropdown.change(fn=load_history_content, inputs=history_dropdown, outputs=[history_preview, history_download])

if __name__ == "__main__":
    demo.launch(inbrowser=True)