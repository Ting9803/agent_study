# Function Reference

本文档用于记录当前 Agent 项目的核心函数、输入输出结构和容易写错的字段名。

当前覆盖文件：

```text
agent.py
planner.py
plan_state.py
agent_utils.py
```

---

# 1. agent.py

## run_agent() -> None

### 功能

主程序入口，负责启动本地 Agent 的多轮对话循环。

它会完成：

```text
1. 接收用户输入
2. 调用 planner 生成任务计划
3. 初始化 plan_state
4. 把用户需求和计划状态加入 messages
5. 调用大模型判断是否需要 tool_call
6. 执行工具调用
7. 根据工具执行结果更新 plan_state
8. 维护 task_log 和 progress_log
9. 输出最终回答
```

### 输入

无显式参数，通过终端 `input("你：")` 获取用户输入。

### 输出

无 return。

主要通过终端输出：

```text
任务计划
当前计划执行状态
AI小助手最终回答
本轮工具调用记录
```

### 依赖函数

| 函数                                                          | 来源文件             | 作用               |
| ----------------------------------------------------------- | ---------------- | ---------------- |
| make_plan(user_input)                                       | planner.py       | 根据用户输入生成计划       |
| init_plan_state(plan)                                       | plan_state.py    | 初始化计划状态          |
| validate_plan_state(plan_state)                             | plan_state.py    | 检查计划状态结构是否合法     |
| build_plan_progress_message(plan_state)                     | plan_state.py    | 生成当前计划进度文本       |
| get_next_pending_step(plan_state)                           | plan_state.py    | 找到下一个 pending 步骤 |
| update_step_status(plan_state, step_id, status)             | plan_state.py    | 更新步骤状态           |
| execute_tool_call(tool_call)                                | tool_executor.py | 执行模型返回的工具调用      |
| summarize_tool_result(tool_name, arguments, result_content) | agent_utils.py   | 压缩工具结果给模型看       |
| format_progress_log(progress_log)                           | agent_utils.py   | 把进度摘要列表转成文本      |
| pretty_print_task_log(task_log)                             | agent_utils.py   | 美化打印工具调用记录       |

### 关键内部变量

| 变量           | 类型                        | 说明                               |
| ------------ | ------------------------- | -------------------------------- |
| messages     | list[dict]                | 传给模型的上下文消息                       |
| user_input   | str                       | 用户本轮输入                           |
| plan         | dict                      | planner 生成的原始任务计划                |
| plan_state   | dict                      | 带执行状态的任务计划                       |
| task_log     | list[dict]                | 给人看的完整工具调用日志                     |
| progress_log | list[dict]                | 给模型看的简短工具执行摘要                    |
| response     | ChatCompletion            | 模型返回结果                           |
| answer       | CompletionMessage         | 当前轮模型消息                          |
| tool_call    | CompletionMessageToolCall | 模型请求调用的工具                        |
| tool_msg     | dict                      | 工具执行后返回给 messages 的 tool message |

### plan 结构

`make_plan()` 返回的原始计划结构：

```python
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
```

### plan_state 结构

`init_plan_state()` 转换后的计划状态结构：

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "id": 1,
            "action": "这一步需要做什么",
            "tool": "工具名或 None",
            "status": "pending"
        }
    ]
}
```

### task_log 结构

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "success": success,
    "result": result_content
}
```

### progress_log 单项结构

由 `summarize_tool_result()` 生成，常见结构如下：

```python
{
    "tool_name": "read_file",
    "arguments": "{\"file_name\": \"xxx.md\"}",
    "status": "success",
    "file": "xxx.md",
    "content_length": 123,
    "summary": "文件已成功读取，完整内容已在上一条 tool message 中。"
}
```

### 注意事项

| 容易写错的点              | 正确写法                                        |
| ------------------- | ------------------------------------------- |
| 原始计划步骤编号字段          | `step`                                      |
| plan_state 里的步骤编号字段 | `id`                                        |
| 原始计划步骤列表            | `steps`                                     |
| 工具调用参数              | `tool_call.function.arguments`              |
| 工具调用名称              | `tool_call.function.name`                   |
| 工具返回内容              | `tool_msg["content"]`                       |
| 工具是否成功              | 从 `json.loads(result_content)` 里取 `success` |
| 没有工具的步骤             | `tool` 为 `None`                             |
| 已完成状态               | `"done"`                                    |
| 失败状态                | `"failed"`                                  |

---

# 2. planner.py

## get_tool_infos() -> list[dict]

### 功能

从 `tool_schema.py` 的 `tools` 中提取当前可用工具的简要信息。

用于构造 planner 的提示词，避免 planner 发明不存在的工具名。

### 输入

无显式参数。

### 输出

返回工具信息列表：

```python
[
    {
        "name": "工具名",
        "description": "工具描述"
    }
]
```

### 关键字段

| 字段          | 类型  | 说明            |
| ----------- | --- | ------------- |
| name        | str | 工具函数名         |
| description | str | 工具描述，没有则为空字符串 |

### 注意事项

这个函数只提取工具名称和描述，不提取完整 parameters schema。

---

## build_planner_prompt() -> str

### 功能

构造 planner 的 system prompt。

这个 prompt 约束模型：

```text
1. 只规划，不执行
2. 不假装已经读取、写入、计算
3. 只能使用工具列表中的工具
4. 不允许发明工具
5. 不需要工具时 tool 写 null
6. 输出纯 JSON
7. 尽量生成完整步骤
8. 路径不确定时优先 list_file
```

### 输入

无显式参数。

内部会调用：

```python
tool_infos = get_tool_infos()
```

### 输出

返回一个字符串类型的 planner prompt。

