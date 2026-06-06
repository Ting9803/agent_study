# Day 07：轻量 Planner、进度提醒与上下文管理

## 一、今天的学习目标

今天的主题从“继续加工具”转向了 **Planner / 任务规划**。

前几天已经跑通了：

```text
tools.py：具体工具函数
tool_schema.py：给模型看的工具声明
tool_executor.py：把 tool_call 转成真实函数调用
agent.py / main.py：管理 messages、多轮 tool call、最终回答
```

第七天的目标是让 Agent 从：

```text
用户提需求 → 模型直接决定调用什么工具 → 执行工具 → 回答
```

升级成：

```text
用户提需求 → Planner 先拆任务 → Agent 根据计划和工具结果继续执行 → 最终回答
```

今天最后形成的版本是：

```text
轻量 Planner + 单 Agent 执行 + tool_call 循环 + progress reminder + 简单上下文压缩
```

---

## 二、今天先讨论清楚的架构问题

今天一开始讨论了一个视频里的观点：很多人按教科书做 `Plan & Execute`，结果发现 Planner 经常越权，自己跑去执行，导致 Executor 显得很累赘。

今天形成的理解是：

```text
Plan & Execute 更像一种工作方式，不一定非要做成两个很重的 Agent。
```

也就是说，不一定要做成：

```text
主 Agent
↓
Planner Agent
↓
Executor Agent
↓
Tool Agent
```

当前学习阶段更适合做成：

```text
planner.py：只生成计划
agent.py：拿着计划继续走原来的 tool_call 主循环
tool_executor.py：只负责执行工具
```

Planner 不是为了让架构看起来更复杂，而是为了解决：

```text
复杂任务开始前，先让模型想清楚大概步骤。
```

---

## 三、今天对生产环境 Agent 的重要理解

今天讨论的重点不是“我能不能写一个 planner.py”，而是以后面对客户需求时，能判断一个 Agent 应该怎么设计架构。

今天总结出的几个生产环境问题：

```text
1. 长任务容易忘规则、偷步骤、越写越短、输出同质化。
2. Planner 不一定要独立成 Agent，它也可以只是一个规划阶段。
3. 子 Agent 的价值不一定是“分工好看”，更可能是“上下文隔离”。
4. Workflow / 状态机适合稳定业务流程，Agent 适合局部判断和生成。
5. 大任务不能只靠 messages 记忆，关键状态应该放在外部结构里。
6. 工具结果要结构化返回，不然模型容易误用工具或误解结果。
7. 是否使用 Planner、子 Agent、MCP、RAG，要看它到底解决什么问题。
```

今天还讨论了一个很重要的边界：

```text
Planner 不能执行任务，这句话不是绝对的。
更准确地说：Planner 可以拥有观察权，但尽量不要拥有修改权。
```

例如写代码场景里，Planner 合理的权限是：

```text
可以读取项目结构
可以读取关键代码文件
可以分析模块边界
可以生成函数拆分计划

但不要直接写文件
不要删除文件
不要提交代码
不要改数据库
不要发邮件
```

所以 Planner 的边界是灵活的，核心不是“能不能用工具”，而是：

```text
它能读什么？
它能不能改东西？
高风险动作要不要人工确认？
失败后谁来修正？
```

---

## 四、今天新增的文件结构

今天项目结构继续拆清楚：

```text
src/
├─ main.py              # 启动入口
├─ agent.py             # 主对话循环 / tool_call 循环
├─ planner.py           # 生成任务计划
├─ agent_utils.py       # 日志美化、进度摘要、当前进度提醒
├─ tools.py             # 本地工具函数
├─ tool_schema.py       # tools 声明，给模型看
├─ tool_executor.py     # 执行 tool_call
└─ config.py            # client / model name
```

今天最重要的拆分是：

```text
planner.py：负责规划
agent.py：负责主流程调度
agent_utils.py：负责辅助函数
```

这样 `agent.py` 不会越来越长。

---

## 五、补充 config.py

一开始发现 `config.py` 里还没有内容，所以先把模型 client 初始化放进去。

推荐结构：

```python
import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI

load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

model_Name = "glm-4.5-air"
```

今天代码里使用的是 `model_Name`，后面也可以统一改成更常见的常量命名：

```python
MODEL_NAME = "glm-4.5-air"
```

---

## 六、planner.py 的核心逻辑

Planner 的流程是：

