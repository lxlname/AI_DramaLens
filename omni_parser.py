import os
import fitz
import docx
import base64
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"), 
    base_url=os.getenv("QWEN_BASE_URL")
)

def extract_txt(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gbk", errors="ignore") as f:
            return f.read()

def extract_docx(file_path):
    doc = docx.Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)

def extract_pdf(file_path):
    text = ""
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except Exception as e:
        print(f"[Error] PDF 解析失败: {e}")
    return text

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_image_vlm(file_path):
    try:
        base64_image = encode_image(file_path)
        response = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "你是一个精准的文字提取（OCR）引擎。请提取图片中的所有小说正文。要求：1. 只输出原文内容，不要添加总结、解释或客套话。2. 保持原有的段落换行。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.01,
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error] 图片视觉提取失败: {str(e)}"

def process_single_file(file_obj):
    file_path = file_obj.name
    filename = os.path.basename(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    content = ""
    print(f"[Process] 线程开始处理: {filename}")
    
    if ext == '.txt':
        content = extract_txt(file_path)
    elif ext == '.docx':
        content = extract_docx(file_path)
    elif ext == '.pdf':
        content = extract_pdf(file_path)
    elif ext in ['.jpg', '.png', '.jpeg']:
        content = extract_image_vlm(file_path)
    else:
        content = f"[Warning] 跳过不支持的文件格式 {ext}"
        
    return {
        "filename": filename,
        "content": content.strip()
    }

def route_and_parse(file_objs):
    if not file_objs:
        return []

    parsed_data = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_file = {executor.submit(process_single_file, obj): obj for obj in file_objs}
        
        for future in as_completed(future_to_file):
            try:
                result = future.result()
                parsed_data.append(result)
            except Exception as exc:
                print(f"[Error] 文件解析线程抛出异常: {exc}")
                
    return parsed_data