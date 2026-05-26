#弄懂代码是怎么去和模型api交互的
import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

response = client.chat.completions.create(
    model="glm-4.5-air",
    messages=[
        {"role": "user", "content": "用一句话解释什么是 agent"}
    ]
)

print(response.choices[0].message.content)