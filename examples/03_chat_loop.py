import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

messages = [{
    "role":"system",
    "content":"假如你是一只会说人话的猫，你只会一些简单的词汇"
}]

while True:
    user_input = input("主人：")
    if user_input in ["退出","exit","quit"]:
        break
    messages.append(
        {
            "role":"user",
            "content":user_input
        }
    )
    response = client.chat.completions.create(
        model="glm-4.5-air",
        messages=messages
    )
    answer = response.choices[0].message.content
    print("AI小猫：",answer)
    messages.append(
        {
            "role":"assistant",
            "content":answer
        }
    )