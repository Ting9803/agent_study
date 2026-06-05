# Agent Study

这是一个用于记录我从 0 开始学习 LLM Agent / AI 应用开发的练习项目。

这个仓库主要用于保存学习过程中的代码、笔记和踩坑记录。它不是生产级 Agent 框架，而是一个边学边写、边 debug 边复盘的实践项目。

目前学习重点包括：

- Python 调用大模型 API
- prompt 与多轮对话
- messages 上下文维护
- tools / function calling 基础流程
- 多轮 tool call
- 本地工具执行与结果回传
- 简单 Agent 执行逻辑
- 条件判断型 workflow
- 学习过程中的问题记录和踩坑总结

---

## 项目结构

```text
agent_study/
├── README.md
├── requirements.txt
├── .env.example
├── examples/        # 按学习顺序保存的练习代码
├── notes/           # 学习笔记和阶段性总结
├── src/             # 当前主要练习代码
└── tests/           # 临时测试代码
```

说明：

- `examples/`：保留从基础 API 调用到 tools / agent 的学习过程代码。
- `notes/`：保存每天的学习笔记、问题总结和复盘内容。
- `src/`：当前正在迭代的小型 Agent 练习代码。
- `tests/`：临时测试文件。

---

## 环境准备

建议使用 Python 虚拟环境。

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

### 2. 激活虚拟环境

Windows：

```bash
.venv\Scripts\activate
```

macOS / Linux：

```bash
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

当前主要依赖：

```text
zhipuai
python-dotenv
```

---

## API Key 配置

项目不会上传真实 API Key。

请在项目根目录新建 `.env` 文件：

```env
ZHIPUAI_API_KEY=your_api_key_here
```

仓库中只保留 `.env.example` 作为示例。

代码中通过环境变量读取：

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ZHIPUAI_API_KEY")
```

注意：

- `.env` 文件不要上传到 GitHub。
- `.gitignore` 中应包含 `.env`、`.venv/`、`__pycache__/` 等内容。
- 如果使用 PyCharm，可以把 `.idea/` 加入 `.gitignore`。

---

## 运行示例

运行某个练习文件：

```bash
python examples/01_basic_call.py
```

运行当前主要练习入口：

```bash
python src/main_05.py
```

如果使用 Windows 虚拟环境，可以先激活：

```bash
.venv\Scripts\activate
```

再运行对应文件。

---

## 当前学习内容

### 1. 基础 API 调用

学习如何通过 Python 调用大模型 API，并观察 SDK 返回结果结构。

重点包括：

- client 初始化
- prompt 输入
- response 返回结构
- 模型回复内容的读取方式

---

### 2. Prompt 与多轮对话

学习如何组织 `messages`，理解上下文在多轮对话中的作用。

重点包括：

- `system`
- `user`
- `assistant`
- 多轮 messages 追加
- 上下文如何影响模型回复

---

### 3. Tools / Function Calling

学习模型如何根据工具描述生成工具调用请求，以及本地代码如何解析参数、执行函数并回传结果。

当前已实现或练习过的工具包括：

- `calculator`
- `read_file`
- `write_file`
- `append_file`
- `list_file`
- `count_file_chars`

---

### 4. 多轮 Tool Call

练习让模型连续调用多个工具，完成一个多步骤任务。

基本流程：

```text
用户输入
→ 请求模型
→ 模型返回 tool_call
→ 本地执行工具
→ 工具结果作为 tool message 回传
→ 再次请求模型
→ 模型继续判断下一步
→ 最终回答
```

已经测试过的任务包括：

```text
写入 poem2.txt
读取 poem.txt 和 poem2.txt
分别统计字符数
计算总字符数
根据条件改写文件
重新统计并输出最终结果
```

---

### 5. 结构化 Tool Return

工具返回值统一使用结构化 `dict`，例如：

```python
return {
    "success": True,
    "file": file_name,
    "char_count": char_count,
    "rule": "不统计空格和换行，标点和数字会计入字符数"
}
```

失败时返回：

```python
return {
    "success": False,
    "error_type": type(e).__name__,
    "error": str(e)
}
```

这样模型可以更稳定地理解工具执行结果。

---

### 6. Tool Executor

`tool_executor.py` 负责根据模型返回的 tool call，找到对应工具并执行。

核心逻辑：

```python
result = tool_map[function_name](**function_args)
```

然后把工具返回结果转成 JSON 字符串，作为 `tool message` 的 `content`：

```python
content = json.dumps(result, ensure_ascii=False)
```

当前理解：

```text
tools.py          负责具体工具逻辑
tool_schema.py    负责描述工具能力和参数
tool_executor.py  负责分发工具和包装 tool message
main.py           负责对话循环和 messages 管理
```

---

### 7. 简单 Agent Workflow

目前已经跑通一个简单条件判断流程：

```text
统计 poem.txt 和 poem2.txt 的字符数
→ 判断总字符数是否超过 100
→ 如果超过，就改写 poem2.txt
→ 再次统计两个文件字符数
→ 输出最终结果
```

这一步开始从单纯的 function calling 过渡到简单 Agent workflow。

---

## 踩坑记录

学习过程中遇到并记录的问题包括：

- API Key 不应该写死在代码里
- `.env` 应该放进 `.gitignore`
- SDK 返回对象和普通字典不一样
- messages 需要持续追加，模型才能看到上下文
- tool call 的 arguments 是 JSON 字符串，需要 `json.loads`
- tool message 的 content 需要是字符串
- Python `dict` 放进 `content` 前建议用 `json.dumps`
- `return {{...}}` 会导致 `unhashable type: 'dict'`
- 工具参数名要和 schema 中的参数名保持一致
- 文件字符数统计需要明确规则，例如是否统计空格、换行、标点和数字

---

## 学习进度

目前大致进度：

```text
Day 01：基础 API 调用
Day 02：messages 与多轮对话
Day 03：tools / function calling 基础
Day 04：多轮 tool call 消化
Day 05：结构化 tool return、task_log、条件判断 workflow
```

后续计划：

```text
Day 06：简单 planner / 任务状态管理
后续：MCP、RAG、本地知识库、更多 Agent workflow 实践
```

---

## 说明

这个仓库主要用于展示学习过程、代码练习和阶段性理解。

代码会尽量保持简单、可运行、便于复盘。后续如果学习到新的 Agent 相关内容，会继续补充到 `examples/`、`src/` 和 `notes/` 中。
