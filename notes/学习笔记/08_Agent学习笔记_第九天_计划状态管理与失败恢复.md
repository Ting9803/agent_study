# Day08 Agent 学习笔记：计划状态管理与失败恢复

## 一、今天的学习目标

第八天的重点不是继续增加工具，而是让 Agent 在执行任务时能够追踪计划进度。

第七天已经完成了 planner、task_log、工具结果摘要和 progress_log。第八天在这个基础上继续推进：

> 从“知道调用了哪些工具”，升级到“知道任务执行到了哪一步、哪一步成功、哪一步失败、失败后怎么继续”。

---

## 二、Day07 和 Day08 的区别

### 1. Day07：记录工具调用

第七天主要完成的是工具调用记录：

```python
task_log = [
    {
        "tool_name": "read_file",
        "arguments": "...",
        "result": "...",
        "success": True
    }
]
```

它回答的是：

> 刚才调用了什么工具？

---

### 2. Day08：管理计划执行状态

第八天新增的是 `plan_state`：

```python
plan_state = {
    "goal": "读取第七天学习笔记并总结",
    "steps": [
        {
            "id": 1,
            "action": "列出 notes 文件夹",
            "tool": "list_file",
            "status": "done"
        },
        {
            "id": 2,
            "action": "读取第七天学习笔记",
            "tool": "read_file",
            "status": "done"
        },
        {
            "id": 3,
            "action": "总结学习内容",
            "tool": None,
            "status": "pending"
        }
    ]
}
```

它回答的是：

> 整个任务推进到哪一步了？

---

## 三、核心数据结构

### 1. plan

`plan` 是 planner 生成的静态计划。

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

注意：

- 外层是 `steps`
- 单个步骤里的编号字段是 `step`
- `plan` 不包含 `status`

---

### 2. plan_state

`plan_state` 是在 `plan` 的基础上增加执行状态后的结构。

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "id": 1,
            "action": "这一步需要做什么",
            "tool": "需要使用的工具名，如果不需要就写 None",
            "status": "pending"
        }
    ]
}
```

注意：

- 外层仍然是 `steps`
- 单个步骤的编号字段改成 `id`
- 新增 `status`
- `status` 可以是：`pending`、`running`、`done`、`failed`

---

## 四、今天新增的核心函数

### 1. init_plan_state(plan)

作用：把 planner 返回的静态计划转换成可追踪状态的 `plan_state`。

```python
def init_plan_state(plan):
    steps = []

    for index, step in enumerate(plan.get("steps", []), start=1):
        steps.append({
            "id": step.get("step", index),
            "action": step.get("action", ""),
            "tool": step.get("tool"),
            "status": "pending"
        })

    return {
        "goal": plan.get("goal", ""),
        "steps": steps
    }
```

这里的重点是：

```python
"id": step.get("step", index)
```

也就是把原始 `plan` 里的 `step` 转换成 `plan_state` 里的 `id`。

---

### 2. build_plan_progress_message(plan_state)

作用：把程序内部的 `plan_state` 转换成模型能看懂的文字提示。

```python
def build_plan_progress_message(plan_state):
    lines = []

    lines.append(f"当前任务目标：{plan_state['goal']}")
    lines.append("当前任务执行状态：")

    for step in plan_state["steps"]:
        lines.append(
            f"{step['id']}. [{step['status']}] {step['action']}，建议工具：{step['tool']}"
        )

    return "\n".join(lines)
```

这个函数表面上像是给人看的，其实主要是给模型看的。

它的作用是：

> 程序内部状态 → 模型可读提示词

---

### 3. get_next_pending_step(plan_state)

作用：找到第一个还没执行的步骤。

```python
def get_next_pending_step(plan_state):
    for step in plan_state.get("steps", []):
        status = str(step.get("status", "")).strip().lower()

        if status == "pending":
            return step

    return None
```

这个函数是状态机推进的关键。

每次工具调用前，先通过它找到当前要执行的步骤。

---

### 4. update_step_status(plan_state, step_id, status)

作用：根据步骤 id 更新状态。

```python
def update_step_status(plan_state, step_id, status):
    for step in plan_state.get("steps", []):
        if step.get("id") == step_id:
            step["status"] = status
            break

    return plan_state
```

这里今天踩了一个关键 bug：

```python
plan_state.get("step", [])
```

写成了单数 `step`，导致一直遍历空列表，状态永远不会更新。

正确写法是：

```python
plan_state.get("steps", [])
```

---

## 五、agent.py 中的执行逻辑

工具调用前：

```python
current_step = get_next_pending_step(plan_state)

if current_step:
    update_step_status(plan_state, current_step["id"], "running")
```

工具调用后：

```python
tool_msg = execute_tool_call(tool_call)
messages.append(tool_msg)

result_content = tool_msg["content"]

try:
    result_data = json.loads(result_content)
    success = result_data.get("success", False)
except json.JSONDecodeError:
    success = False

if current_step:
    if success:
        update_step_status(plan_state, current_step["id"], "done")
    else:
        update_step_status(plan_state, current_step["id"], "failed")
