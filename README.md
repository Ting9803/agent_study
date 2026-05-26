# Agent Study

这是一个用于记录我学习 LLM Agent / AI 应用开发过程的练习项目。

项目会随着学习进度持续更新，内容不限定在某一个技术点。目前主要包括：

- Python 调用大模型 API
- prompt 与多轮对话
- tools / function calling 的基础流程
- 简单 Agent 执行逻辑
- 学习过程中的问题记录和踩坑总结

这个仓库更偏向学习实践和过程复盘，不是完整的生产级框架。

## 项目结构

```text
agent_study/
├── README.md
├── requirements.txt
├── .env.example
├── examples/   # 练习代码
├── notes/      # 学习笔记
└── tests/      # 临时测试代码
```

## 环境准备

建议使用 Python 虚拟环境。

安装依赖：

```bash
pip install -r requirements.txt
```

当前主要依赖：

```txt
zhipuai
python-dotenv
```

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

## 运行示例

例如运行某个练习文件：

```bash
python examples/01_basic_call.py
```

如果使用 Windows 虚拟环境，可以先激活：

```bash
.venv\Scripts\activate
```

再运行对应文件。

## 学习内容

### 1. 基础 API 调用

学习如何通过 Python 调用大模型 API，并观察返回结果结构。

### 2. Prompt 与多轮对话

学习如何组织 `messages`，理解上下文在多轮对话中的作用。

### 3. Tools / Function Calling

学习模型如何根据工具描述生成工具调用请求，以及本地代码如何解析参数、执行函数并回传结果。

### 4. 简单 Agent 流程

尝试把“用户输入 → 模型判断 → 工具调用 → 结果回传 → 模型回复”的过程串起来，理解 Agent 的基本执行逻辑。

### 5. 踩坑记录

记录学习过程中遇到的问题，例如：

- 文件路径读取
- API Key 管理
- JSON 参数解析
- 消息历史维护
- SDK 返回对象与普通字典的区别

## 说明

这个仓库主要用于展示学习过程、代码练习和阶段性理解。

代码会尽量保持简单、可运行、便于复盘。后续如果学习到新的 Agent 相关内容，会继续补充到 `examples/` 和 `notes/` 中。