### planner 要求输出的 JSON 格式

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "需要使用的工具名，如果不需要就写 null"
        }
    ]
}
```

### 注意事项

| 字段       | 说明        |
| -------- | --------- |
| `goal`   | 用户最终目标    |
| `steps`  | 任务步骤列表    |
| `step`   | 步骤编号      |
| `action` | 当前步骤动作    |
| `tool`   | 工具名或 null |

---

## clean_json_content(content: str) -> str

### 功能

清洗模型返回的 JSON 字符串，去掉模型可能额外包上的 Markdown 代码块标记。

主要处理：

````text
```json
````

````

### 输入

| 参数 | 类型 | 说明 |
|---|---|---|
| content | str | 模型返回的原始文本 |

### 输出

返回清理后的字符串。

### 示例

输入：

```text
```json
{"goal": "列出文件", "steps": []}
````

````

输出：

```text
{"goal": "列出文件", "steps": []}
````

### 注意事项

这个函数只做简单字符串清理，不负责校验 JSON 是否合法。

---

## validate_plan_tools(plan: dict) -> dict

### 功能

检查 planner 生成的每一步 `tool` 是否在当前可用工具列表中。

如果模型返回了不可用工具名，会把该步骤的 `tool` 改成 `None`，并添加 `note` 字段说明原因。

### 输入

| 参数   | 类型   | 说明              |
| ---- | ---- | --------------- |
| plan | dict | planner 生成的任务计划 |

### 输出

返回修正后的 plan。

### 输入结构

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "工具名或 null"
        }
    ]
}
```

### 输出结构

正常情况：

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "read_file"
        }
    ]
}
```

工具名不可用时：

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": None,
            "note": "原工具名 xxx 不在可用工具列表中，已置为 null"
        }
    ]
}
```

### 特殊处理

以下值都会被统一改成 `None`：

```python
None
"null"
"None"
""
```

### 注意事项

| 容易写错的点            | 正确写法         |
| ----------------- | ------------ |
| Python 空值         | `None`       |
| JSON 空值           | `null`       |
| planner 输出里的无工具步骤 | `tool: null` |
| Python 代码里的无工具步骤  | `tool: None` |

---

## make_plan(user_input: str) -> dict

### 功能

调用大模型，根据用户输入生成任务计划。

它只负责生成计划，不负责初始化状态，也不负责执行工具。

### 输入

| 参数         | 类型  | 说明     |
| ---------- | --- | ------ |
| user_input | str | 用户原始需求 |

### 输出

返回计划字典。

