from tools import calculator,read_file,write_file,list_file,append_file,count_file_chars
import json

tool_map = {
    "calculator" : calculator,
    "read_file" : read_file,
    "write_file" : write_file,
    "append_file" : append_file,
    "list_file" : list_file,
    "count_file_chars":count_file_chars
}

def execute_tool_call(tool_call):
    """
    执行单个 tool_call，并返回一条 tool 消息,dict格式
    适合arguments是dict的情况
    :param tool_call:dist
    :return:
    """
    function_name = tool_call.function.name
    print(f"调用工具：{function_name}")
    try:
        function_args = json.loads(tool_call.function.arguments)
    except Exception as e:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps({
                "success": False,
                "tool_name": function_name,
                "error_type": type(e).__name__,
                "error": str(e)
            }, ensure_ascii=False)
        }
    if function_name not in tool_map:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps({
                "success": False,
                "tool_name": function_name,
                "error_type": "UnknownTool",
                "error": f"未知工具：{function_name}"
            }, ensure_ascii=False)
        }

    try:
        result = tool_map[function_name](**function_args)


        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, ensure_ascii=False)
        }

    except Exception as e:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps({
                "success": False,
                "tool_name": function_name,
                "arguments": function_args,
                "error_type": type(e).__name__,
                "error": str(e)
            }, ensure_ascii=False)
        }

