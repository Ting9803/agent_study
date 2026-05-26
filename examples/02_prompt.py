import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

messages = [
    {
        "role":"system",
        "content":"你是一个ai小助手，说话简洁明了通俗易懂，不长篇大论"
    },
    {
        "role":"user",
        "content":"什么是agent？"
    }

]
response = client.chat.completions.create(
    model="glm-4.5-air",
    messages=messages
)

print(response.choices[0].message.content)