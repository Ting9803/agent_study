import json
from config import client,MODEL_NAME
from tool_schema import tools


def get_tool_infos() ->list[dict]:
    """
    获取当前能够使用的工具信息
    :return:
    {
                {
                "name":function_info["name"],
                "description":function_info.get("description","")
            }，
            {…………
            }
    }
    """
    tool_infos = []
    for tool in tools:
        function_info = tool["function"]
        tool_infos.append(
            {
                "name":function_info["name"],
                "description":function_info.get("description","")
            }
        )
    return tool_infos

def build_planner_prompt() -> str:
    tool_infos = get_tool_infos()

    return f"""
你是一个任务规划器，只负责把用户需求拆成执行计划。

要求：
1. 只规划，不执行任务。
2. 不要声称你已经读取文件、写入文件或完成计算。
3. 如果需要工具，只能从下面的工具列表中选择。
4. 不允许发明工具名。
5. 如果不需要工具，tool 字段写 null，不要写成字符串 "null"。
6. 输出必须是纯 JSON，不要使用 ```json 代码块，不要输出多余解释。
7. 计划必须尽量覆盖完整任务，不要只写第一步。
8. 如果用户要查找目录下的某个文件，必须拆成：列目录、进入子目录、找到具体文件、读取文件、总结内容。
9. 如果路径或文件名不确定，也要规划使用 list_file 逐步确认路径。
10. steps 至少包含 2 步；除非用户需求本身只需要一步。

可用工具列表：
{json.dumps(tool_infos, ensure_ascii=False, indent=2)}

JSON 格式如下：
{{
  "goal": "用户最终想完成什么",
  "steps": [
    {{
      "step": 1,
      "action": "这一步需要做什么",
      "tool": "需要使用的工具名，如果不需要就写 null"
    }}
  ]
}}
"""

def clean_json_content(content: str) -> str:
    """
    避免模型返回的json有别的符号，清洗一下先
    :param content:
    :return:
    """
    content = content.strip()

    if content.startswith("```json"):
        content = content.replace("```json", "", 1).strip()

    if content.startswith("```"):
        content = content.replace("```", "", 1).strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    return content

def validate_plan_tools(plan: dict) -> dict:
    """
    看工具名是否可用，不可用就加个note
    :param plan:
    :return:
    """
    valid_tool_names = {
        tool["function"]["name"]
        for tool in tools
    }

    for step in plan.get("steps", []):
        tool_name = step.get("tool")

        # 模型可能会把 null 写成字符串 "null"
        if tool_name in [None, "null", "None", ""]:
            step["tool"] = None
            continue

        if tool_name not in valid_tool_names:
            step["note"] = f"原工具名 {tool_name} 不在可用工具列表中，已置为 null"
            step["tool"] = None

    return plan

def make_plan(user_input :str) -> dict:
    """
    让模型先根据用户需求生成任务计划，不管初始化和执行状态
    :parameter user_input:str
    :return
    {
  "goal": "用户最终想完成什么",
  "steps": [
    {
      "step": 1,
      "action": "这一步需要做什么",
      "tool": "需要使用的工具名，如果不需要就写 None"
    }
  ]
}
    """
    PLANNER_SYSTEM_PROMPT = build_planner_prompt()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        thinking = {"type": "disabled"},
        messages=[
            {
                "role":"system",
                "content":PLANNER_SYSTEM_PROMPT
            },
            {
                "role":"user",
                "content":user_input
            }
        ],
    )

    content = response.choices[0].message.content
    content = clean_json_content(content)


    try:
        plan = json.loads(content)
        plan = validate_plan_tools(plan)
        return  plan

    except json.JSONDecodeError:
        return {
            "goal": user_input,
            "steps": [
                {
                    "step": 1,
                    "action": "模型没有返回标准 JSON，直接根据用户需求继续执行",
                    "tool": None
                }
            ],
            "raw_plan": content
        }


