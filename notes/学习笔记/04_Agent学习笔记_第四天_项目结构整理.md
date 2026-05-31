# 第四天学习笔记：Tools Agent 主流程整理

## 今天完成了什么

今天主要把前三天零散的 tools 调用代码，整理成了一个更清晰的小型 agent 项目结构。

目前项目拆成了四个核心文件：

```text
main.py
tools.py
tool_schema.py
tool_executor.py
```

每个文件的职责比之前更清楚了：

```text
tools.py          存放真实可执行的本地工具函数
tool_schema.py    存放给大模型看的 tools 工具声明
tool_executor.py  根据模型返回的 tool_call 执行对应工具
main.py           负责对话主流程、调用模型、维护 messages
```

这一天的核心目标不是增加很多功能，而是理解：

```text
模型负责判断要不要调用工具
Python 代码负责真正执行工具
工具执行结果再返回给模型
模型基于工具结果生成最终回答
```

---

## 一、tools.py：真实工具函数

`tools.py` 里面放的是 Python 真正会执行的函数。

目前实现了几个基础工具：

```text
calculator   执行简单计算
read_file    读取文件内容
write_file   写入文件内容
list_file    查看指定路径下的文件和文件夹
```

例如 `write_file` 使用：

```python
with open(file_name, "w", encoding="utf-8") as f:
    f.write(content)
```

这里 `"w"` 表示写入模式：

```text
文件不存在：自动创建
文件已存在：覆盖原内容
```

如果只是读取文件，就使用 `"r"`：

```text
"r" 读取文件，文件不存在会报错
"w" 写入文件，文件不存在会创建，文件存在会覆盖
"a" 追加写入，文件不存在会创建，文件存在会写到末尾
```

今天还复习了函数类型提示：

```python
def read_file(file_name: str) -> str:
```

其中：

```text
file_name: str 表示参数预期是字符串
-> str 表示函数预期返回字符串
```

但类型提示不会自动转换类型，只是给人和编辑器看的提示。

---

## 二、tool_schema.py：给模型看的工具说明书

`tool_schema.py` 里面的 `tools = [...]` 不是工具本身，而是给大模型看的工具声明。

它的作用是告诉模型：

```text
有哪些工具
每个工具叫什么
每个工具是干什么的
每个工具需要哪些参数
哪些参数是必填的
```

例如 `calculator` 的 schema 里包含：

```text
name: calculator
description: 用于执行数学计算
parameters: 需要 expression 参数
required: ["expression"]
```

也就是说，模型看到这个声明后，才知道自己可以这样调用工具：

```json
{
  "expression": "50+60"
}
```

今天理解到：

```text
tools.py 是给 Python 执行的
tool_schema.py 是给模型理解的
```

这两个文件虽然名字都和 tools 有关，但作用不同。

---

## 三、tool_executor.py：工具执行器

`tool_executor.py` 是今天最核心的部分之一。

它负责把模型返回的 `tool_call` 转成真实的 Python 函数调用。

核心流程是：

```text
拿到 tool_call
→ 取出工具名 function.name
→ 取出参数 function.arguments
→ json.loads 转成字典
→ 根据工具名去 tool_map 里找函数
→ 用 **function_args 执行函数
→ 把结果包装成 role=tool 的消息
→ 返回给 main.py
```

其中 `tool_map` 是工具名和真实函数的映射关系：

```python
tool_map = {
    "calculator": calculator,
    "read_file": read_file,
    "write_file": write_file,
    "list_file": list_file
}
```

模型返回的工具名只是字符串，例如：

```text
calculator
```

Python 不能直接执行字符串，所以需要 `tool_map` 把字符串映射成真实函数。

例如：

```python
result = tool_map[function_name](**function_args)
```

如果模型返回：

```json
{
  "name": "calculator",
  "arguments": "{"expression":"50+60"}"
}
```

实际执行效果相当于：

```python
calculator(expression="50+60")
```

---

## 四、main.py：主流程

`main.py` 负责把整个对话流程串起来。

当前主流程是：