```text
调用一次大模型
↓
让模型只生成任务计划
↓
拿到 content
↓
清洗可能存在的 ```json 代码块
↓
json.loads 转成 dict
↓
校验工具名是否合法
↓
返回 plan 给 agent
```

Planner 调模型时不传 `tools`，这样它没有真实工具调用权限。

---

## 七、Planner 里为什么要读取 tool_schema

一开始考虑在 planner 里手写工具列表：

```python
AVAILABLE_TOOLS = ["read_file", "write_file", ...]
```

后来发现这样不好。因为以后新增工具，就要同时改：

```text
tool_schema.py
planner.py
```

容易漏。

今天改成让 Planner 从 `tool_schema.py` 自动读取工具信息：

```python
from tool_schema import tools


def get_tool_infos() -> list[dict]:
    tool_infos = []

    for tool in tools:
        function_info = tool["function"]

        tool_infos.append(
            {
                "name": function_info["name"],
                "description": function_info.get("description", "")
            }
        )

    return tool_infos
```

这里踩过一个错：

```python
"description": function_info.get()["description", ""]
```

这是错的，因为 `get()` 要传 key。

正确写法是：

```python
"description": function_info.get("description", "")
```

---

## 八、build_planner_prompt 里的 f-string 大括号问题

今天还理解了为什么在 f-string 里写 JSON 示例时，要写双重大括号。

因为 f-string 里：

```python
{name}
```

表示变量替换。

如果想真的输出 JSON 的大括号：

```json
{
  "goal": "..."
}
```

在 f-string 里要写成：

```python
{{
  "goal": "..."
}}
```

简单记：

```text
{name}  → 变量替换
{{      → 输出真正的 {
}}      → 输出真正的 }
```

---

## 九、Planner Prompt 的优化

今天的 Planner Prompt 后来补充了几类约束：

```text
1. 只规划，不执行任务。
2. 不要声称已经读取文件、写入文件或完成计算。
3. 如果需要工具，只能从工具列表中选择。
4. 不允许发明工具名。
5. 不需要工具时，tool 字段写 null。
6. 输出纯 JSON，不要用 ```json 代码块。
7. 计划要尽量覆盖完整任务，不要只写第一步。
8. 如果路径或文件名不确定，要先 list_file 确认，再 read_file。
9. read_file 只能读取具体文件，不能读取目录。
```

因为测试时发现：

```text
用户说“notes 下面的学习笔记里，第五天学了什么”
模型如果不知道具体文件路径，就可能只规划第一步 list_file。
```

所以后来要求它尽量拆成：

```text
列出 notes
列出 notes/学习笔记
找到具体第五天文件
读取文件
总结内容
```

---

## 十、清洗 JSON：clean_json_content

第一次测试 Planner 时，模型返回了：

````text
```json
{
  "goal": "...",
  "steps": []
}
```
````

导致：

```python
json.loads(content)
```

解析失败。

所以增加了清洗函数：

```python
def clean_json_content(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content.replace("```json", "", 1).strip()

    if content.startswith("```"):
        content = content.replace("```", "", 1).strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    return content
```

这个函数解决的是：

```text
模型看起来返回了 JSON，但外面包了一层 markdown 代码块。
```

---

## 十一、校验工具名：validate_plan_tools

今天还发现 Planner 会发明不存在的工具名，比如：

```text
文件浏览器
文件搜索工具
文本查看工具
```

但实际工具名是：

```text
list_file
read_file
write_file
append_file
count_file_chars
calculator
```

所以加入校验函数：

```python
def validate_plan_tools(plan: dict) -> dict:
    valid_tool_names = {
        tool["function"]["name"]
        for tool in tools
    }

    for step in plan.get("steps", []):
        tool_name = step.get("tool")

        if tool_name in [None, "null", "None", ""]:
            step["tool"] = None
            continue

        if tool_name not in valid_tool_names:
            step["tool"] = None
            step["note"] = f"原工具名 {tool_name} 不在可用工具列表中，已置为 null"

    return plan
```

这里踩过几个点：

### 1. valid_tool_names 不要多包一层列表

错误写法：

```python
valid_tool_names = [
    {
        tool["function"]["name"]
        for tool in tools
    }
]
```

这会变成：

```python
[{"read_file", "write_file", ...}]
```

也就是列表里包了一个 set。

正确写法：

```python
valid_tool_names = {
    tool["function"]["name"]
    for tool in tools
}
```

### 2. 要遍历 `steps`，不是 `step`

错误写法：

```python
for step in plan.get("step", []):
```

正确写法：

```python
for step in plan.get("steps", []):
```

### 3. 写了 validate_plan_tools 之后要真的调用

错误逻辑：

```python
plan = json.loads(content)
return plan
```

正确逻辑：

```python
plan = json.loads(content)
plan = validate_plan_tools(plan)
return plan
```

### 4. 模型可能把 null 写成字符串

模型有时会返回：

```json
"tool": "null"
```

所以校验里要把这些都统一成 Python 的 `None`：

```python
if tool_name in [None, "null", "None", ""]:
    step["tool"] = None
    continue
