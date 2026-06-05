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
    "content":"你是本地文件管理 + 学习记录助手的小助手，需要时可以完成文件读写、追加、统计、列目录、总结学习记录等任务"
    }
]



while True:
    user_input = input("你：")
    if user_input.lower() in ["quit","exit","q"]:
        print("AI小助手：拜拜~")
        break

    messages.append(
        {
            "role":"user",
            "content":user_input
        }
    )

    task_log = []


    while True:
        response = client.chat.completions.create(
            model="glm-4.5-air",
            messages=messages,
            tools=tools,
            thinking={"type": "disabled"}
        )

        answer = response.choices[0].message

        # 有toolcall要放进去
        if answer.tool_calls:
            messages.append(
                {
                    "role":"assistant",
                    "content":answer.content or "",#content可能是没有内容
                    "tool_calls":[
                        tool_call.model_dump()
                        for tool_call in answer.tool_calls
                    ]
                }
            )

            #并且要根据toolcall调用工具
            for tool_call in answer.tool_calls:
                tool_msg = execute_tool_call(tool_call)
                messages.append(tool_msg)
                task_log.append({
                    "tool_name":tool_call.function.name,
                    "arguments":tool_call.function.arguments,
                    "result":tool_msg["content"]
                }
                )

            #调用完以后回到顶部看是不是所有toolcall都弄完了
            continue

        messages.append(
            {
                "role":"assistant",
                "content":answer.content
            }
        )

        print(f"AI小助手：{answer.content}")
        print("本轮工具调用：")
        for index, item in enumerate(task_log,start=1):
            print(f"{index}.{item}")
        break