成功解析时返回：

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "工具名或 None"
        }
    ]
}
```

JSON 解析失败时返回 fallback 结构：

```python
{
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
```

### 内部流程

```text
1. 调用 build_planner_prompt() 生成 planner system prompt
2. 调用 client.chat.completions.create()
3. 获取 response.choices[0].message.content
4. 调用 clean_json_content(content)
5. 尝试 json.loads(content)
6. 成功后调用 validate_plan_tools(plan)
7. 失败则返回 fallback plan
```

### 依赖

| 名称                          | 来源             | 说明                |
| --------------------------- | -------------- | ----------------- |
| client                      | config.py      | 模型客户端             |
| MODEL_NAME                  | config.py      | 模型名称              |
| tools                       | tool_schema.py | 工具 schema         |
| build_planner_prompt()      | planner.py     | 构造 planner prompt |
| clean_json_content(content) | planner.py     | 清洗 JSON 文本        |
| validate_plan_tools(plan)   | planner.py     | 校验工具名             |

### 注意事项

| 容易写错的点     | 正确写法         |
| ---------- | ------------ |
| 用户输入参数名    | `user_input` |
| 计划步骤列表字段   | `steps`      |
| 单个步骤编号字段   | `step`       |
| 单个步骤动作字段   | `action`     |
| 单个步骤工具字段   | `tool`       |
| 解析失败保存原始内容 | `raw_plan`   |

---

# 3. plan_state.py

## 状态常量

### 功能

定义计划步骤的执行状态。

```python
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
```

### VALID_STATUS

```python
VALID_STATUS = {
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_DONE,
    STATUS_FAILED
}
```

### 状态说明

| 状态      | 含义   |
| ------- | ---- |
| pending | 等待执行 |
| running | 正在执行 |
| done    | 已完成  |
| failed  | 执行失败 |

### 注意事项

所有状态更新都应该使用上面四种字符串，不要随手写新的状态名。

---

## init_plan_state(plan: dict) -> dict

### 功能

把 planner 返回的原始 plan 转成带状态的 plan_state。

原始 plan 里的每一步没有执行状态，这个函数会给每一步加上：

```python
"status": "pending"
```

### 输入

| 参数   | 类型   | 说明              |
| ---- | ---- | --------------- |
| plan | dict | planner 生成的原始计划 |

### 输入结构

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "工具名或 None"
        }
    ]
}
```

### 输出

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "id": 1,
            "action": "这一步需要做什么",
            "tool": "工具名或 None",
            "status": "pending"
        }
    ]
}
```

### 字段转换规则

| 原始 plan 字段       | plan_state 字段                |
| ---------------- | ---------------------------- |
| `goal`           | `goal`                       |
| `steps[].step`   | `steps[].id`                 |
| `steps[].action` | `steps[].action`             |
| `steps[].tool`   | `steps[].tool`               |
| 无                | `steps[].status = "pending"` |

### 默认值

| 情况             | 默认值                    |
| -------------- | ---------------------- |
| plan 缺少 goal   | `""`                   |
| plan 缺少 steps  | `[]`                   |
| step 缺少 step   | 使用 enumerate 生成的 index |
| step 缺少 action | `""`                   |
| step 缺少 tool   | `None`                 |
| step 初始 status | `"pending"`            |

### 注意事项

这里会把原始计划里的 `step` 改名成 `id`。

后续更新状态时用的是：

```python
current_step["id"]
```

不是：

```python
current_step["step"]
```

---

## build_plan_progress_message(plan_state: dict) -> str

### 功能

把当前计划状态格式化成一段文本，方便加入 messages 让模型知道当前任务进度。

### 输入

| 参数         | 类型   | 说明       |
| ---------- | ---- | -------- |
| plan_state | dict | 带状态的任务计划 |

### 输出

返回字符串。

### 输出示例

```text
当前任务目标：总结第七天学习笔记
当前任务执行状态：
1. [pending] 列出 notes 文件夹，建议工具：list_file
2. [pending] 读取第七天学习笔记，建议工具：read_file
```

### 依赖字段

```python
plan_state["goal"]
plan_state["steps"]
step["id"]
step["status"]
step["action"]
step["tool"]
```

### 注意事项

这个函数返回的是字符串，不是 dict。

---

## get_next_pending_step(plan_state: dict) -> dict | None

### 功能

从 plan_state 里找到第一个状态为 `pending` 的步骤。

用于判断当前应该推进哪一步。

### 输入

| 参数         | 类型   | 说明       |
| ---------- | ---- | -------- |
| plan_state | dict | 带状态的任务计划 |

### 输出

找到 pending 步骤时：

```python
{
    "id": 1,
    "action": "这一步需要做什么",
    "tool": "工具名或 None",
    "status": "pending"
}
```

没有 pending 步骤时：

```python
None
```

### 内部逻辑

```text
1. 读取 plan_state.get("steps", [])
2. 遍历 steps
3. 把 status 转成小写并去掉空格
4. 找到第一个 status == "pending" 的 step
5. 返回该 step
6. 如果都没有，返回 None
```

### 注意事项

这个函数只找 `pending`，不会找 `running`、`failed` 或 `done`。

---

## update_step_status(plan_state: dict, step_id: int, status: str) -> dict

### 功能

根据 step_id 更新某一步的执行状态。

### 输入

| 参数         | 类型   | 说明                                        |
| ---------- | ---- | ----------------------------------------- |
| plan_state | dict | 带状态的任务计划                                  |
| step_id    | int  | 要更新的步骤 id                                 |
| status     | str  | 新状态，只能是 pending / running / done / failed |

### 输出

更新后的 plan_state。

### 成功示例

输入：

```python
update_step_status(plan_state, 1, "running")
```

结果：

```python
{
    "goal": "...",
    "steps": [
        {
            "id": 1,
            "action": "...",
            "tool": "read_file",
            "status": "running"
        }
    ]
}
```

### 异常情况

| 情况                       | 抛出异常       |
| ------------------------ | ---------- |
| status 不在 VALID_STATUS 中 | ValueError |
| plan_state 缺少 steps 字段   | KeyError   |
| 找不到对应 step_id            | ValueError |

### 注意事项

`step_id` 对应的是 plan_state 里的 `id` 字段，不是原始 plan 里的 `step` 字段。

---

## validate_plan_state(plan_state: dict) -> bool

### 功能

检查 plan_state 的结构是否合法。

### 输入

| 参数         | 类型   | 说明        |
| ---------- | ---- | --------- |
| plan_state | dict | 需要检查的计划状态 |

### 输出

合法时返回：

```python
True
```

不合法时抛出异常。

### 校验规则

```text
1. plan_state 必须是 dict
2. 必须包含 goal 字段
3. 必须包含 steps 字段
4. steps 必须是 list
5. 每个 step 必须包含 id / action / tool / status
6. 每个 step 的 status 必须属于 VALID_STATUS
```

### 单个 step 必须有的字段

```python
["id", "action", "tool", "status"]
```

### 异常情况

| 情况                 | 抛出异常       |
| ------------------ | ---------- |
| plan_state 不是 dict | TypeError  |
| 缺少 goal            | KeyError   |
| 缺少 steps           | KeyError   |
| steps 不是 list      | TypeError  |
| step 缺少必要字段        | KeyError   |
| step status 非法     | ValueError |

---

# 4. agent_utils.py

## pretty_print_task_log(task_log: list) -> None

### 功能

美化打印本轮工具调用记录。

它会尝试把 `arguments` 和 `result` 这两个字段里的 JSON 字符串解析成 dict，再用缩进格式打印出来。

### 输入

| 参数       | 类型   | 说明       |
| -------- | ---- | -------- |
| task_log | list | 本轮工具调用日志 |

### task_log 单项结构

```python
{
    "tool_name": "read_file",
    "arguments": "{\"file_name\": \"day07.md\"}",
    "success": True,
    "result": "{\"success\": true, \"content\": \"...\"}"
}
```

### 输出

无 return。

通过终端打印：

```text
1.
{
  "tool_name": "read_file",
  "arguments": {
    "file_name": "day07.md"
  },
  "success": true,
  "result": {
    "success": true,
    "content": "..."
  }
}
```

### 注意事项

| 字段        | 处理方式                    |
| --------- | ----------------------- |
| arguments | 如果是合法 JSON 字符串，就转成 dict |
| result    | 如果是合法 JSON 字符串，就转成 dict |
| 其他字段      | 原样保留                    |

如果 JSON 解析失败，不会报错，会保留原字符串。

---

## summarize_tool_result(tool_name: str, arguments: str, result_content: str) -> dict

### 功能

把完整工具结果压缩成简短摘要，给模型继续推理使用。

这样可以避免把大段文件内容反复塞进 messages，减少 token 消耗。

### 输入

| 参数             | 类型  | 说明                  |
| -------------- | --- | ------------------- |
| tool_name      | str | 工具名称                |
| arguments      | str | 工具调用参数，通常是 JSON 字符串 |
| result_content | str | 工具返回内容，通常是 JSON 字符串 |

### 输出

返回 dict 类型的工具执行摘要。

---

### JSON 解析失败时

如果 `result_content` 不是合法 JSON，返回：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "failed",
    "error_type": "JSONDecodeError",
    "error": "工具返回结果不是合法 JSON",
    "summary": result_content[:100]
}
```

