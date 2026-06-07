import json
from tool_schema import tools
from tool_executor import execute_tool_call
from config import client,MODEL_NAME
from planner import make_plan
from agent_utils import (
    pretty_print_task_log,
    summarize_tool_result,
    format_progress_log
)
from plan_state import (
    init_plan_state,
    get_next_pending_step,
    update_step_status,
    build_plan_progress_message,
    validate_plan_state
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

        # 1.先让planner生成计划,
        plan = make_plan(user_input)
        # 并且初始化plan_state
        plan_state = init_plan_state(plan)
        validate_plan_state(plan_state)
        print("任务计划：")
        print(json.dumps(plan, ensure_ascii=False, indent=2))

        # 2. 生成的计划加进messages里面
        messages.append(
            {
                "role": "user",
                "content": f"""
        用户原始需求：
        {user_input}

        {build_plan_progress_message(plan_state)}

        请根据当前计划状态完成用户需求。
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
                    # 找到当前要执行的计划步骤
                    current_step = get_next_pending_step(plan_state)
                    #print("当前步骤：", current_step)
                    # 工具调用前：标记为 running
                    if current_step:
                        update_step_status(plan_state, current_step["id"], "running")

                    # 开始执行
                    tool_msg = execute_tool_call(tool_call)
                    messages.append(tool_msg)

                    tool_name = tool_call.function.name
                    arguments = tool_call.function.arguments
                    result_content = tool_msg["content"]

                    #解析工具结果
                    try:
                        result_data = json.loads(result_content)
                        success = result_data.get("success", False)
                    except json.JSONDecodeError:
                        success = False

                    # 根据工具真实执行结果更新 plan_state
                    if current_step:
                        if success:
                            update_step_status(plan_state, current_step["id"], "done")
                        else:
                            update_step_status(plan_state, current_step["id"], "failed")

                    #print("更新后的 plan_state：")
                    #print(json.dumps(plan_state, ensure_ascii=False, indent=2))

                    # 完整日志：给自己终端调试看
                    task_log.append({
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "success":success,
                        "result": result_content,
                    })

                    # 简短进度：给模型继续执行用
                    progress_log.append(
                        summarize_tool_result(
                            tool_name=tool_name,
                            arguments=arguments,
                            result_content=result_content
                        )
                    )

                # 当前进度提醒：放当前计划执行状态
                progress_text = format_progress_log(progress_log)
                messages.append(
                    {
                        "role":"user",
                        "content":f"""
                    
                    {build_plan_progress_message(plan_state)}
                    已完成工具摘要：
                    {progress_text}
                    请根据当前计划状态继续推进任务。
                    """
                    }
                )
                print(build_plan_progress_message(plan_state))

                continue

            messages.append(
                {
                    "role": "assistant",
                    "content": answer.content
                }
            )
            #如果步骤没有 tool call。模型直接回答最终总结时，这一步也应该标记成 done。
            final_step = get_next_pending_step(plan_state)

            if final_step and final_step.get("tool") is None:
                update_step_status(plan_state, final_step["id"], "done")

            print(f"AI小助手：{answer.content}")

            if task_log:
                print("本轮工具调用：")
                pretty_print_task_log(task_log)

            break




