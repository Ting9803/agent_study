import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv
from tool_schema import tools
from tool_executor import execute_tool_call


load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

messages = [
    {
    "role":"system",
    "content":"你是一个可以调用本地工具的小助手，需要时可以调用工具完成任务"
    }
]


while True:
    user_input = input("你：")

    if user_input.lower() in ["q", "exit", "quit"]:
        print("AI小助手：拜拜~")
        break

    messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    # 记录用户每轮用什么工具
    task_log = []

    while True:
        response = client.chat.completions.create(
            model="glm-4.5-air",
            messages=messages,
            tools=tools,
            thinking={"type": "disabled"}
        )
        print("请求模型")

        assistant_msg = response.choices[0].message

        # 如果模型要调用工具
        if assistant_msg.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_msg.content or "",
                    "tool_calls": [
                        tool_call.model_dump()
                        for tool_call in assistant_msg.tool_calls
                    ]
                }
            )


            for tool_call in assistant_msg.tool_calls:
                tool_msg = execute_tool_call(tool_call)
                messages.append(tool_msg)
                task_log.append({
                    "tool_name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                    "result": tool_msg["content"]
                })

            # 回到 while True 顶部，让模型继续判断：
            # 是继续调用工具，还是输出最终回答
            continue

        # 如果没有 tool_calls，说明模型已经给出最终回答
        answer = assistant_msg.content

        messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        print(f"AI小助手：{answer}")
        print("本轮工具调用记录：")
        for index, item in enumerate(task_log, start=1):
            print(f"{index}. {item}")
        break
