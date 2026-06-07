# 函数输入输出说明

本文档用于记录项目中核心函数的输入、输出和关键 dict 数据结构，避免字段名混乱。

---

# 1. 核心数据结构

## 1.1 plan

`plan` 是 `make_plan(user_input)` 返回的原始任务计划。

来源：

```python
plan = make_plan(user_input)
```

结构：

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "需要使用的工具名，如果不需要工具则为 None"
        }
    ]
}
```

字段说明：

| 字段             | 类型         | 说明                    |
| -------------- | ---------- | --------------------- |
| goal           | str        | 用户最终目标                |
| steps          | list[dict] | 任务步骤列表                |
| steps[].step   | int        | 第几步                   |
| steps[].action | str        | 当前步骤要做什么              |
| steps[].tool   | str / None | 建议使用的工具名，不需要工具则为 None |

注意：

* `plan` 里面是 `steps`，不是 `step`
* 单个步骤里的编号字段叫 `step`
* `plan` 是静态计划，不包含执行状态
* `status` 不放在 `plan` 里

---

## 1.2 plan_state

`plan_state` 是 `init_plan_state(plan)` 返回的可执行状态结构。

来源：

```python
plan_state = init_plan_state(plan)
```

结构：

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "id": 1,
            "action": "这一步需要做什么",
            "tool": "需要使用的工具名，如果不需要工具则为 None",
            "status": "pending"
        }
    ]
}
```

字段说明：

| 字段             | 类型         | 说明                         |
| -------------- | ---------- | -------------------------- |
| goal           | str        | 用户最终目标                     |
| steps          | list[dict] | 带状态的任务步骤列表                 |
| steps[].id     | int        | 步骤 id，由原 plan 中的 step 转换而来 |
| steps[].action | str        | 当前步骤要做什么                   |
| steps[].tool   | str / None | 建议使用的工具名                   |
| steps[].status | str        | 当前步骤执行状态                   |

status 可选值：

| 状态      | 含义   |
| ------- | ---- |
| pending | 等待执行 |
| running | 正在执行 |
| done    | 执行成功 |
| failed  | 执行失败 |

注意：

* `plan_state` 里面仍然是 `steps`
* 单个步骤的编号字段叫 `id`
* `update_step_status()` 修改的是 `plan_state["steps"]`
* 不要写成 `plan_state.get("step", [])`

---

## 1.3 tool_msg

`tool_msg` 是 `execute_tool_call(tool_call)` 返回的工具消息。

来源：

```python
tool_msg = execute_tool_call(tool_call)
```

结构：

```python
{
    "role": "tool",
    "tool_call_id": "工具调用 id",
    "content": "JSON 字符串"
}
```

其中 `content` 是 JSON 字符串，解析后一般是：

```python
{
    "success": True,
    "...": "不同工具自己的返回字段"
}
```

失败时通常是：

```python
{
    "success": False,
    "tool_name": "工具名",
    "error_type": "错误类型",
    "error": "错误信息"
}
```

注意：

* `tool_msg["content"]` 是字符串
* 如果要判断成功失败，需要先：

```python
result_data = json.loads(tool_msg["content"])
success = result_data.get("success", False)
```

---

## 1.4 task_log

`task_log` 是给人看的完整工具调用记录。

来源：

```python
task_log.append(...)
```

结构：

```python
{
    "tool_name": "read_file",
    "arguments": "{\"file_name\": \"abc.txt\"}",
    "success": False,
    "result": "完整工具返回内容"
}
```

字段说明：

| 字段        | 类型   | 说明                     |
| --------- | ---- | ---------------------- |
| tool_name | str  | 工具名                    |
| arguments | str  | 模型传给工具的参数，通常是 JSON 字符串 |
| success   | bool | 工具是否执行成功               |
| result    | str  | 完整工具返回结果               |

用途：

* 打印到终端
* 给开发者调试
* 不建议完整塞回模型，避免 token 过长

---

## 1.5 progress_log

`progress_log` 是给模型看的工具执行摘要。

来源：

```python
progress_log.append(
    summarize_tool_result(
        tool_name=tool_name,
        arguments=arguments,
        result_content=result_content
    )
)
```

结构示例：

```python
{
    "tool_name": "read_file",
    "arguments": "{\"file_name\": \"notes/day07.md\"}",
    "status": "success",
    "file": "notes/day07.md",
    "content_length": 1234,
    "summary": "文件已成功读取，完整内容已在上一条 tool message 中。"
}
```

失败时：

```python
{
    "tool_name": "read_file",
    "arguments": "{\"file_name\": \"abc.txt\"}",
    "status": "failed",
    "error_type": "FileNotFoundError",
    "error": "文件不存在"
}
```

