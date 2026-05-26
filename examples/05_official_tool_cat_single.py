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
        你是一只会说人话的小猫。
        你可以使用 calculator 工具完成计算。
        如果问题涉及计算，请使用工具。
        最终回答要用小猫语气，不要暴露工具调用过程。"""
    },
    {
        "role": "user",
        "content": "你昨天吃了2个小鱼干，今天吃了3个小鱼干，一共吃了多少个？"
    }
]

#调用工具
response = client.chat.completions.create(
    model="glm-4.5-air",
    messages=messages,
    tools= tools,
    tool_choice="auto"
)

assistant_message = response.choices[0].message
#print("模型第一次返回：", assistant_message)

print("模型第一次返回",assistant_message.model_dump())
#"""模型第一次返回： CompletionMessage(
# content='\n我来帮你算一下总共吃了多少个小鱼干！\n',
# role='assistant',
# reasoning_content='\n用户问的是昨天吃了2个小鱼干，今天吃了3个小鱼干，一共吃了多少个。这是一个简单的加法计算问题。\n\n我需要使用calculator工具来计算 2 + 3。\n\n表达式应该是 "2 + 3"。',
# tool_calls=[
# CompletionMessageToolCall(
# id='call_-7598140572208980570',
# function=Function(
#              arguments='{"expression":"2 + 3"}',
#              name='calculator'),
# type='function', index=0)])

assistant_dict = assistant_message.model_dump()
#{'content': '\n我来帮你算一下小鱼干的总数！\n', '
# role': 'assistant',
# 'reasoning_content': '\n用户问的是一个小数学问题：昨天吃了2个小鱼干，今天吃了3个小鱼干，一共吃了多少个。\n\n这是一个简单的加法问题：2 + 3 = 5\n\n我可以使用calculator工具来计算这个表达式。',
# 'tool_calls': [
#   {'id': 'call_-7598176168897933486',
#   'function': {'arguments': '{"expression":"2 + 3"}', 'name': 'calculator'},
#   'type': 'function', 'index': 0}]}
assistant_msg = {
    "role":assistant_dict["role"],
    "content":assistant_dict["content"] or ""
}
if assistant_dict.get("tool_calls"):
    assistant_msg["tool_calls"] = assistant_dict["tool_calls"]
messages.append(assistant_msg)

if assistant_message.tool_calls:
    #本来是自己手写的toolcalls转dict，但是为了方便，可以用model_dump()来搬，就不用写那么多
    # messages.append({
    #     "role": "assistant",
    #     "content": assistant_message.content or "",
    #     "tool_calls": [
    #         {
    #             "id":tool_call.id,
    #             "type":tool_call.type,
    #             "function":{
    #                 "name":tool_call.function.name,
    #                 "arguments":tool_call.function.arguments
    #             }
    #
    #         }
    #         for tool_call in assistant_message.tool_calls
    #     ]
    #
    # })

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

        messages.append(
            {
                "role":"tool",
                "tool_call_id":tool_call.id,
                "content":result
            }
        )
        final_response = client.chat.completions.create(
            model="glm-4.5-air",
            messages=messages
        )
        final_answer = final_response.choices[0].message.content
        print(f"AI小猫：{final_answer}")
        print(messages)


else:
    print(f"AI小猫：{assistant_message.content}")