```

---

## 十二、字典取值：`[]` 和 `.get()` 的区别

今天还复习了字典取值。

### `tool["function"]["name"]`

这是强制取值：

```text
我确定 tool 里一定有 function
我也确定 function 里一定有 name
如果没有，就应该报错
```

适合用于自己写的、结构稳定的 `tool_schema.py`。

### `plan.get("steps", [])`

这是安全取值：

```text
从 plan 里取 steps
如果没有 steps，就返回空列表 []
```

适合用于模型生成的内容，因为模型生成的 JSON 可能不稳定。

今天形成的理解是：

```text
tool_schema 是自己定义的，结构稳定 → 可以用 []
planner 的 plan 是模型生成的，结构不稳定 → 更适合用 get()
```

---

## 十三、agent.py 的改造

`agent.py` 里新增的核心流程是：

```python
plan = make_plan(user_input)
print("任务计划：")
print(json.dumps(plan, ensure_ascii=False, indent=2))
```

然后把用户原始需求和计划一起塞进 messages：

```python
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
```

这样 Agent 拿到的不再只是用户一句话，而是：

```text
原始需求 + Planner 生成的计划 + 执行约束
```

---

## 十四、遇到的问题：把目录当文件读

测试时输入：

```text
你帮我看看notes下面的学习笔记里面，第六天学了什么
```

一开始工具调用过程是：

```text
list_file notes → 返回 学习笔记
read_file notes/学习笔记 → PermissionError
```

当时看起来像权限问题：

```text
PermissionError: [Errno 13] Permission denied
```

后来判断出真正原因是：

```text
notes/学习笔记 是文件夹，不是文件。
Windows 上用 open() 读取文件夹，可能会报 PermissionError。
```

这不是没有权限，而是工具返回信息不够清楚，模型把目录当文件读了。

解决方式有两个：

### 1. list_file 返回文件类型

让 `list_file` 返回：

```text
[dir] 学习笔记
[file] 05_Agent学习笔记_第五天_错误处理.md
```

这样模型知道哪些是目录，哪些是文件。

### 2. read_file 识别目录

在 `read_file` 里先判断：

```python
if file_path.is_dir():
    return {
        "success": False,
        "file": str(file_path),
        "error_type": "IsADirectoryError",
        "error": "这是一个文件夹，不是文件。请先使用 list_file 查看该目录下的文件。"
    }
```

这个问题很典型：

```text
工具返回信息不够清楚，模型就会误用工具。
```

---

## 十五、Planner 只有一个 step 的问题

测试时还遇到过 Planner 只生成一个步骤：

```json
{
  "step": 1,
  "action": "列出notes目录下的文件和文件夹",
  "tool": "list_file"
}
```

但 Agent 后面仍然自己继续调用了：

```text
list_file
list_file
read_file
```

这说明当前结构是：

```text
Planner 给大方向
Agent 根据工具结果动态执行
```

这可以完成任务，但计划不够完整。

后来通过 Prompt 约束，让 Planner 尽量拆成完整步骤：

```text
1. 列出 notes
2. 进入 notes/学习笔记
3. 找到第五天文件
4. 读取第五天文件
5. 总结第五天内容
```

---

## 十六、加入当前进度提醒：Progress Reminder

今天引入了视频里提到的 Restatement 思想。

意思是：每次工具调用结束后，不只把工具结果塞回 messages，还额外追加一条“当前进度提醒”：

```text
当前任务计划是什么
已经完成了哪些工具调用
不要重复已完成步骤
如果还需要工具就继续调用
如果任务完成就直接回答
```

它解决的是：

```text
plan 一开始在上下文前面，后面消息越来越长，模型可能逐渐忘记原计划。
```

加入后流程变成：

```text
用户输入
↓
planner 生成 plan
↓
agent 把 plan 加进 messages
↓
模型调用工具
↓
工具结果 append 回 messages
↓
追加 progress reminder
↓
再次请求模型
```

在代码里，当前进度提醒要放在：

```text
for tool_call in answer.tool_calls 循环结束后
continue 前面
```

也就是：

```python
for tool_call in answer.tool_calls:
    tool_msg = execute_tool_call(tool_call)
    messages.append(tool_msg)
    ...

