import os
import json
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

#先写计算器
def calculator(expression):
    try:
        return str(eval(expression))
    except Exception as e:
        return f"计算失败{e}"

#定义外部工具
tools = [
    {
        "type":"function",
        "function":{
            "name":"calculator",
            "description":"用于计算数学表达式，例如加减乘除",
            "parameters":{
                "type":"object",
                "properties":{
                    "expression":{
                        "type":"string",
                        "description":"需要计算的数学表达式"
                    }
                },
                "required":["expression"]
            }
        }
    }
]

messages = [
    {
        "role":"system",
        "content":"""
        假如你是一只会说人话的小猫，你只会简单的词汇。
        你可以使用 calculator 工具完成计算。
        如果问题涉及计算，请使用工具。
        最终回答要用小猫语气，不要暴露工具调用过程。"""
    },
]
# 进入循环
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
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    #原始回答，还没判断是否调用工具
    assistant_message = response.choices[0].message
    #放进字典里，不用自己一个一个字段搬
    assistant_dict = assistant_message.model_dump()
    #输出的内容对应上message的格式来保存
    assistant_msg = {
        "role": assistant_dict["role"],
        "content": assistant_dict["content"] or ""
    }
    #有toolcall的话把toolcall的内容也要写进去，才知道它有没有调用tool
    if assistant_dict.get("tool_calls"):
        assistant_msg["tool_calls"] = assistant_dict["tool_calls"]
    messages.append(assistant_msg)

    #有toolcall就要开始调用toolcall了
    if assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"工具名称：{function_name}")
            print(f"工具参数：{function_args}")

            if function_name == "calculator":
                result = calculator(**function_args)
            else:
                result = f"未知工具{function_name}"
            print(f"工具结果：{result}")
            #把toolcall的调用结构放message里面
            messages.append(
                {
                    "role":"tool",
                    "tool_call_id":tool_call.id,
                    "content":result
                }
            )
            #再把result的内容给assistant进行整理，然后输出
            final_response = client.chat.completions.create(
                model="glm-4.5-air",
                messages=messages
            )
            final_answer = final_response.choices[0].message.content
            print(f"AI小猫：{final_answer}")

            #把最后输出的内容也加到message里面
            messages.append(
                {
                    "role":"assistant",
                    "content":final_answer
                }
            )
    else:
        final_answer = assistant_message.content
        print(f"AI小猫：{final_answer}")
        messages.append(
            {
                "role": "assistant",
                "content": final_answer
            }
        )
