# 09_Agent学习笔记：run_history 与 Agent 执行记录

## 一、今天的学习目标

第九天正式学习的重点不是继续增加工具，而是让 Agent 在完成任务后留下结构化执行记录。

之前 Agent 已经能完成：

```text
用户输入
↓
planner 生成计划
↓
plan_state 跟踪执行状态
↓
工具调用
↓
最终回答
```

今天新增的目标是：

```text
Agent 做完任务后，把完整执行过程保存下来，方便后续 debug、复盘和做记忆/RAG。
```

---

## 二、为什么需要 run_history

之前的 `task_log`、`progress_log`、`plan_state` 都只存在于当前程序运行过程中。

一旦程序结束，这些信息就消失了。

但真实 Agent 项目需要知道：

```text
用户问了什么
模型怎么规划
调用了哪些工具
工具参数是什么
工具返回了什么
哪一步失败了
最终回答是什么
```

所以今天新增了一个执行历史记录文件：

```text
logs/run_history.jsonl
```

---

## 三、jsonl 是什么

`jsonl` 是 JSON Lines 的缩写。

它的特点是：

```text
一行就是一条 JSON 记录
适合不断追加日志
适合后续逐行读取和分析
```

普通 JSON 可能是一个大数组：

```json
[
  {...},
  {...}
]
```

而 JSONL 是：

```json
{"created_at": "...", "user_input": "..."}
{"created_at": "...", "user_input": "..."}
```

这样每次保存新记录时，只需要追加一行，不需要重新读写整个文件。

---

## 四、新增文件：run_logger.py

今天新增了一个模块：

```text
src/run_logger.py
```

它负责保存和读取 Agent 的执行记录。

---

## 五、ensure_log_dir()

### 功能

确保 `logs` 目录存在。

```python
def ensure_log_dir():
    """
    确保 logs 目录存在。
    如果不存在就创建；如果已经存在就不报错。
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
```

### 关键理解

这个函数没有 `return`，因为它的作用不是返回结果，而是执行动作。

它执行的动作是：

```text
如果 logs 目录不存在，就创建
如果 logs 目录已经存在，就保持原样
```

### exist_ok=True 的含义

```python
LOG_DIR.mkdir(exist_ok=True)
```

意思是：

```text
如果目录已经存在，不要报错
```

如果不写 `exist_ok=True`，第二次运行时因为 `logs` 已经存在，可能会报：

```text
FileExistsError
```

### parents=True 的含义

```python
LOG_DIR.mkdir(parents=True, exist_ok=True)
```

意思是：

```text
如果中间父目录不存在，也一起创建
```

虽然当前只创建 `logs` 一层目录，但加上 `parents=True` 更稳。

---

## 六、save_run_history()

### 功能

保存一次完整任务执行记录。

```python
def save_run_history(
    user_input: str,
    plan: dict,
    final_plan_state: dict,
    task_log: list,
    final_answer: str
) -> None:
    """
    保存一次完整任务执行记录。
    """
```

### 保存内容

一条记录包含：

```text
created_at：记录创建时间
user_input：用户原始输入
plan：planner 生成的原始计划
final_plan_state：最终计划状态
task_log：工具调用记录
final_answer：最终回答
```

### 示例结构

```json
{
  "created_at": "2026-06-09 19:22:02",
  "user_input": "帮我读取一个不存在的 abc.txt，如果失败，就列出当前目录",
  "plan": {...},
  "final_plan_state": {...},
  "task_log": [...],
  "final_answer": "任务已完成..."
}
```

---

## 七、第一次保存日志时的问题

第一次保存成功后，发现 `task_log` 里的 `arguments` 和 `result` 是 JSON 字符串。

例如：

```json
"arguments": "{\"file_name\":\"abc.txt\"}"
```

```json
"result": "{\"success\": false, \"error\": \"文件不存在\"}"
```

这种格式虽然能用，但阅读起来很困难，因为里面有大量转义字符：

```text
\"
\\
\n
```

这说明：

```text
能保存日志，不代表日志适合后续分析。
```

---

## 八、normalize_task_log()

为了解决这个问题，新增了日志清洗函数。

### try_parse_json()

```python
def try_parse_json(value):
    """
    如果 value 是合法 JSON 字符串，就转成 dict/list。
    如果不是，就原样返回。
    """
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
```

这个函数用于安全解析 JSON 字符串。

如果能解析，就转成真正的 dict/list。

如果不能解析，就保留原字符串。

---

### normalize_task_log()

```python
def normalize_task_log(task_log: list) -> list:
    """
    把 task_log 里的 arguments/result 从 JSON 字符串转成 dict。
    这样保存到 run_history.jsonl 以后更容易阅读和分析。
    """
    normalized = []

    for item in task_log:
        new_item = item.copy()

        if "arguments" in new_item:
            new_item["arguments"] = try_parse_json(new_item["arguments"])

        if "result" in new_item:
            new_item["result"] = try_parse_json(new_item["result"])

        normalized.append(new_item)

    return normalized
```

### 优化后的 task_log

优化前：