---

### 工具执行失败时

如果工具返回的 JSON 中：

```python
success is False
```

返回：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "failed",
    "error_type": result.get("error_type"),
    "error": result.get("error")
}
```

---

### list_file 成功时

返回：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "success",
    "dir": result.get("dir"),
    "files": result.get("files")
}
```

---

### read_file 成功时

返回：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "success",
    "file": result.get("file"),
    "content_length": len(content),
    "summary": "文件已成功读取，完整内容已在上一条 tool message 中。"
}
```

### 注意事项

`read_file` 不会把完整 content 再放进 summary，只记录：

```python
content_length
summary
```

这样可以减少重复 token。

---

### count_file_chars 成功时

返回：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "success",
    "file": result.get("file"),
    "char_count": result.get("char_count"),
    "rule": result.get("rule")
}
```

---

### write_file / append_file 成功时

返回：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "success",
    "file": result.get("file"),
    "message": result.get("message")
}
```

---

### calculator 成功时

返回：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "success",
    "expression": result.get("expression"),
    "result": result.get("result")
}
```

---

### 其他工具成功时

返回通用摘要：

```python
{
    "tool_name": tool_name,
    "arguments": arguments,
    "status": "success",
    "summary": str(result)[:100]
}
```

### 注意事项

| 容易写错的点      | 正确写法                            |
| ----------- | ------------------------------- |
| 参数名         | `tool_name`                     |
| 参数名         | `arguments`                     |
| 参数名         | `result_content`                |
| 成功状态字段      | `status`                        |
| 工具真实成功字段    | `success`                       |
| JSON 解析错误字段 | `error_type: "JSONDecodeError"` |

---

## format_progress_log(progress_log: list) -> str

### 功能

把 progress_log 里的工具摘要 dict 转成给模型看的文本。

用于在工具调用后提醒模型：

```text
已经执行过哪些工具
参数是什么
状态是什么
摘要是什么
```

### 输入

| 参数           | 类型   | 说明       |
| ------------ | ---- | -------- |
| progress_log | list | 工具执行摘要列表 |

### progress_log 单项结构

```python
{
    "tool_name": "read_file",
    "arguments": "{\"file_name\": \"day07.md\"}",
    "status": "success",
    "summary": "文件已成功读取，完整内容已在上一条 tool message 中。"
}
```

### 输出

返回字符串。

### 输出示例

```text
1. 工具：read_file
   参数：{"file_name": "day07.md"}
   状态：success
   摘要：文件已成功读取，完整内容已在上一条 tool message 中。
```

### 注意事项

当前函数只固定输出：

```python
tool_name
arguments
status
summary
```

所以如果某些工具摘要里没有 `summary` 字段，比如 `list_file` 返回的是 `files`，这里的摘要可能会显示成：

```text
摘要：None
```

后续可以考虑优化成：

```python
item.get("summary") or item.get("files") or item.get("message") or item.get("result")
```

---

# 5. 当前项目核心数据结构

## plan

由 `make_plan()` 返回，表示“原始计划”。

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "工具名或 None"
        }
    ]
}
```

---

## plan_state

由 `init_plan_state()` 返回，表示“带执行状态的计划”。

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "id": 1,
            "action": "这一步需要做什么",
            "tool": "工具名或 None",
            "status": "pending"
        }
    ]
}
```

---

## task_log

给人看的完整工具调用记录。

```python
[
    {
        "tool_name": "read_file",
        "arguments": "{\"file_name\": \"day07.md\"}",
        "success": True,
        "result": "{\"success\": true, \"content\": \"...\"}"
    }
]
```

---

## progress_log

给模型看的简短工具执行摘要。

```python
[
    {
        "tool_name": "read_file",
        "arguments": "{\"file_name\": \"day07.md\"}",
        "status": "success",
        "file": "day07.md",
        "content_length": 1000,
        "summary": "文件已成功读取，完整内容已在上一条 tool message 中。"
    }
]
```

---

# 6. 最容易写错的字段对照表

| 场景              | 正确字段                                | 错误写法                  |
| --------------- | ----------------------------------- | --------------------- |
| 原始计划步骤列表        | `steps`                             | `step`                |
| 原始计划步骤编号        | `step`                              | `id`                  |
| plan_state 步骤编号 | `id`                                | `step`                |
| 当前步骤动作          | `action`                            | `task`                |
| 建议工具            | `tool`                              | `tool_name`           |
| 工具调用名称          | `tool_call.function.name`           | `tool_call.name`      |
| 工具调用参数          | `tool_call.function.arguments`      | `tool_call.arguments` |
| 工具返回内容          | `tool_msg["content"]`               | `tool_msg.content`    |
| 工具执行是否成功        | `result_data.get("success", False)` | 直接判断 tool_msg         |
| 无工具步骤           | `None`                              | `"None"`              |
| JSON 里的无工具      | `null`                              | `"null"`              |
| Python 里的无工具    | `None`                              | `null`                |
| 等待执行状态          | `"pending"`                         | `"wait"`              |
| 正在执行状态          | `"running"`                         | `"run"`               |
| 已完成状态           | `"done"`                            | `"success"`           |
| 执行失败状态          | `"failed"`                          | `"error"`             |

---

# 7. 当前执行链路速查