```text
用户输入
→ 加入 messages
→ 调用大模型
→ 判断模型有没有返回 tool_calls
→ 如果有，执行工具
→ 把工具结果加入 messages
→ 再次调用模型
→ 输出最终回答
```

也就是：

```text
user message
assistant tool_call
tool result
assistant final answer
```

今天已经实现了基础的一轮工具调用流程。

例如用户输入：

```text
我昨天赚了50块，今天赚了60块，我这两天一共赚了多少钱
```

模型会调用 `calculator`，程序执行本地计算工具，然后模型根据工具结果回答：

```text
这两天一共赚了110块
```

---

## 五、messages 的作用

`messages` 是整个对话历史。

它不只保存用户和助手说过的话，也保存工具调用过程。

一次工具调用大概会在 `messages` 里形成这样的结构：

```text
system：你是一个可以调用本地工具的小助手
user：帮我计算 50+60
assistant：我要调用 calculator
tool：计算结果：110
assistant：这两天一共赚了110块
```

这里最重要的是：

```text
工具执行完以后，要把工具结果 append 回 messages
```

否则模型不知道工具执行结果是什么。

---

## 六、今天遇到的问题

### 1. content 里出现了重复答案和 think 标签

测试时模型返回过类似：

```text
答案...</think>答案...
```

这说明模型的思考内容或中间内容混进了最终 `content`。

解决方法是给请求加：

```python
thinking={"type": "disabled"}
```

这样可以关闭模型的思考输出，减少 `<think>` 或 `</think>` 混入回答的情况。

---

### 2. write_file 文件不存在时能不能写入

结论：

```text
open(file_name, "w") 可以在文件不存在时自动创建文件
```

但如果上级文件夹不存在，例如：

```text
data/poem.txt
```

而 `data` 文件夹不存在，就会报错。

当前阶段先处理普通文件即可。

---

### 3. 为什么复杂任务做不到

测试过这样的任务：

```text
调取 poem.txt 数一下有多少个字，然后和另一首15个字的诗相加
```

模型只调用了 `read_file`，最终没有正常回答。

原因是当前程序主要支持“一轮 tool call”：

```text
调用 read_file
→ 返回文件内容
→ 模型直接回答
```

但这个任务实际需要多步：

```text
读取文件
→ 统计字数
→ 计算总数
→ 输出答案
```

也就是多轮工具调用，或者需要新增专门的 `count_file_chars` 工具。

---

## 七、多轮 tool call 的思路

当前代码是单轮工具调用，后面可以改成循环结构：

```text
调用模型
→ 如果模型返回 tool_calls
→ 执行工具
→ 把工具结果加入 messages
→ continue 回到循环开头
→ 再调用模型
→ 直到模型不再返回 tool_calls
→ 输出最终回答
```

这样模型就可以连续调用多个工具，例如：

```text
read_file
→ calculator
→ final answer
```

这部分今天只理解思路，没有完全继续扩展。

---

## 八、下一步可以做什么

下一次可以从两个方向继续。

### 方向一：新增工具

可以加一个：

```text
count_file_chars
```

作用是统计文件字数。

这样复杂任务会更稳定：

```text
统计 poem.txt 字数
→ 再调用 calculator 计算总字数
```

### 方向二：支持多轮 tool call

把 `main.py` 里的工具调用逻辑改成循环，让模型可以连续调用多个工具，而不是只执行一轮。

---

## 九、今天的收获

今天真正理解了 tools agent 的基本结构：

```text
tool_schema.py：告诉模型有什么工具
tools.py：定义真实工具函数
tool_executor.py：把模型的 tool_call 变成真实函数调用
main.py：维护对话流程，把工具结果交还给模型
```

也理解了一个 agent 调用工具的完整链路：

```text
用户提出需求
→ 模型判断是否需要工具
→ 模型返回 tool_call
→ Python 执行本地工具
→ 工具结果写回 messages
→ 模型基于结果生成最终回答
```

这就是后面做本地文件操作、RAG、MCP、workflow 的基础。