```json
"arguments": "{\"file_name\":\"abc.txt\"}"
```

优化后：

```json
"arguments": {
  "file_name": "abc.txt"
}
```

优化前：

```json
"result": "{\"success\": false, \"error\": \"文件不存在\"}"
```

优化后：

```json
"result": {
  "success": false,
  "error": "文件不存在"
}
```

这样后续统计、搜索、分析都会更方便。

---

## 九、agent.py 中的接入方式

在 `agent.py` 中导入：

```python
from run_logger import save_run_history
```

在最终回答前保存执行记录：

```python
final_answer = answer.content

save_run_history(
    user_input=user_input,
    plan=plan,
    final_plan_state=plan_state,
    task_log=task_log,
    final_answer=final_answer
)

print(f"AI小助手：{final_answer}")
```

这样每次 Agent 完成一轮任务，就会自动写入一条执行历史。

---

## 十、测试任务

今天使用的测试任务是：

```text
帮我读取一个不存在的 abc.txt，如果失败，就列出当前目录
```

执行结果：

```text
1. read_file abc.txt
   结果：失败，文件不存在

2. list_file 当前目录
   结果：成功，列出了当前项目目录
```

最终 `run_history.jsonl` 中成功保存了：

```text
用户输入
原始计划
最终计划状态
工具调用记录
最终回答
创建时间
```

---

## 十一、今天学到的核心概念

### 1. 函数不一定需要 return

有些函数的目的不是返回结果，而是执行动作。

例如：

```python
ensure_log_dir()
```

它没有返回值，但会创建目录。

---

### 2. exist_ok=True 可以避免重复创建目录时报错

```python
LOG_DIR.mkdir(exist_ok=True)
```

表示：

```text
目录不存在就创建
目录存在就继续运行
```

---

### 3. jsonl 适合保存不断增长的执行日志

因为它可以一行一条记录，不需要每次重写整个 JSON 文件。

---

### 4. 日志应该结构化保存

不推荐长期保存这种形式：

```json
"arguments": "{\"file_name\":\"abc.txt\"}"
```

更推荐保存成：

```json
"arguments": {
  "file_name": "abc.txt"
}
```

这样后续才能方便做分析。

---

### 5. run_history 是后续 memory / RAG / debug 的基础

今天的日志记录以后可以用于：

```text
查看最近执行过哪些任务
统计哪些工具最常失败
分析 FileNotFoundError 出现频率
让 Agent 读取历史执行记录
把历史记录作为 RAG 数据来源
```

---

## 十二、关于 run_history 太长的问题

今天也发现了一个问题：

```text
完整 run_history 记录很长。
```

这是正常的。

完整日志主要用于 debug，不适合原封不动全部喂给模型。

后续可以分成三层：

### 1. full log

```text
logs/run_history.jsonl
```

保存完整执行过程，用于 debug。

### 2. summary log

```text
logs/run_summary.jsonl
```

只保存短摘要，例如：

```json
{
  "created_at": "2026-06-09 19:22:02",
  "user_input": "帮我读取 abc.txt...",
  "status": "completed_with_failed_step",
  "tools_used": ["read_file", "list_file"],
  "failed_tools": ["read_file"],
  "final_answer_summary": "abc.txt 不存在，已列出当前目录"
}
```

### 3. error log

```text
logs/error_history.jsonl
```

只保存失败工具调用，例如：

```json
{
  "tool_name": "read_file",
  "arguments": {
    "file_name": "abc.txt"
  },
  "error_type": "FileNotFoundError",
  "error": "文件不存在"
}
```

---

## 十三、后续学习方向

今天讨论了后续应该先学 RAG 还是 MCP。

当前更适合先学 RAG。

原因是当前项目已经具备 RAG 的前置条件：

```text
会读文件
会列目录
有 notes
有 docs
有 logs
已经遇到“文件越来越多，模型记不住”的问题
```

所以第十天建议先做一个轻量版本地知识检索工具：

```python
def search_local_notes(keyword: str, path: str = "notes") -> dict:
    """
    在 notes 目录下搜索包含 keyword 的 markdown 文件。
    返回匹配文件名和命中的文本片段。
    """
```

先用关键词搜索，不急着上向量库。

后续路线可以是：

```text
第10天：关键词版本地知识检索
第11天：markdown chunk 切片
第12天：embedding + 向量检索
再之后：MCP
```

---

## 十四、今天的阶段性成果

今天完成了：

```text
- 新增 run_logger.py
- 实现 ensure_log_dir()
- 实现 save_run_history()
- 生成 logs/run_history.jsonl
- 成功保存一次 Agent 执行记录
- 发现 task_log 字符串嵌套问题
- 新增 try_parse_json()
- 新增 normalize_task_log()
- 优化 task_log 保存结构
- 明确后续先学 RAG，再学 MCP
```

今天的重点是：

```text
Agent 不只是要会执行任务，还要能留下结构化执行痕迹。
```

这一步让项目从“会调用工具的小 demo”继续往“可复盘、可 debug、可扩展的 Agent 工程”靠近。

```
```