```text
用户输入
↓
run_agent()
↓
make_plan(user_input)
↓
build_planner_prompt()
↓
模型生成 plan
↓
clean_json_content(content)
↓
json.loads(content)
↓
validate_plan_tools(plan)
↓
init_plan_state(plan)
↓
validate_plan_state(plan_state)
↓
build_plan_progress_message(plan_state)
↓
模型判断是否需要 tool_call
↓
execute_tool_call(tool_call)
↓
summarize_tool_result(tool_name, arguments, result_content)
↓
update_step_status(plan_state, step_id, status)
↓
format_progress_log(progress_log)
↓
模型继续执行或生成最终回答
↓
pretty_print_task_log(task_log)
```

---

# 8. tool_executor.py

## tool_map

### 功能

保存“工具名字符串”和“真实 Python 函数”的映射关系。

模型返回的 tool_call 里只有工具名字符串，真正执行时需要通过 `tool_map` 找到对应的 Python 函数。

### 当前结构

```python
tool_map = {
    "calculator": calculator,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "list_file": list_file,
    "count_file_chars": count_file_chars
}
```

### 字段说明

| key                  | value               |
| -------------------- | ------------------- |
| `"calculator"`       | calculator 函数       |
| `"read_file"`        | read_file 函数        |
| `"write_file"`       | write_file 函数       |
| `"append_file"`      | append_file 函数      |
| `"list_file"`        | list_file 函数        |
| `"count_file_chars"` | count_file_chars 函数 |

### 注意事项

`tool_map` 里的 key 必须和 `tool_schema.py` 里声明的工具名完全一致。

例如：

```python
"read_file"
```

不能写成：

```python
"readfile"
"read_files"
"read_file_tool"
```

---

## execute_tool_call(tool_call) -> dict

### 功能

执行单个模型返回的 `tool_call`，并返回一条符合 messages 格式的 tool 消息。

它负责：

```text
1. 读取 tool_call.function.name
2. 读取 tool_call.function.arguments
3. 把 arguments 从 JSON 字符串解析成 dict
4. 检查工具名是否存在于 tool_map
5. 调用真实 Python 工具函数
6. 把工具结果包装成 role="tool" 的消息
7. 处理 JSON 解析错误、未知工具错误、工具执行异常
```

### 输入

| 参数        | 类型                        | 说明          |
| --------- | ------------------------- | ----------- |
| tool_call | CompletionMessageToolCall | 模型返回的工具调用对象 |

### 依赖字段

```python
tool_call.function.name
tool_call.function.arguments
tool_call.id
```

### 输出

返回 dict，结构为：

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": "JSON 字符串"
}
```

注意：`content` 是 JSON 字符串，不是 dict。

---

### 成功返回结构

如果工具执行成功：

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps(result, ensure_ascii=False)
}
```

其中 `result` 是真实工具函数返回的 dict，例如：

```python
{
    "success": True,
    "file": "...",
    "content": "..."
}
```

最终会被转成 JSON 字符串放进 `content`。

---

### arguments 解析失败时

如果：

```python
json.loads(tool_call.function.arguments)
```

失败，会返回：

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps({
        "success": False,
        "tool_name": function_name,
        "error_type": type(e).__name__,
        "error": str(e)
    }, ensure_ascii=False)
}
```

常见原因：

```text
1. arguments 不是合法 JSON 字符串
2. 模型返回了多余文本
3. 参数里缺少引号
4. 参数格式不是 dict
```

---

### 工具名不存在时

如果 `function_name` 不在 `tool_map` 里，会返回：

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps({
        "success": False,
        "tool_name": function_name,
        "error_type": "UnknownTool",
        "error": f"未知工具：{function_name}"
    }, ensure_ascii=False)
}
```

---

### 工具执行异常时

如果真实工具函数运行时报错，会返回：

```python
{
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
```

---

### 内部关键变量

| 变量            | 类型   | 说明       |
| ------------- | ---- | -------- |
| function_name | str  | 工具名      |
| function_args | dict | 工具参数     |
| result        | dict | 工具函数返回结果 |

### 调用真实工具的方式

```python
result = tool_map[function_name](**function_args)
```

### 注意事项

| 容易写错的点     | 正确写法                                       |
| ---------- | ------------------------------------------ |
| 工具名字段      | `tool_call.function.name`                  |
| 工具参数字段     | `tool_call.function.arguments`             |
| 工具调用 id    | `tool_call.id`                             |
| 参数解析       | `json.loads(tool_call.function.arguments)` |
| 调用工具       | `tool_map[function_name](**function_args)` |
| 返回消息角色     | `"tool"`                                   |
| 返回消息字段     | `"tool_call_id"`                           |
| 返回内容字段     | `"content"`                                |
| content 类型 | JSON 字符串                                   |

---

# 9. tool_schema.py

## tools

### 功能

声明当前模型可以调用哪些工具，以及每个工具需要什么参数。

这个文件给模型看。

真正执行工具的是：

```text
tool_executor.py
```

真正的工具函数定义在：

```text
tools.py
```

