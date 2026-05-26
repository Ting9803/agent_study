import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

#计算器
def calculator(expression):
    try:
        return str(eval(expression))
    except Exception as e:
        return f"计算失败：{e}"


messages = [{
    "role":"system",
    "content":"""
    你是一只会说人话的猫，你只会一些简单的词汇和计算。
    你有一个工具：
    calculator(expression)：用于计算数学表达式。
    当用户询问你的问题涉及到计算时，你必须只能输出：
    工具调用: calculator|表达式
    
    如果不需要计算，你直接回答。
    """
}]

while True:
    user_input = input("主人：")
    if user_input in ["退出","exit","quit"]:
        break

    #用户的输入信息喂给AI，加入上下文记忆
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
    #原始输出
    answer = response.choices[0].message.content.strip()

    # 假设涉及到计算部分输入到函数并输出,那么过程不要放到用户上下文记忆里面
    if answer.startswith("工具调用: calculator|"):
        expression = answer.replace("工具调用: calculator|","").strip()
        temp_answer = calculator(expression)
        print(f"（工具调用：{temp_answer}）")
        #输出的结果给AI用语言进行整理,过程放临时变量
        temp_messages = messages + [
            {
                "role":"assistant",
                "content":temp_answer
            },
            {
                "role":"user",
                "content":f"工具计算结果是{temp_answer},请联系上下文情景用小猫的语气回答用户，不要涉及计算过程"
            }
        ]
        #输出正式结果，展示给用户，并加入上下文记忆
        response = client.chat.completions.create(
            model="glm-4.5-air",
            messages=temp_messages
        )
        answer = response.choices[0].message.content
        print(f"AI小猫：{answer}")
        messages.append(
            {
                "role":"assistant",
                "content":f"{answer}"
            }
        )
    else:
        print("AI小猫：", answer)
        messages.append(
            {
                "role": "assistant",
                "content": f"{answer}"
            }
        )

