# Day 06：main.py 整合、项目路径与工具调用验证

## 一、今天目标

今天的目标不是重新写一套 tools，而是把前几天已经写好的工具调用能力整合起来，重点验证：

* `main.py` 是否能稳定处理多轮 tool call
* 工具函数是否能基于项目根目录读取和写入文件
* `tool_executor.py` 是否能正常执行工具并把结果回传给模型
* 工具返回 `dict` 后是否能被正确序列化
* agent 是否能完成“读取 + 总结 + 统计 + 追加”这类组合任务

今天最大的理解是：
如果 `main05` 已经支持多轮 tool call，那么第六天的 `main.py` 看起来和它很像是正常的。因为 agent 的主循环本来就是固定结构：用户输入、请求模型、处理工具调用、回灌工具结果、继续请求模型，直到模型给出最终回答。

---

## 二、今天主要做了什么

### 1. 保留原来的 tools / schema / executor

今天没有重写：

* `tools.py`
* `tool_schema.py`
* `tool_executor.py`

因为工具能力基本已经够用。

已有工具包括：

```python
calculator
read_file
write_file
append_file
list_file
count_file_chars
```

今天的重点是让这些工具在真实项目结构里稳定工作。

---

### 2. 重新整理 main.py 的主循环

`main.py` 的核心逻辑是：

```text
用户输入
→ messages 追加 user 消息
→ 请求模型
→ 模型返回 assistant 消息
→ 判断是否有 tool_calls
→ 如果有，执行工具并把 tool 结果追加进 messages
→ 再次请求模型
→ 如果没有 tool_calls，输出最终回答
```

外层循环负责持续聊天：

```text
外层 while：一轮一轮接收用户输入
```

内层循环负责处理当前这一轮里的工具调用：

```text
内层 while：只要模型还在调用工具，就继续执行工具并回灌结果
```

一轮对话结束的标志是：

```python
if not assistant_msg.tool_calls:
    print(assistant_msg.content)
    break
```

也就是说，只有模型不再请求工具时，才说明它已经可以给最终回答。

---

## 三、今天解决的重点问题：项目路径

### 1. 遇到的问题

`main.py` 放在 `src` 里，而学习笔记放在 `notes/学习笔记` 里。

项目结构大致是：

```text
agent_study/
├── notes/
│   └── 学习笔记/
│       └── 05_Agent学习笔记_第五天_错误处理.md
└── src/
    ├── main.py
    ├── tools.py
    ├── tool_schema.py
    └── tool_executor.py
```

如果直接用相对路径读取文件，很容易出现：

```text
FileNotFoundError
```

原因是程序运行时的当前目录不一定等于项目根目录。

---

### 2. 解决方式

