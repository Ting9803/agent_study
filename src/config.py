import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)
MODEL_NAME = "glm-4.5-air"
