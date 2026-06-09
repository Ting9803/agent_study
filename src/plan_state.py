STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"

VALID_STATUS = {
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_DONE,
    STATUS_FAILED
}
def init_plan_state(plan):
    """
    初始化plan的状态为pending
    :param plan:
    :return:
        {
  "goal": "用户最终想完成什么",
  "steps": [
    {
      "step": 1,
      "action": "这一步需要做什么",
      "tool": "需要使用的工具名，如果不需要就写 None",
      "status":"pending"
    }
  ]
}
    """
    steps = []
    for index,step in enumerate(plan.get("steps",[]),start=1):
        steps.append(
            {
                "id":step.get("step",index),
                "action":step.get("action",""),
                "tool":step.get("tool"),
                "status":STATUS_PENDING
            }
        )
    return {
        "goal":plan.get("goal",""),
        "steps":steps
    }

def build_plan_progress_message(plan_state):
    """
    输出当前进度状态
    :param plan_state:
    :return: str类型：
    当前任务目标：总结第七天学习笔记

当前计划执行状态：
1. [pending] 列出 notes 文件夹，建议工具：list_file
2. [pending] 读取第七天学习笔记，建议工具：read_file

请优先推进下一步：列出 notes 文件夹
    """
    lines = []
    lines.append(f"当前任务目标：{plan_state['goal']}")
    lines.append(f"当前任务执行状态：")
    for step in plan_state["steps"]:
        lines.append(
            f"{step['id']}. [{step['status']}] {step['action']}，建议工具：{step['tool']}"
        )
    return "\n".join(lines)


def get_next_pending_step(plan_state):
    steps = plan_state.get("steps", [])
#    print("get_next_pending_step 收到的 steps：", steps)

    for step in steps:
        status = str(step.get("status", "")).strip().lower()

        #print("正在检查 step：", step.get("id"), "status =", repr(status))

        if status == "pending":
            #print("找到 pending 步骤：", step)
            return step

    #print("没有找到 pending 步骤")
    return None

def get_step_for_tool_call(plan_state, tool_name):
    """
    根据当前工具调用，找到应该更新的计划步骤。

    逻辑：
    1. 优先找 pending 且 tool == tool_name 的步骤。
    2. 如果在它前面有 pending 且 tool is None 的步骤，
       说明模型已经通过思考跨过了这些步骤，可以先标记为 done。
    3. 如果找不到匹配工具的步骤，再退回第一个 pending 步骤。
    """
    steps = plan_state.get("steps", [])

    for index, step in enumerate(steps):
        status = str(step.get("status", "")).strip().lower()

        if status == "pending" and step.get("tool") == tool_name:
            # 把这个工具步骤前面的无工具 pending 步骤标记为 done
            for previous_step in steps[:index]:
                previous_status = str(previous_step.get("status", "")).strip().lower()

                if previous_status == "pending" and previous_step.get("tool") is None:
                    previous_step["status"] = STATUS_DONE

            return step

    # 如果没有匹配工具的 pending 步骤，再退回原来的逻辑
    return get_next_pending_step(plan_state)

def update_step_status(plan_state, step_id, status):
    """
    根据 step_id 更新某一步的执行状态。
    status 可以是 pending / running / done / failed。
    """
    if status not in VALID_STATUS:
        raise ValueError(f"非法状态：{status}")

    if "steps" not in plan_state:
        raise KeyError("plan_state 缺少 steps 字段")

    for step in plan_state["steps"]:
        if step.get("id") == step_id:
            step["status"] = status
            return plan_state

    raise ValueError(f"没有找到 id 为 {step_id} 的步骤")

def validate_plan_state(plan_state):
    """
    检查 plan_state 的结构是否符合约定。
    """
    if not isinstance(plan_state, dict):
        raise TypeError("plan_state 必须是 dict")

    if "goal" not in plan_state:
        raise KeyError("plan_state 缺少 goal 字段")

    if "steps" not in plan_state:
        raise KeyError("plan_state 缺少 steps 字段")

    if not isinstance(plan_state["steps"], list):
        raise TypeError("plan_state['steps'] 必须是 list")

    for step in plan_state["steps"]:
        required_keys = ["id", "action", "tool", "status"]

        for key in required_keys:
            if key not in step:
                raise KeyError(f"step 缺少字段：{key}")

        if step["status"] not in VALID_STATUS:
            raise ValueError(f"非法 step status：{step['status']}")

    return True