在 `tools.py` 里设置项目根目录：

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
```

因为 `tools.py` 在 `src` 目录下：

```text
tools.py
→ parent 是 src
→ parent.parent 是 agent_study 项目根目录
```

所以后续所有文件操作都基于 `BASE_DIR`：

```python
file_name = BASE_DIR / file_name
```

这样输入：

```text
notes/学习笔记/05_Agent学习笔记_第五天_错误处理.md
```

就能正确找到项目根目录下的文件，而不需要写：

```text
../notes/学习笔记/xxx.md
```

---

## 四、tools.py 今天调整的关键点

### 1. list_file 的问题

一开始 `list_file` 里虽然计算了：

```python
dir_path = BASE_DIR / path
```

但是后面实际写成了：

```python
files = os.listdir(path)
```

这样还是会按当前运行目录查找，路径逻辑没有真正生效。

正确写法是：

```python
files = os.listdir(dir_path)
```

并且返回时最好把 `dir_path` 转成字符串：

```python
"dir": str(dir_path)
```

---

### 2. Path 对象要转成 str

工具返回结果里如果包含 `Path` 对象，后面可能会在 `json.dumps()` 时出错：

```text
TypeError: Object of type WindowsPath is not JSON serializable
```

所以返回文件路径时要写成：

```python
"file": str(file_name)
```

需要转成字符串的是路径，例如：

```python
"file": str(file_name)
"dir": str(dir_path)
```

不需要转成字符串的是普通数字，例如：

```python
"char_count": char_count
```

---

### 3. char_count 保持 int

`count_file_chars` 里的 `char_count` 不需要转成字符串。

原因是它本质上是数字，后面如果还要继续计算，比如两个文件字符数相加，保留 `int` 会更方便。

推荐写法：

```python
return {
    "success": True,
    "file": str(file_name),
    "char_count": char_count,
    "rule": "不统计空格、换行和制表符，标点和数字会计入字符数"
}
```

---

### 4. count_file_chars 用 isspace 更稳

原来只去掉：

```python
"\n"
" "
```

但这样不会处理：

```text
\t 制表符
\r Windows 换行符
```

所以更稳的写法是：

```python
char_count = sum(1 for ch in content if not ch.isspace())
```

这样所有空白字符都不会被统计。

---

## 五、今天的验证任务

今天验证 main.py 时，重点不是证明它“会调用工具”，而是验证它能不能在真实项目结构下稳定完成组合任务。

### 1. 验证项目根目录

测试指令：

```text
列出项目根目录下的文件
```

预期调用：

```text
list_file
```

如果能看到：

```text
notes
src
examples
```

说明路径已经基于项目根目录。

---

### 2. 验证读取 notes 文件

测试指令：

```text
读取 notes/学习笔记/05_Agent学习笔记_第五天_错误处理.md，然后总结内容
```

预期调用：

```text
read_file
```

这一步用于验证：

```python
BASE_DIR / file_name
```

是否能正确找到 `notes` 目录里的文件。

---

### 3. 验证写入第六天笔记

测试指令：

```text
帮我写一份第六天学习笔记到 notes/学习笔记/06_Agent学习笔记_第六天_main整合.md
```

预期调用：

```text
write_file
```

这一步用于确认文件是不是被写到了：

```text
notes/学习笔记/
```

而不是错误地写进：

```text
src/notes/学习笔记/
```

---

### 4. 验证读取 + 统计

测试指令：

```text
读取 notes/学习笔记/06_Agent学习笔记_第六天_main整合.md，并统计它有多少个字符
```

可能出现两种正常情况。

一种是模型一次返回多个工具调用：

```text
read_file
count_file_chars
```

另一种是模型分多轮调用：

```text
请求模型
调用 read_file
请求模型
调用 count_file_chars
请求模型
最终回答
```

只要最终能完成任务，两种都算正常。

---

### 5. 验证读取 + 总结 + 追加

测试指令：

```text
读取 notes/学习笔记/06_Agent学习笔记_第六天_main整合.md，总结成三句话，然后追加到 notes/learning_log.md
```

预期调用：

```text
read_file
append_file
```

这一步最接近真实 agent workflow，因为它不是单工具测试，而是组合任务。

---

### 6. 验证错误处理

测试指令：

```text
读取 notes/学习笔记/不存在的文件.md
```

预期结果：

```text
工具返回 success: false
error_type: FileNotFoundError
模型最终说明文件不存在
程序不崩溃
```

---

## 六、今天发现的关键问题：agent 会编学习笔记

今天还有一个重要发现：

agent 确实可以调用 `write_file` 写出一份 `.md` 学习笔记，但如果没有给它真实日志、真实代码或明确过程，它会根据上下文自动补全，写出一份“看起来很合理”的笔记。

比如它可能会编出：

* 实际没用过的模型名
* 实际没写过的日志系统
* 实际没遇到的性能问题
* 和当前项目结构不一致的代码示例
* 自相矛盾的测试结果

所以之后让 agent 写学习笔记时，不能只说：

```text
帮我写今天的学习笔记
```

更稳的做法是：

```text
先读取今天的代码、运行日志、我提供的学习记录，再基于真实内容总结，不要编造没有发生的内容。
```

这也是今天最有价值的收获之一：
agent 可以执行工具，但总结类任务必须有可靠上下文，否则很容易合理脑补。

---

## 七、今天的阶段性结论

今天第六天的核心不是学新工具，而是把前几天的工具调用能力放到真实项目结构中验证。

最终理解：

```text
tools.py：提供工具能力
tool_schema.py：告诉模型有哪些工具、参数怎么传
tool_executor.py：把模型的 tool_call 转成真实函数调用
main.py：负责管理对话循环、多轮工具调用和最终回答
```

main.py 和第五天相似是正常的，因为多轮 tool call 的核心结构不会变。

第六天真正新增的能力是：

```text
1. 工具函数统一基于项目根目录访问文件
2. Path 对象返回前要转成 str
3. char_count 保持 int
4. list_file 要用 dir_path，而不是 path
5. 通过真实组合任务验证 agent workflow
6. 意识到 agent 写总结时可能会编造，需要用真实日志约束
```

---

## 八、下一步

下一步可以继续做两件事：

### 1. 给 agent 加轻量日志

先不用复杂日志系统，只需要在 main.py 中打印：

```text
请求模型
模型返回几个 tool_calls
调用了哪个工具
工具参数是什么
工具结果是什么
最终回答是什么
```

这样方便观察每一轮模型请求和工具调用。

### 2. 开始进入 planner / 任务分解

在 tools 阶段收尾之后，可以开始学习更像 agent 的能力：

```text
任务拆解
任务状态管理
多步骤计划
错误恢复
简单 workflow
```

也就是让 agent 从“模型想调用什么工具就调用什么工具”，逐渐升级成“能先规划任务，再按步骤执行”。