messages.append(build_progress_message(plan, progress_log))
continue
```

不能放进 `for` 循环里面，因为模型一次可能返回多个 tool_calls。

正确顺序是：

```text
assistant 发起 tool_calls
tool result 1
tool result 2
progress reminder
下一次请求模型
```

---

## 十七、今天发现的 token 爆炸问题

加入 progress reminder 后，又发现一个新问题：

```text
read_file 的完整文件内容已经在 tool message 里出现过一次。
progress reminder 里如果再放完整 task_log，就会把全文再塞一遍。
```

这会导致：

```text
1. token 成本变高
2. 上下文变脏
3. 弱模型更容易抓不到重点
4. 模型可能重复调用工具或忘记任务
```

所以今天进一步区分了两种日志：

```text
task_log：给人看的完整调试日志，可以最后打印在终端
progress_log：给模型看的简短进度摘要，不能重复塞全文
```

这也是今天很重要的上下文管理意识。

---

## 十八、新增 agent_utils.py

因为 `agent.py` 越来越长，所以今天新建了：

```text
agent_utils.py
```

用来放：

```text
pretty_print_task_log()
summarize_tool_result()
build_progress_message()
```

这样 `agent.py` 只保留主流程。

---

## 十九、summarize_tool_result：给模型看的短摘要

`progress_log` 不能直接保存完整工具结果，所以新增：

```python
def summarize_tool_result(tool_name: str, arguments: str, result_content: str) -> dict:
    ...
```

不同工具保留的信息不同：

### list_file

保留目录和文件列表：

```python
{
    "tool_name": "list_file",
    "status": "success",
    "dir": result.get("dir"),
    "files": result.get("files")
}
```

### read_file

不重复塞全文，只告诉模型已经读到文件：

```python
{
    "tool_name": "read_file",
    "status": "success",
    "file": result.get("file"),
    "content_length": len(content),
    "summary": "文件已成功读取，完整内容已在上一条 tool message 中。"
}
```

### count_file_chars

保留字符数和统计规则：

```python
{
    "tool_name": "count_file_chars",
    "status": "success",
    "file": result.get("file"),
    "char_count": result.get("char_count"),
    "rule": result.get("rule")
}
```

### write_file / append_file

保留写入状态和文件路径：

```python
{
    "tool_name": tool_name,
    "status": "success",
    "file": result.get("file"),
    "message": result.get("message")
}
```

### 工具失败

保留错误类型和错误信息：

```python
{
    "tool_name": tool_name,
    "status": "failed",
    "error_type": result.get("error_type"),
    "error": result.get("error")
}
```

---

## 二十、build_progress_message：只放进度摘要

今天最终使用的是：

```python
def build_progress_message(plan: dict, progress_log: list) -> dict:
    recent_progress = progress_log[-5:]

    return {
        "role": "user",
        "content": f"""
当前任务计划：
{json.dumps(plan, ensure_ascii=False, indent=2)}

已完成步骤摘要：
{json.dumps(recent_progress, ensure_ascii=False, indent=2)}

请根据以上进度继续完成任务。
不要重复已经完成的工具调用。
如果还需要工具，请继续调用工具。
如果任务已经完成，请直接给出最终回答。
不要假装已经完成未调用的工具操作。
"""
    }
```

这里的关键是：

```text
progress_message 只放摘要，不放完整文件内容。
```

这样既能提醒模型当前进度，又不会重复塞大段文本。

---

## 二十一、task_log 和 progress_log 的区别

今天最终形成的日志结构是：

```python
task_log = []
progress_log = []
```

### task_log

给人看，用于终端调试，保留完整结果：

```python
task_log.append({
    "tool_name": tool_name,
    "arguments": arguments,
    "result": result_content
})
```

### progress_log

给模型看，用于继续执行，保留简短摘要：

```python
progress_log.append(
    summarize_tool_result(
        tool_name=tool_name,
        arguments=arguments,
        result_content=result_content
    )
)
```

今天的理解是：

```text
给人看的完整日志 ≠ 给模型看的上下文状态
```

这是后面学习状态管理、RAG、workflow 的基础。

---

## 二十二、美化打印 task_log

原来的打印方式是：

```python
for index, item in enumerate(task_log, start=1):
    print(f"{index}.{item}")
```

输出很丑，而且 `arguments` 和 `result` 里面有很多转义字符。

今天改成在 `agent_utils.py` 里写：

```python
def pretty_print_task_log(task_log: list) -> None:
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
```

然后在 `agent.py` 里用：

```python
if task_log:
    print("本轮工具调用：")
    pretty_print_task_log(task_log)