字段说明：

| 字段         | 类型  | 说明               |
| ---------- | --- | ---------------- |
| tool_name  | str | 工具名              |
| arguments  | str | 工具参数             |
| status     | str | success / failed |
| summary    | str | 简短摘要             |
| error_type | str | 失败时的错误类型         |
| error      | str | 失败时的错误信息         |

用途：

* 通过 `format_progress_log(progress_log)` 转成文字
* 塞回 messages，让模型知道已经执行过什么
* 避免重复塞大段文件内容

---

# 2. 函数输入输出说明

## 2.1 planner.py

| 函数                    | 输入              | 输出         | 作用           |
| --------------------- | --------------- | ---------- | ------------ |
| make_plan(user_input) | user_input: str | plan: dict | 根据用户需求生成任务计划 |

输出结构：

```python
{
    "goal": str,
    "steps": [
        {
            "step": int,
            "action": str,
            "tool": str | None
        }
    ]
}
```

---

## 2.2 plan_state.py

| 函数                                              | 输入                                          | 输出                | 作用               |
| ----------------------------------------------- | ------------------------------------------- | ----------------- | ---------------- |
| init_plan_state(plan)                           | plan: dict                                  | plan_state: dict  | 将静态计划转换成可追踪状态    |
| get_next_pending_step(plan_state)               | plan_state: dict                            | step: dict / None | 找到第一个 pending 步骤 |
| update_step_status(plan_state, step_id, status) | plan_state: dict, step_id: int, status: str | plan_state: dict  | 更新某一步的执行状态       |
| build_plan_progress_message(plan_state)         | plan_state: dict                            | message: str      | 把计划状态转换成给模型看的提示词 |

---

## 2.3 tool_executor.py

| 函数                           | 输入        | 输出             | 作用                     |
| ---------------------------- | --------- | -------------- | ---------------------- |
| execute_tool_call(tool_call) | tool_call | tool_msg: dict | 解析模型 tool_call 并调用本地工具 |

输出结构：

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps(result, ensure_ascii=False)
}
```

其中 `content` 里的 result 必须包含：

```python
{
    "success": True | False
}
```

---

## 2.4 agent_utils.py

| 函数                                                          | 输入            | 输出   | 作用             |
| ----------------------------------------------------------- | ------------- | ---- | -------------- |
| summarize_tool_result(tool_name, arguments, result_content) | str, str, str | dict | 将工具结果压缩成结构化摘要  |
| format_progress_log(progress_log)                           | list[dict]    | str  | 将工具摘要转换成模型可读文本 |
| pretty_print_task_log(task_log)                             | list[dict]    | None | 打印完整工具调用记录     |

---

## 2.5 agent.py

| 函数          | 输入    | 输出    | 作用                         |
| ----------- | ----- | ----- | -------------------------- |
| run_agent() | 控制台输入 | 控制台输出 | 主循环，负责规划、执行、工具调用、状态更新和最终回答 |

主要流程：

```python
user_input
    ↓
make_plan(user_input)
    ↓
init_plan_state(plan)
    ↓
build_plan_progress_message(plan_state)
    ↓
模型生成 tool_call
    ↓
get_next_pending_step(plan_state)
    ↓
update_step_status(plan_state, step_id, "running")
    ↓
execute_tool_call(tool_call)
    ↓
根据 success 更新 done / failed
    ↓
summarize_tool_result(...)
    ↓
format_progress_log(progress_log)
    ↓
模型继续执行或最终回答
```

---

# 3. 容易写错的字段名

| 正确字段      | 错误写法        | 说明                                          |
| --------- | ----------- | ------------------------------------------- |
| steps     | step        | plan 和 plan_state 里都是 steps                 |
| id        | step        | plan_state 里步骤编号叫 id                        |
| step      | id          | 原始 plan 里步骤编号叫 step                         |
| status    | state       | 执行状态字段叫 status                              |
| action    | description | 当前项目里统一用 action                             |
| tool      | tool_name   | plan / plan_state 里统一用 tool                 |
| tool_name | tool        | task_log / progress_log 里记录实际工具名用 tool_name |

---

# 4. 关键约定

1. `plan` 是静态计划，不记录状态。
2. `plan_state` 是动态执行状态，必须有 `status`。
3. `task_log` 给人看，可以保留完整结果。
4. `progress_log` 给模型看，必须压缩内容。
5. 工具函数返回值必须包含 `success` 字段。
6. `execute_tool_call()` 返回的是 tool message，真正结果在 `tool_msg["content"]` 里。
7. 读取 `tool_msg["content"]` 时要先 `json.loads()`。
