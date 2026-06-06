import json
from tool_schema import tools
from tool_executor import execute_tool_call
from config import client,MODEL_NAME
from planner import make_plan
from agent_utils import (
    pretty_print_task_log,
    summarize_tool_result,
    build_progress_message
)


def run_agent( ):
    """
    主程序
    """


    messages = [
        {
            "role": "system",
            "content": "你是本地文件管理 + 学习记录助手的小助手，需要时可以完成文件读写、追加、统计、列目录、总结学习记录等任务"
        }
    ]

    while True:
        user_input = input("你：")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("AI小助手：拜拜~")
            break

        # 1.先让planner生成计划
        plan = make_plan(user_input)
        print("任务计划：")
        print(json.dumps(plan, ensure_ascii=False, indent=2))

        # 2. 生成的计划加进messages里面
        messages.append(
            {
                "role": "user",
                "content": f"""
用户原始需求：
{user_input}

任务计划：
{json.dumps(plan, ensure_ascii=False, indent=2)}

请根据任务计划完成用户需求。
如果需要工具，请调用工具。
不要假装已经读取、写入或计算。
"""
            }
        )

        #task_log给人看，progress_log给大模型看。大模型看的要简略，不然token爆炸
        task_log = []
        progress_log = []

        while True:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=tools,
                thinking={"type": "disabled"}
            )

            answer = response.choices[0].message

            # 有toolcall要放进去
            if answer.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": answer.content or "",  # content可能是没有内容
                        "tool_calls": [
                            tool_call.model_dump()
                            for tool_call in answer.tool_calls
                        ]
                    }
                )

                # 并且要根据toolcall调用工具
                for tool_call in answer.tool_calls:
                    tool_msg = execute_tool_call(tool_call)
                    messages.append(tool_msg)

                    tool_name = tool_call.function.name
                    arguments = tool_call.function.arguments
                    result_content = tool_msg["content"]

                    # 完整日志：给自己终端调试看
                    task_log.append({
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": result_content
                    })

                    # 简短进度：给模型继续执行用
                    progress_log.append(
                        summarize_tool_result(
                            tool_name=tool_name,
                            arguments=arguments,
                            result_content=result_content
                        )
                    )

                # 当前进度提醒：只放摘要，不放完整内容
                messages.append(build_progress_message(plan, progress_log))

                continue

            messages.append(
                {
                    "role": "assistant",
                    "content": answer.content
                }
            )

            print(f"AI小助手：{answer.content}")
            if task_log:
                print("本轮工具调用：")
                pretty_print_task_log(task_log)

            break