```

整体状态流转变成：

```text
pending → running → done / failed
```

---

## 六、工具结果摘要的调整

今天发现 `summarize_tool_result()` 返回的是 dict，不是字符串。

所以不能直接写：

```python
"\n".join(progress_log)
```

因为 `join()` 只能拼接字符串列表。

因此新增了类似 `format_progress_log(progress_log)` 的函数，把结构化摘要转换成模型可读文本。

分工变成：

```text
summarize_tool_result()  生成结构化摘要 dict
format_progress_log()   把摘要 dict 转成模型可读文本
```

这样 `progress_log` 既保留结构化信息，又能安全地塞回 messages。

---

## 七、失败恢复测试

今天完成了一个关键测试：

```text
帮我读取一个不存在的 abc.txt，如果失败，就列出当前目录
```

planner 生成的计划：

```json
{
  "goal": "读取不存在的 abc.txt 文件，如果失败则列出当前目录内容",
  "steps": [
    {
      "step": 1,
      "action": "尝试读取 abc.txt 文件",
      "tool": "read_file"
    },
    {
      "step": 2,
      "action": "如果读取失败，列出当前目录下的文件和文件夹",
      "tool": "list_file"
    }
  ]
}
```

实际执行结果：

```text
read_file → failed
list_file → done
```

最终 Agent 正确回答：

```text
读取 abc.txt 文件失败，因为该文件不存在。
以下是当前目录的内容：
...
```

这个测试说明：

- 工具失败后程序没有崩溃
- `plan_state` 能正确标记 failed
- 模型能根据失败状态继续执行下一步
- Agent 已经具备初步的失败恢复能力

---

## 八、今天整理的文档

今天还补充了项目文档，用来降低后续维护难度。

### 1. function_reference.md

用于记录：

- 每个函数的输入
- 每个函数的输出
- dict 的字段名
- 字段类型
- 哪些字段容易写错

重点记录了这些结构：

```text
plan
plan_state
tool_msg
task_log
progress_log
```

这个文档的作用是防止再次出现：

```python
steps 写成 step
id 和 step 混用
status 写错字段名
```

---

### 2. architecture.md

用 Mermaid 画了 Agent 执行流程图。

主要流程是：

```text
用户输入
→ make_plan
→ init_plan_state
→ build_plan_progress_message
→ 模型判断是否需要 tool_call
→ 执行工具
→ 根据 success 更新状态
→ 生成工具摘要
→ 继续执行或最终回答
```

---

### 3. data_structure_flow.md

用 Mermaid 画了核心数据结构流转图。

重点区分：

```text
plan.steps[].step
plan_state.steps[].id
```

这个图可以帮助以后快速看懂数据结构变化。

---

## 九、今天遇到的问题和解决方式

### 问题 1：plan 里到底该用 description 还是 action？

最开始示例里用了 `description`，但项目中的 planner 返回结构是：

```python
{
    "step": 1,
    "action": "这一步需要做什么",
    "tool": "..."
}
```

所以最终统一使用：

```python
action
```

避免字段名混乱。

---

### 问题 2：为什么 status 不直接放在 make_plan 里？

因为 `make_plan()` 只负责生成静态计划。

```text
make_plan()          生成静态计划
init_plan_state()    初始化动态执行状态
update_step_status() 更新执行进度
```

这样职责更清楚。

---

### 问题 3：为什么模型要看 plan_state？

因为程序内部的 dict，模型本身看不到。

所以需要：

```python
build_plan_progress_message(plan_state)
```

把程序状态转换成文字，再加入 `messages`。

---

### 问题 4：为什么状态一直不更新？

排查后发现 `update_step_status()` 里写错了 key：

错误写法：

```python
for step in plan_state.get("step", []):
```

正确写法：

```python
for step in plan_state.get("steps", []):
```

因为 `plan_state` 里是 `steps`，不是 `step`。

---

## 十、今天的收获

今天真正完成的是 Agent 的“执行状态管理”。

现在 Agent 不只是能调用工具，也能知道：

```text
哪一步还没做
哪一步正在做
哪一步成功了
哪一步失败了
失败后下一步该做什么
```

这一步让项目从普通 tool call demo 更接近真实工作流系统。

---

## 十一、后续可以优化的方向

### 1. 增加 validate_plan_state()

用于检查 `plan_state` 是否符合结构约定。

比如：

```python
if "steps" not in plan_state:
    raise KeyError("plan_state 缺少 steps 字段")
```

这样以后字段写错时，能更早暴露问题。

---

### 2. 增加状态常量

比如：

```python
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
```

避免手写字符串时拼错。

---

### 3. 优化 planner 输出

目前 planner 有时会把任务拆得太细，比如：

```text
列出 notes
进入 notes
查找文件
读取文件
总结
```

后续可以优化 prompt，让 planner 生成更简洁的步骤。

---

### 4. 增加测试文件

可以新建：

```text
tests/test_plan_state.py
```

测试：

```text
init_plan_state
get_next_pending_step
update_step_status
failed 状态更新
```

---

## 十二、README 可更新内容

```md
### Day08：计划状态管理与失败恢复

- 将 planner 生成的静态计划转换为可追踪的 plan_state
- 为每个计划步骤增加 pending / running / done / failed 状态
- 根据工具返回的 success 字段更新步骤状态
- 支持工具失败后的后续补救执行
- 增加 function_reference.md，记录核心 dict 的输入输出结构
- 使用 Mermaid 绘制 Agent 执行流程和数据结构流转图
```

---

## 十三、今日总结

第八天的核心成果是：

> 把 planner 的静态计划变成可执行、可追踪、可恢复的任务状态。

现在项目已经具备了比较清晰的执行闭环：

```text
规划任务 → 初始化状态 → 调用工具 → 更新状态 → 摘要结果 → 继续推进 → 最终回答
```

这一步是后续学习 MCP、RAG、多工具协作和更复杂 workflow 的基础。
