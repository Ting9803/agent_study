# agent_study

这是一个从零开始学习 AI Agent 的练习项目。项目重点不是直接使用现成框架，而是通过手写 Python 代码，理解 Agent 如何完成工具调用、多轮执行、文件读写、任务规划和进度管理。

当前阶段主要围绕本地文件管理与学习记录助手展开：让模型能够根据用户需求调用本地工具，读取文件、写入文件、列目录、统计字符数，并在复杂任务中先生成计划，再按工具执行结果继续推进。

## 当前能力

- 支持本地工具调用
  - `calculator`：执行简单计算
  - `read_file`：读取项目内文件
  - `write_file`：写入文件
  - `append_file`：追加文件内容
  - `list_file`：列出目录内容，并区分文件和文件夹
  - `count_file_chars`：统计文件字符数

- 支持多轮 tool call
  - 模型可以连续调用多个工具
  - 每次工具结果会回灌到 `messages`
  - 直到模型不再请求工具，输出最终回答

- 支持结构化工具返回
  - 工具返回统一使用 `dict`
  - `tool_executor.py` 负责将结果转成 JSON 字符串
  - 便于模型理解成功、失败、错误类型和具体结果

- 支持轻量 Planner
  - `planner.py` 会先根据用户需求生成任务计划
  - Planner 只负责规划，不直接执行任务
  - Planner 会从 `tool_schema.py` 自动读取可用工具信息，避免工具列表维护两份

- 支持进度提醒
  - 每轮工具调用后，会生成简短的 progress reminder
  - 避免模型忘记原始任务和当前进度
  - 将完整日志和模型可见摘要分开，减少上下文重复和 token 浪费

## 项目结构

```text
agent_study/
├── src/
│   ├── main.py              # 启动入口
│   ├── agent.py             # Agent 主循环，负责用户输入、模型请求、多轮 tool call
│   ├── planner.py           # 轻量任务规划器
│   ├── agent_utils.py       # 进度摘要、美化日志打印等辅助函数
│   ├── tools.py             # 本地工具函数
│   ├── tool_schema.py       # 工具声明，给模型看的工具说明
│   ├── tool_executor.py     # 根据模型 tool_call 执行真实 Python 函数
│   └── config.py            # 模型 client、模型名、环境变量配置
├── notes/
│   └── 学习笔记/             # 每日学习笔记
├── examples/                # 学习过程中的练习代码或示例
├── tests/                   # 后续测试代码
├── .env.example             # 环境变量示例
├── .gitignore
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
ZHIPUAI_API_KEY=你的 API Key
```

`.env` 文件不要提交到 GitHub。

### 3. 启动项目

```bash
python src/main.py
```

退出时输入：

```text
q
quit
exit
```

## 当前主流程

```text
用户输入
↓
planner.py 生成任务计划
↓
agent.py 把用户需求 + 任务计划加入 messages
↓
模型判断是否需要调用工具
↓
tool_executor.py 执行工具
↓
工具结果回灌 messages
↓
agent_utils.py 生成当前进度提醒
↓
模型继续判断下一步
↓
任务完成后输出最终回答
```

## 学习进度

### Day 01：Tools 基础链路

理解 tools 的基本概念，初步跑通模型调用本地函数的流程。

### Day 02：Tools 工具调用

继续练习工具声明、参数传递和模型如何选择工具。

### Day 03：多工具与本地文件操作

加入文件读取、写入等本地工具，开始理解工具与真实环境的连接。

### Day 04：项目结构整理

将工具函数、工具声明、执行器和主流程拆分到不同文件中，形成更清晰的项目结构。

### Day 05：错误处理、结构化返回与简单 workflow

统一工具返回格式，加入错误处理和 `task_log`，跑通“统计 → 判断 → 改写 → 复查”的简单条件流程。

### Day 06：main.py 整合、项目路径与工具调用验证

解决 `src` 与项目根目录之间的路径问题，让工具能够稳定访问 `notes` 等项目目录，并验证组合任务。

### Day 07：Planner 与进度提醒

加入轻量 Planner，让 Agent 在执行前先生成任务计划；同时加入 progress reminder，区分给人看的完整日志和给模型看的简短进度摘要，初步理解上下文管理和 token 成本问题。

## 当前重点理解

这个项目目前不是为了追求复杂架构，而是通过最小可运行代码理解 Agent 的几个核心问题：

```text
tools：Agent 如何连接外部能力
executor：模型请求如何变成真实函数调用
planner：复杂任务如何先拆步骤
progress reminder：长任务中如何提醒模型当前进度
日志：如何观察模型到底调用了什么工具、传了什么参数、拿到了什么结果
上下文管理：哪些内容应该完整保留，哪些内容应该压缩摘要
```

## 后续计划

- 继续完善 Planner 与任务状态管理
- 尝试加入 re-plan：根据工具结果动态调整计划
- 学习 MCP，理解工具接入的标准化方式
- 学习 RAG，理解如何让 Agent 检索和使用外部知识
- 增加测试用例，验证工具函数和主流程稳定性
