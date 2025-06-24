from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import os
import requests
import json
import io
from markdown2 import markdown
from weasyprint import HTML as PDFHTML
import os 
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

app = FastAPI()

BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ---- DeepSeek LLM Agent ----
# DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def deepseek_prd_agent(user_input: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "[错误] DeepSeek API Key 未配置，请设置 DEEPSEEK_API_KEY 环境变量"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
你是一个资深的产品经理，请根据以下用户输入内容生成标准的产品需求文档（PRD），格式使用 Markdown，包含以下结构：
1. 产品概述
2. 目标用户
3. 核心功能
4. 页面结构流程图（用 mermaid）
5. 非功能性需求

用户输入："{user_input}"
"""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个资深产品经理，擅长撰写 PRD"},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(DEEPSEEK_API_URL, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"[错误] 调用 DeepSeek 失败：{response.status_code} - {response.text}"

# ---- API Routes ----
class PRDRequest(BaseModel):
    input: str
    format: str = "markdown"

@app.post("/generate_prd")
async def generate_prd(request: PRDRequest):
    content = deepseek_prd_agent(request.input)

    if request.format == "pdf":
        html_content = markdown(content)
        pdf_io = io.BytesIO()
        PDFHTML(string=html_content).write_pdf(pdf_io)
        pdf_io.seek(0)
        return StreamingResponse(pdf_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=prd.pdf"
        })
    else:
        return {"markdown": content}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)