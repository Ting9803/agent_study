# agent_study

这是一个用于学习 Agent 工程基础的 Python 项目。

项目从最基础的 tools 调用开始，逐步实现本地文件读写、工具执行、任务规划、计划状态管理、失败恢复和执行历史记录。当前目标不是直接使用成熟框架，而是通过手写代码理解 Agent 的核心运行机制。

## 当前已实现功能

* 基础工具调用

  * 数学计算
  * 读取文件
  * 写入文件
  * 追加写入文件
  * 列出目录
  * 统计文件字符数

* 多轮 tool call 执行

  * 模型可以连续调用多个工具
  * 工具结果会写回 messages
  * 模型根据工具结果继续执行或生成最终回答

* Planner 任务规划

  * 根据用户输入生成任务计划
  * 计划包含 goal 和 steps
  * 每个 step 包含 action 和建议 tool

* Plan State 状态管理

  * 将静态计划转换为可追踪的执行状态
  * 支持 pending / running / done / failed
  * 工具执行成功或失败后自动更新步骤状态
  * 支持失败后的后续任务推进

* 工具执行摘要

  * 将完整工具结果压缩成 progress_log
  * 避免重复把大段文件内容塞回模型上下文
  * 降低 token 消耗

* 执行历史记录

  * 新增 run_logger.py
  * 每次任务完成后写入 logs/run_history.jsonl
  * 记录 user_input、plan、final_plan_state、task_log、final_answer
  * 将 task_log 中的 arguments / result 从 JSON 字符串转成 dict，方便后续分析

## 项目结构

```text
agent_study/
│
├─ src/
│  ├─ main.py
│  ├─ agent.py
│  ├─ planner.py
│  ├─ plan_state.py
│  ├─ agent_utils.py
│  ├─ run_logger.py
│  ├─ tool_schema.py
│  ├─ tool_executor.py
│  ├─ tools.py
│  └─ config.py
│
├─ docs/
│  ├─ architecture.md
│  └─ function_reference.md
│
├─ notes/
│  └─ 学习笔记/
│
├─ logs/
│  └─ run_history.jsonl
│
├─ examples/
├─ tests/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ .gitignore
└─ LICENSE
```

## 核心执行流程

```text
用户输入
↓
planner 生成任务计划
↓
init_plan_state 初始化计划状态
↓
模型根据计划判断是否需要调用工具
↓
execute_tool_call 执行工具
↓
根据工具返回结果更新 plan_state
↓
summarize_tool_result 生成工具摘要
↓
模型继续执行或输出最终回答
↓
save_run_history 保存本轮执行记录
```

## 计划状态结构

原始计划结构：

```python
{
    "goal": "用户最终想完成什么",
    "steps": [
        {
            "step": 1,
            "action": "这一步需要做什么",
            "tool": "需要使用的工具名，如果不需要则为 None"
        }
    ]
}
```

执行状态结构：

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

当前支持的状态：

```text
pending：等待执行
running：正在执行
done：执行完成
failed：执行失败
```

## 执行历史记录

项目会将每次 Agent 执行过程保存到：

```text
logs/run_history.jsonl
```

每条记录包含：

```python
{
    "created_at": "记录创建时间",
    "user_input": "用户输入",
    "plan": "planner 生成的原始计划",
    "final_plan_state": "最终计划状态",
    "task_log": "工具调用记录",
    "final_answer": "最终回答"
}
```

这部分用于后续 debug、复盘、失败分析，以及未来扩展 memory / RAG。

## 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/Ting9803/agent_study.git
cd agent_study
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
```

Windows 下激活：

```bash
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 并创建 `.env`：

```text
ZHIPUAI_API_KEY=your_api_key_here
```

### 5. 启动项目

```bash
python src/main.py
```

## 示例任务

```text
帮我列出当前目录
```

```text
帮我读取一个不存在的 abc.txt，如果失败，就列出当前目录
```

```text
帮我列出 notes 目录，找到第八天学习笔记并读取出来，总结成 100 字以内
```

## 当前学习进度

* Day 01：理解 tools 基础链路
* Day 02：实现工具调用
* Day 03：多工具与本地文件操作
* Day 04：项目结构整理
* Day 05：错误处理
* Day 06：main 主流程整合
* Day 07：Planner 与进度提醒
* Day 08：计划状态管理与失败恢复
* Day 09：run_history 与 Agent 执行记录

## 后续计划

接下来计划继续学习：

```text
1. 本地知识检索
2. 轻量版 RAG
3. Markdown chunk 切片
4. embedding 与向量检索
5. MCP 工具协议
```

当前下一步会优先做本地知识检索，让 Agent 不只按路径读取文件，也能根据关键词搜索 notes / docs 中的相关内容。

## 说明

这个项目主要用于学习 Agent 的底层运行逻辑，因此暂时没有直接使用 LangChain、LlamaIndex 等成熟框架。

当前重点是通过手写代码理解：

```text
工具声明
工具执行
任务规划
状态管理
失败恢复
执行记录
后续记忆与 RAG 的基础数据结构
```
