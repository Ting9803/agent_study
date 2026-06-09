# AI_CONTEXT

## 项目目标

这是一个本地文件管理 + 学习记录 Agent 项目。
当前重点是学习 tools、planner、plan_state、tool call 执行循环，为后续 MCP / RAG 做准备。

## 当前已完成功能

- 支持多轮 tool_call
- 支持本地工具：
  - calculator
  - read_file
  - write_file
  - append_file
  - list_file
  - count_file_chars
- 支持 planner 生成 plan
- 支持 plan_state 管理执行状态
- 支持 task_log 记录完整工具调用
- 支持 progress_log 给模型看简短工具摘要
- 支持工具失败后的继续执行

## 当前核心文件

- main.py：启动入口
- agent.py：主循环
- planner.py：生成任务计划
- plan_state.py：管理计划执行状态
- tool_executor.py：执行 tool_call
- tools.py：具体工具函数
- tool_schema.py：工具 schema
- agent_utils.py：日志、摘要、格式化工具

## 当前核心数据结构

详见 docs/function_reference.md。

## 已经做过，不要重复设计

- task_log 已经存在
- summarize_tool_result 已经存在
- progress_log 已经存在
- build_progress_message 旧版已被 plan_state 流程替代
- plan_state 已支持 pending / running / done / failed

## 当前下一步

根据当天学习目标继续推进，不要重复设计已有模块。