### tools 整体结构

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "工具名",
            "description": "工具描述",
            "parameters": {
                "type": "object",
                "properties": {
                    "参数名": {
                        "type": "参数类型",
                        "description": "参数说明"
                    }
                },
                "required": ["必填参数"]
            }
        }
    }
]
```

### 当前工具列表

| 工具名              | 功能             | 必填参数               |
| ---------------- | -------------- | ------------------ |
| calculator       | 执行数学计算         | expression         |
| read_file        | 读取文件内容         | file_name          |
| write_file       | 写入文件           | file_name, content |
| append_file      | 追加写入文件         | file_name, content |
| list_file        | 列出指定路径下的文件和文件夹 | 无                  |
| count_file_chars | 统计指定文件字数       | file_name          |

---

## calculator schema

### 功能

声明计算器工具。

### 结构

```python
{
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "用于执行数学计算，例如加减乘除、括号运算等。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "需要计算的数学表达式，例如 123*456"
                }
            },
            "required": ["expression"]
        }
    }
}
```

### 参数

| 参数         | 类型     | 是否必填 | 说明         |
| ---------- | ------ | ---- | ---------- |
| expression | string | 是    | 需要计算的数学表达式 |

### 对应真实函数

```python
calculator(expression: str)
```

---

## read_file schema

### 功能

声明读取文件工具。

### 参数

| 参数        | 类型     | 是否必填 | 说明       |
| --------- | ------ | ---- | -------- |
| file_name | string | 是    | 需要读取的文件名 |

### 对应真实函数

```python
read_file(file_name: str)
```

### 注意事项

参数名必须是：

```python
file_name
```

不能写成：

```python
filename
file
path
```

---

## write_file schema

### 功能

声明写入文件工具。

### 参数

| 参数        | 类型     | 是否必填 | 说明         |
| --------- | ------ | ---- | ---------- |
| file_name | string | 是    | 要写入的文件名    |
| content   | string | 是    | 要写入文件的具体内容 |

### 对应真实函数

```python
write_file(file_name: str, content: str)
```

---

## append_file schema

### 功能

声明追加写入文件工具。

### 参数

| 参数        | 类型     | 是否必填 | 说明           |
| --------- | ------ | ---- | ------------ |
| file_name | string | 是    | 要追加写入的文件名    |
| content   | string | 是    | 要追加写入文件的具体内容 |

### 对应真实函数

```python
append_file(file_name: str, content: str)
```

---

## list_file schema

### 功能

声明列出目录内容工具。

### 参数

| 参数   | 类型     | 是否必填 | 说明             |
| ---- | ------ | ---- | -------------- |
| path | string | 否    | 要查看的路径，默认是当前目录 |

### 对应真实函数

```python
list_file(path: str = ".") -> dict
```

### 注意事项

`required` 是空列表：

```python
"required": []
```

所以模型可以不传 `path`。

如果不传，真实函数会使用默认值：

```python
path = "."
```

---

## count_file_chars schema

### 功能

声明统计文件字符数工具。

### 参数

| 参数        | 类型     | 是否必填 | 说明         |
| --------- | ------ | ---- | ---------- |
| file_name | string | 是    | 需要统计字数的文件名 |

### 对应真实函数

```python
count_file_chars(file_name: str)
```

### 统计规则

真实函数里的规则是：

```text
不统计空格和换行，标点和数字会计入字符数
```

---

## tool_schema.py 注意事项

| 容易写错的点         | 正确写法                              |
| -------------- | --------------------------------- |
| 工具列表变量名        | `tools`                           |
| 工具类型           | `"type": "function"`              |
| 工具名位置          | `tool["function"]["name"]`        |
| 工具描述位置         | `tool["function"]["description"]` |
| 参数结构位置         | `tool["function"]["parameters"]`  |
| 必填参数字段         | `"required"`                      |
| 文件名参数          | `file_name`                       |
| 写入内容参数         | `content`                         |
| 计算表达式参数        | `expression`                      |
| list_file 路径参数 | `path`                            |

---

# 10. tools.py

## BASE_DIR

### 功能

定义工具函数操作文件时的基础目录。

### 当前代码

```python
BASE_DIR = Path(__file__).resolve().parent.parent
```

### 含义

`BASE_DIR` 是当前 `tools.py` 文件所在目录的上一级目录。

后续文件读写都会基于这个目录拼接路径：

```python
BASE_DIR / file_name
BASE_DIR / path
```

### 注意事项

如果你的项目结构是：

```text
agent_study/
├─ src/
│  └─ tools.py
├─ notes/
└─ docs/
```

那么：

```python
Path(__file__).resolve().parent
```

大概率是：

```text
agent_study/src
```

而：

```python
Path(__file__).resolve().parent.parent
```

就是：

```text
agent_study
```

所以当前工具默认操作的是项目根目录。

---

## calculator(expression: str) -> dict

### 功能

执行简单数学表达式计算。

### 输入

| 参数         | 类型  | 说明       |
| ---------- | --- | -------- |
| expression | str | 数学表达式字符串 |

### 输出

成功时：

```python
{
    "success": True,
    "expression": expression,
    "result": result
}
```

失败时：

```python
{
    "success": False,
    "expression": expression,
    "error_type": type(e).__name__,
    "error": str(e)
}
```

### 示例

```python
calculator("1 + 2 * 3")
```

返回：

```python
{
    "success": True,
    "expression": "1 + 2 * 3",
    "result": 7
}
```

### 注意事项

当前实现使用的是：

```python
eval(expression)
```

这在真实项目里有安全风险。

学习阶段可以先用，但后续如果要公开项目或接真实用户，建议换成更安全的表达式解析方式。

---

## read_file(file_name: str) -> dict

### 功能

读取项目目录下指定文件的内容。

### 输入

| 参数        | 类型  | 说明           |
| --------- | --- | ------------ |
| file_name | str | 要读取的文件名或相对路径 |

### 路径处理

```python
file_name = BASE_DIR / file_name
```

### 输出

成功时：

```python
{
    "success": True,
    "file": str(file_name),
    "content": "文件内容"
}
```

文件不存在时：

```python
{
    "success": False,
    "file": str(file_name),
    "error_type": "FileNotFoundError",
    "error": "文件不存在"
}
```

读取目标是文件夹时：

```python
{
    "success": False,
    "file": str(file_name),
    "error_type": "IsADirectoryError",
    "error": "这是一个文件夹，不是文件。请先使用 list_file 查看该目录下的文件。"
}
```

其他异常时：

```python
{
    "success": False,
    "file": str(file_name),
    "error_type": type(e).__name__,
    "error": str(e)
}
```

### 注意事项

| 容易写错的点 | 正确写法                   |
| ------ | ---------------------- |
| 参数名    | `file_name`            |
| 拼接路径   | `BASE_DIR / file_name` |
| 判断是否存在 | `file_name.exists()`   |
| 判断是否目录 | `file_name.is_dir()`   |
| 打开方式   | `"r"`                  |
| 编码     | `"utf-8"`              |
| 返回内容字段 | `content`              |

---

## write_file(file_name: str, content: str) -> dict

### 功能

把指定内容写入到项目目录下的指定文件中。

如果文件已存在，会覆盖原内容。

### 输入

| 参数        | 类型  | 说明           |
| --------- | --- | ------------ |
| file_name | str | 要写入的文件名或相对路径 |
| content   | str | 要写入的具体内容     |

### 路径处理

```python
file_name = BASE_DIR / file_name
```

### 输出

成功时：

```python
{
    "success": True,
    "file": str(file_name),
    "message": "文件写入成功"
}
```

失败时：

```python
{
    "success": False,
    "file": str(file_name),
    "error_type": type(e).__name__,
    "error": str(e)
}
```

### 注意事项

| 容易写错的点  | 正确写法        |
| ------- | ----------- |
| 参数名     | `file_name` |
| 内容参数名   | `content`   |
| 写入模式    | `"w"`       |
| 编码      | `"utf-8"`   |
| 是否覆盖原内容 | 会覆盖         |

---

## append_file(file_name: str, content: str) -> dict

### 功能

把指定内容追加写入到项目目录下的指定文件中。

不会覆盖原内容。

### 输入

| 参数        | 类型  | 说明             |
| --------- | --- | -------------- |
| file_name | str | 要追加写入的文件名或相对路径 |
| content   | str | 要追加写入的具体内容     |

### 路径处理

```python
file_name = BASE_DIR / file_name
```

### 输出

成功时：

```python
{
    "success": True,
    "file": str(file_name),
    "message": "文件写入成功"
}
```

失败时：

```python
{
    "success": False,
    "file": str(file_name),
    "error_type": type(e).__name__,
    "error": str(e)
}
```

### 注意事项

| 容易写错的点  | 正确写法        |
| ------- | ----------- |
| 参数名     | `file_name` |
| 内容参数名   | `content`   |
| 追加模式    | `"a"`       |
| 编码      | `"utf-8"`   |
| 是否覆盖原内容 | 不会覆盖，会追加到末尾 |

---

## list_file(path: str = ".") -> dict

### 功能

列出指定目录下的文件和文件夹。

默认列出项目根目录。

### 输入

| 参数   | 类型  | 默认值   | 说明       |
| ---- | --- | ----- | -------- |
| path | str | `"."` | 要查看的目录路径 |

### 路径处理

```python
dir_path = BASE_DIR / path
```

### 输出

成功时：

```python
{
    "success": True,
    "dir": str(dir_path),
    "files": "[dir] docs\n[file] README.md"
}
```

目录不存在时：

```python
{
    "success": False,
    "dir": str(dir_path),
    "error_type": "FileNotFoundError",
    "error": "目录不存在"
}
```

路径不是目录时：

```python
{
    "success": False,
    "dir": str(dir_path),
    "error_type": "NotADirectoryError",
    "error": "这个路径不是目录，不能列出文件"
}
```

其他异常时：

```python
{
    "success": False,
    "dir": str(dir_path),
    "error_type": type(e).__name__,
    "error": str(e)
}
```

### files 字段格式

目录：

```text
[dir] 文件夹名
```

文件：

```text
[file] 文件名
```

多个项目用换行拼接：

```python
"\n".join(items)
```

### 注意事项

| 容易写错的点   | 正确写法     |
| -------- | -------- |
| 参数名      | `path`   |
| 默认路径     | `"."`    |
| 返回目录字段   | `dir`    |
| 返回文件列表字段 | `files`  |
| 文件夹前缀    | `[dir]`  |
| 文件前缀     | `[file]` |

---

## count_file_chars(file_name: str) -> dict

### 功能

统计指定文件的字符数。

当前规则是：

```text
不统计空格和换行，标点和数字会计入字符数
```

### 输入

| 参数        | 类型  | 说明              |
| --------- | --- | --------------- |
| file_name | str | 要统计字符数的文件名或相对路径 |

### 路径处理

```python
file_name = BASE_DIR / file_name
```

### 核心逻辑

```python
char_count = sum(1 for ch in content if not ch.isspace())
```

### 输出

成功时：

```python
{
    "success": True,
    "file": str(file_name),
    "char_count": char_count,
    "rule": "不统计空格和换行，标点和数字会计入字符数"
}
```

失败时：

```python
{
    "success": False,
    "file": str(file_name),
    "error_type": type(e).__name__,
    "error": str(e)
}
```

### 注意事项

| 容易写错的点  | 正确写法                          |
| ------- | ----------------------------- |
| 参数名     | `file_name`                   |
| 返回字符数字段 | `char_count`                  |
| 统计规则字段  | `rule`                        |
| 不统计内容   | 空格、换行等 `isspace()` 为 True 的字符 |
| 会统计内容   | 中文、英文、数字、标点                   |

---

# 11. tool_schema.py / tool_executor.py / tools.py 三者关系

## 关系说明

```text
tool_schema.py：告诉模型有哪些工具、每个工具需要什么参数
tool_executor.py：接收模型返回的 tool_call，找到真实函数并执行
tools.py：真正实现工具功能
```

## 执行链路

```text
模型看到 tool_schema.py 里的 tools
↓
模型生成 tool_call
↓
tool_call.function.name
tool_call.function.arguments
↓
execute_tool_call(tool_call)
↓
json.loads(tool_call.function.arguments)
↓
tool_map[function_name](**function_args)
↓
调用 tools.py 里的真实函数
↓
真实函数返回 dict
↓
execute_tool_call 把 dict 转成 JSON 字符串
↓
返回 role="tool" 的消息
```

---

# 12. 工具参数对照表

| 工具名              | schema 参数          | 真实函数参数             | 是否一致 |
| ---------------- | ------------------ | ------------------ | ---- |
| calculator       | expression         | expression         | 一致   |
| read_file        | file_name          | file_name          | 一致   |
| write_file       | file_name, content | file_name, content | 一致   |
| append_file      | file_name, content | file_name, content | 一致   |
| list_file        | path               | path               | 一致   |
| count_file_chars | file_name          | file_name          | 一致   |

---

# 13. 工具返回结构对照表

| 工具               | 成功字段    | 主要结果字段     | 失败字段              |
| ---------------- | ------- | ---------- | ----------------- |
| calculator       | success | result     | error_type, error |
| read_file        | success | content    | error_type, error |
| write_file       | success | message    | error_type, error |
| append_file      | success | message    | error_type, error |
| list_file        | success | files      | error_type, error |
| count_file_chars | success | char_count | error_type, error |

---

# 14. 当前最重要的防错点

## 1. schema、tool_map、真实函数名必须一致

这三个地方必须都叫：

```python
read_file
```

不能一个叫：

```python
read_file
```

另一个叫：

```python
read_files
```

否则模型会调用成功，但执行器找不到工具。

---

## 2. schema 参数名必须和真实函数参数名一致

例如 schema 里是：

```python
"file_name"
```

真实函数也必须是：

```python
def read_file(file_name: str):
```

如果 schema 写成 `filename`，真实函数写成 `file_name`，执行这里会报错：

```python
tool_map[function_name](**function_args)
```

因为 Python 找不到对应参数。

---

## 3. tool_call.function.arguments 是字符串

模型返回的参数不是 dict，而是 JSON 字符串。

正确处理：

```python
function_args = json.loads(tool_call.function.arguments)
```

不能直接：

```python
function_args = tool_call.function.arguments
```

---

## 4. execute_tool_call 返回的是 tool message

返回结构必须类似：

```python
{
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": "JSON 字符串"
}
```

这里的 `role` 不要写成：

```python
"assistant"
"user"
```

---

## 5. 工具函数返回 dict，execute_tool_call 再转 JSON 字符串

真实工具函数返回：

```python
{
    "success": True,
    "result": 123
}
```

执行器包装时变成：

```python
"content": json.dumps(result, ensure_ascii=False)
```

---

## 6. list_file 的 path 是可选参数

schema 里：

```python
"required": []
```

真实函数里：

```python
def list_file(path: str = ".") -> dict:
```

所以模型不传 path 也能执行。

---

## 7. read_file 不能读取文件夹

如果传入的是目录，`read_file` 会返回：

```python
{
    "success": False,
    "error_type": "IsADirectoryError",
    "error": "这是一个文件夹，不是文件。请先使用 list_file 查看该目录下的文件。"
}
```

所以路径不确定时应该先用：

```python
list_file
```

---

## 8. write_file 会覆盖，append_file 会追加

| 函数          | 模式    | 效果      |
| ----------- | ----- | ------- |
| write_file  | `"w"` | 覆盖原文件   |
| append_file | `"a"` | 追加到文件末尾 |

---

## 9. count_file_chars 不统计空白字符

统计逻辑：

```python
not ch.isspace()
```

所以不会统计：

```text
空格
换行
tab
```

会统计：

```text
中文
英文
数字
标点
```

---

# 15. 当前完整模块关系补充

```text
agent.py
负责主循环，接收用户输入，调用 planner，执行工具，更新 plan_state。