```

这样输出会更容易看清：

```json
{
  "tool_name": "list_file",
  "arguments": {
    "path": "notes"
  },
  "result": {
    "success": true,
    "files": "[dir] 学习笔记"
  }
}
```

---

## 二十三、最终 agent.py 的核心结构

今天最后的 `agent.py` 主流程是：

```text
初始化 messages
↓
循环接收用户输入
↓
调用 make_plan(user_input)
↓
打印任务计划
↓
把用户原始需求 + 任务计划加入 messages
↓
初始化 task_log 和 progress_log
↓
请求模型
↓
如果有 tool_calls：
    追加 assistant tool_calls 消息
    执行每个工具
    工具结果加入 messages
    完整结果加入 task_log
    摘要结果加入 progress_log
    追加 progress reminder
    continue
↓
如果没有 tool_calls：
    输出最终回答
    美化打印 task_log
    break
```

今天这个版本已经从单纯 tool call agent 升级成：

```text
轻量 Planner + 执行循环 + 当前进度提醒 + 工具日志区分
```

---

## 二十四、今天成功跑通的测试

测试输入：

```text
帮我看看notes下面的学习笔记里面，第五天大概学了啥
```

Planner 输出了大致计划：

```text
1. 列出 notes 目录
2. 进入学习笔记子目录
3. 查找第五天文件
4. 读取第五天学习笔记
5. 总结第五天学习内容
```

实际工具调用是：

```text
list_file notes
list_file notes/学习笔记
read_file notes/学习笔记/05_Agent学习笔记_第五天_错误处理.md
```

说明：

```text
Planner 给完整路线，Agent 根据工具结果动态合并了“查找文件”这一步。
```

这是合理的，因为第二次 `list_file` 已经拿到了文件名，不需要额外工具调用。

---

## 二十五、今天最重要的阶段性结论

今天不是只写了一个 `planner.py`。

今天真正学到的是：

```text
1. Planner 是任务拆解机制，不是架构装饰。
2. Planner 可以只生成计划，不一定要做成独立重 Agent。
3. Planner 可以根据需要拥有只读工具权限，但修改权限要谨慎。
4. 计划不是死的，Executor 应该根据工具结果动态推进。
5. 长任务里要把关键进度推到上下文尾部，防止模型忘记任务。
6. 进度提醒不能重复塞完整工具结果，否则 token 会爆炸。
7. 给人看的完整日志和给模型看的上下文状态要分开。
8. 工具返回信息越清楚，模型越不容易误用工具。
9. 生产环境中，关键状态不能只靠 messages，要逐步外部化。
```

---

## 二十六、今天和生产环境的联系

今天遇到的问题都很像真实生产环境问题：

### 1. Planner 越权 / 乱规划

解决方向：

```text
Planner 不传 tools，或者只给只读工具。
Planner 输出计划后做工具名校验。
```

### 2. 模型不按 JSON 输出

解决方向：

```text
Prompt 约束 + clean_json_content + JSONDecodeError fallback。
```

### 3. 模型发明不存在的工具

解决方向：

```text
从 tool_schema 自动读取工具列表。
validate_plan_tools 校验工具名。
```

### 4. 模型误用工具

解决方向：

```text
工具返回更清晰的信息，比如 [dir] / [file]。
read_file 遇到目录时返回明确错误。
```

### 5. 长任务上下文污染

解决方向：

```text
progress reminder 放在上下文尾部。
progress_log 只放摘要，不重复放全文。
```

### 6. token 成本上升

解决方向：

```text
大内容只出现一次。
进度提醒只放摘要。
必要时只保留最近 N 条进度。
后续学习状态管理 / RAG / 任务队列。
```

---

## 二十七、下一步可以学什么

第七天已经完成了 Planner 入门。

下一步可以继续沿着这条线学：

```text
1. task_state：把任务状态结构化保存，而不是只靠 messages。
2. re-plan：工具结果和原计划不一致时，重新规划。
3. workflow：固定业务流程，不完全交给模型自由发挥。
4. context compression：长内容摘要、窗口裁剪、最近 N 条。
5. MCP：把工具接入方式标准化。
6. RAG：从大量资料中检索必要信息，而不是全部塞进上下文。
```

今天最适合记住的一句话：

```text
Planner 负责给方向，Executor 负责根据现实推进；进度要被记录，但不能把所有历史都塞回模型。
```
