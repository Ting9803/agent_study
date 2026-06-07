import json


def pretty_print_task_log(task_log: list) -> None:
    """
    美化打印本轮工具调用记录。
    """

    for index, item in enumerate(task_log, start=1):
        pretty_item = item.copy()

        for key in ["arguments", "result"]:
            value = pretty_item.get(key)

            if isinstance(value, str):
                try:
                    pretty_item[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass

        print(f"{index}.")
        print(json.dumps(pretty_item, ensure_ascii=False, indent=2))


def summarize_tool_result(tool_name: str, arguments: str, result_content: str) -> dict:
    """
    把完整工具结果压缩成给模型看的进度摘要。
    避免重复塞大段文件内容。
    """

    try:
        result = json.loads(result_content)
    except json.JSONDecodeError:
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "failed",
            "error_type": "JSONDecodeError",
            "error": "工具返回结果不是合法 JSON",
            "summary": result_content[:100]
        }

    success = result.get("success", False)

    if success is False:
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "failed",
            "error_type": result.get("error_type"),
            "error": result.get("error")
        }

    if tool_name == "list_file":
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "success",
            "dir": result.get("dir"),
            "files": result.get("files")
        }

    if tool_name == "read_file":
        content = result.get("content", "")

        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "success",
            "file": result.get("file"),
            "content_length": len(content),
            "summary": "文件已成功读取，完整内容已在上一条 tool message 中。"
        }

    if tool_name == "count_file_chars":
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "success",
            "file": result.get("file"),
            "char_count": result.get("char_count"),
            "rule": result.get("rule")
        }

    if tool_name in ["write_file", "append_file"]:
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "success",
            "file": result.get("file"),
            "message": result.get("message")
        }

    if tool_name == "calculator":
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "success",
            "expression": result.get("expression"),
            "result": result.get("result")
        }

    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "status": "success",
        "summary": str(result)[:100]
    }
# 不要了，换成build_plan_progress_message
# def build_progress_message(plan: dict, progress_log: list) -> dict:
#     """
#     构造当前进度提醒。
#     只放简短摘要，不重复放完整文件内容。
#     """
#
#     recent_progress = progress_log[-5:]
#
#     return {
#         "role": "user",
#         "content": f"""
# 当前任务计划：
# {json.dumps(plan, ensure_ascii=False, indent=2)}
#
# 已完成步骤摘要：
# {json.dumps(recent_progress, ensure_ascii=False, indent=2)}
#
# 请根据以上进度继续完成任务。
# 不要重复已经完成的工具调用。
# 如果还需要工具，请继续调用工具。
# 如果任务已经完成，请直接给出最终回答。
# 不要假装已经完成未调用的工具操作。
# """
#     }

def format_progress_log(progress_log):
    """
    将 progress_log 里的工具摘要字典转换成给模型看的文本。
    """
    lines = []

    for index, item in enumerate(progress_log, start=1):
        lines.append(
            f"{index}. 工具：{item.get('tool_name')}\n"
            f"   参数：{item.get('arguments')}\n"
            f"   状态：{item.get('status')}\n"
            f"   摘要：{item.get('summary')}"
        )

    return "\n".join(lines)