planner.py
负责生成原始 plan，只规划，不执行。

plan_state.py
负责给 plan 增加状态，并维护 pending / running / done / failed。

agent_utils.py
负责打印日志、压缩工具结果、格式化 progress_log。

tool_schema.py
负责声明模型可调用的工具。

tool_executor.py
负责把模型的 tool_call 转成真实 Python 函数调用。

tools.py
负责实现真实工具能力，例如读文件、写文件、列目录、计算、统计字符数。
```

---

# 16. 当前完整调用链路补充版

```text
用户输入
↓
agent.py / run_agent()
↓
planner.py / make_plan(user_input)
↓
planner.py / build_planner_prompt()
↓
tool_schema.py / tools 提供工具列表
↓
模型返回原始 plan
↓
planner.py / clean_json_content(content)
↓
planner.py / validate_plan_tools(plan)
↓
plan_state.py / init_plan_state(plan)
↓
plan_state.py / validate_plan_state(plan_state)
↓
agent.py 把用户需求 + plan_state 加入 messages
↓
模型根据 tool_schema.py 决定是否生成 tool_call
↓
tool_executor.py / execute_tool_call(tool_call)
↓
tool_executor.py / tool_map 找到真实函数
↓
tools.py / calculator、read_file、write_file 等真实执行
↓
tool_executor.py 把结果包装成 role="tool" 的消息
↓
agent_utils.py / summarize_tool_result()
↓
plan_state.py / update_step_status()
↓
agent_utils.py / format_progress_log()
↓
模型继续执行或输出最终回答
↓
agent_utils.py / pretty_print_task_log()
```
