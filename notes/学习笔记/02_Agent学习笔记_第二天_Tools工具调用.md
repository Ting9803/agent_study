# Agent 学习笔记｜第二天：Tools 工具调用

> 学习范围：从 `05` 文件开始，围绕 tools、tool_calls、`CompletionMessageToolCall`、工具结果回填、多轮 loop 进行整理。

---

## 1. 本阶段学习主线

第二天的核心不是“写一个计算器函数”，而是理解一个最小版 Agent 的工具调用链路：

```text
用户输入
↓
模型根据 tools 描述判断是否需要工具
↓
如果需要，模型返回 tool_calls
↓
Python 读取 tool_call，解析函数名和参数
↓
Python 执行本地函数 / 外部 API / MCP 工具
↓
把工具结果用 role="tool" 放回 messages
↓
再次调用模型，让模型基于工具结果生成最终回复
```

一句话概括：

```text
模型负责判断和表达，工具负责执行，messages 负责把中间过程接起来。
```

---

## 2. tools 是什么

`tools` 不是官方已经提供好的工具。

更准确地说：

```text
tools 是你告诉模型：“我这边有哪些工具可以用。”
```

也就是说，模型本身并不知道你本地有什么函数。你需要按平台 API 文档的格式，把工具描述写进去。

例如：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学表达式计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "需要计算的数学表达式，例如 2+3"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]
```

这段描述告诉模型：

```text
我有一个工具，名字叫 calculate。
它可以执行数学表达式计算。
它需要一个参数 expression。
expression 是字符串。
```

但真正执行计算的，仍然是 Python 代码。

---

## 3. tools 和本地函数的关系

本地函数是真正干活的代码：

```python
def calculate(expression):
    return eval(expression)
```

`tools` 是给模型看的说明书：

```text
工具叫什么
工具能做什么
工具需要哪些参数
参数是什么类型
哪些参数必填
```

两者要对应：

```text
tools 里 function.name = "calculate"
Python 里也要有 calculate 这个函数
```

模型看到 `tools` 后，才知道自己可以请求调用 `calculate`。

但是：

```text
模型返回 tool_call ≠ 工具已经执行
```

模型只是发起请求，真正执行工具的是你的 Python 代码。

---

## 4. tools、外部 API、MCP、skill 的区别和相似处

### 4.1 相似处

它们都在解决同一个问题：

```text
让模型获得自己原本没有的能力。
```

| 类型 | 给模型补充的能力 |
|---|---|
| tools | 调用你定义的函数 |
| 外部 API | 调用远程服务，例如天气、数据库、业务系统 |
| MCP 工具 | 用标准化协议接入外部工具 |
| skill | 封装一套特定任务处理能力 |

### 4.2 区别

| 名称 | 更像什么 | 你负责什么 |
|---|---|---|
| tools | 工具说明书 | 描述函数名、用途、参数格式 |
| 本地函数 | 真正干活的代码 | 写具体执行逻辑 |
| 外部 API | 远程服务接口 | 用代码请求第三方服务 |
| MCP | 工具连接协议 / 工具中转站 | 用统一方式接入多个外部工具 |
| skill | 任务能力包 | 按固定流程处理文件、文档、表格、PPT 等任务 |

一句话区分：

```text
tools：告诉模型有哪些函数能调用。
外部 API：函数背后调用的是外部服务。
MCP：用标准协议把很多工具接进来。
skill：封装好的特定任务处理能力。
```

---

## 5. CompletionMessageToolCall 是什么

当模型判断需要工具时，它通常不会直接返回最终答案，而是返回一个工具调用请求。

这个请求就是你看到的：

```text
CompletionMessageToolCall
```

可以理解为：

```text
模型生成的一条“我要调用工具”的结构化消息。
```

里面通常包含：

| 字段 | 含义 |
|---|---|
| `id` | 这次工具调用的编号 |
| `type` | 工具类型，一般是 `function` |
| `function.name` | 模型想调用的函数名 |
| `function.arguments` | 模型传给函数的参数，通常是 JSON 字符串 |

示例：

```python
tool_call = assistant_message.tool_calls[0]

tool_call.id
tool_call.function.name
tool_call.function.arguments
```

可能得到：

```text
function.name = "calculate"
function.arguments = '{"expression": "2+3"}'
```

意思是：

```text
模型想调用 calculate 工具，参数是 expression = "2+3"。
```

---

## 6. 为什么必须保存 assistant_message

工具调用时，messages 里的顺序必须完整。

正确顺序是：

```text
user：用户提问
assistant：模型发起 tool_call
tool：工具返回结果
assistant：模型根据工具结果回答
```

也就是：

```python
messages.append({
    "role": "user",
    "content": user_input
})

response = client.chat.completions.create(
    model="xxx",
    messages=messages,
    tools=tools
)

assistant_message = response.choices[0].message

messages.append(assistant_message_dict)

messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": str(tool_result)
})
```

中间的 `assistant_message` 不能省。

原因是：

```text
role="tool" 的消息必须对应前面 assistant 发起的 tool_call。
```

如果不把 `assistant_message` 加进 messages，后面的 `role="tool"` 就会变成：

```text
这里有一个工具结果，但前面没有任何模型消息说要调用这个工具。
```

这样后续模型或 API 就可能找不到对应的前置工具调用。

---

## 7. function_args 为什么要用 json.loads

模型返回的 `function.arguments` 通常是 JSON 字符串，不是 Python 字典。

例如：

```python
tool_call.function.arguments
```

拿到的可能是：

```python
'{"expression": "2+3"}'
```

注意，它是字符串。

不能直接这样写：

```python
function_args = tool_call.function.arguments
result = calculate(**function_args)
```

因为 `**` 后面需要的是字典，不是字符串。

正确做法：

```python
import json

function_args = json.loads(tool_call.function.arguments)
```

这样它会从 JSON 字符串变成 Python 字典：

```python
{
    "expression": "2+3"
}
```

然后就可以：

```python
result = calculate(**function_args)
```

这等价于：

```python
result = calculate(expression="2+3")
```

---

## 8. `**function_args` 和手动取参数的区别

如果不用 `**function_args`，也可以手动取：

```python
result = calculate(function_args["expression"])
```

或者：

```python
expression = function_args["expression"]
result = calculate(expression)
```

但如果参数变多，手动拆会比较麻烦。

例如：

```python
{
    "city": "上海",
    "date": "明天",
    "unit": "celsius"
}
```

用 `**function_args`：

```python
get_weather(**function_args)
```

等价于：

```python
get_weather(city="上海", date="明天", unit="celsius")
```

所以 `**function_args` 的作用是：

```text
把字典里的 key-value 自动展开成函数参数。
```

---

## 9. 不要直接 append 对象，要转成 dict

API 返回的 `assistant_message` 看起来像消息，但它本质可能是对象，不一定是普通 Python 字典。

例如：

```python
assistant_message = response.choices[0].message
```

如果直接：

```python
messages.append(assistant_message)
```

后续请求可能不认。

智谱 AI 支持：

```python
assistant_message.model_dump()
```

可以把对象转成 Python 字典。

示例：

```python
assistant_message_dict = assistant_message.model_dump()
messages.append(assistant_message_dict)
```

`model_dump()` 可以理解为：

```text
自动把对象里的字段搬运成 dict。
```

不用自己手敲：

```python
{
    "role": assistant_message.role,
    "content": assistant_message.content,
    "tool_calls": assistant_message.tool_calls
}
```

---

## 10. model_dump 后要清理不需要的字段

`model_dump()` 的优点是省事，缺点是可能会带出一些不需要的字段。

例如：

```python
{
    "role": "assistant",
    "content": None,
    "tool_calls": [...],
    "audio": None,
    "reasoning_content": None
}
```

有些平台对多余字段、空字段比较敏感。

所以可以清理掉值为 `None` 的字段：

```python
assistant_message_dict = assistant_message.model_dump()

assistant_message_dict = {
    key: value
    for key, value in assistant_message_dict.items()
    if value is not None
}

messages.append(assistant_message_dict)
```

可以进一步封装成函数：

```python
def clean_message(message):
    message_dict = message.model_dump()
    return {
        key: value
        for key, value in message_dict.items()
        if value is not None
    }
```

之后使用：

```python
assistant_message_dict = clean_message(assistant_message)
messages.append(assistant_message_dict)
```

---

## 11. 单次工具调用流程

这是单次工具调用的基本思路：

```python
import json

messages = [
    {
        "role": "system",
        "content": "你是一只会说话的小猫。"
    },
    {
        "role": "user",
        "content": "主人昨天吃了2个小鱼干，今天吃了3个，一共吃了多少？"
    }
]

response = client.chat.completions.create(
    model="xxx",
    messages=messages,
    tools=tools
)

assistant_message = response.choices[0].message

assistant_message_dict = assistant_message.model_dump()
assistant_message_dict = {
    k: v
    for k, v in assistant_message_dict.items()
    if v is not None
}

messages.append(assistant_message_dict)

if assistant_message.tool_calls:
    tool_call = assistant_message.tool_calls[0]

    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)

    if function_name == "calculate":
        tool_result = calculate(**function_args)

    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": str(tool_result)
    })

    final_response = client.chat.completions.create(
        model="xxx",
        messages=messages
    )

    final_answer = final_response.choices[0].message.content
    print(final_answer)
else:
    print(assistant_message.content)
```

这个流程可以拆成三段：

```text
第一次调用模型：让模型判断是否需要工具
执行工具：Python 真正运行函数
第二次调用模型：让模型根据工具结果组织回复
```

---

## 12. loop 时要保存单次循环中的结果

单次工具调用跑通以后，就可以进入 loop。

loop 的关键是：

```text
每一轮用户输入、模型工具调用、工具结果、最终模型回复，都要正确保存到 messages。
```

否则会出现：

```text
上一轮信息丢了
工具结果没接上
模型不知道自己刚刚调用过工具
小猫人设断掉
下一轮上下文混乱
```

基本结构：

```python
while True:
    user_input = input("主人：")

    if user_input == "exit":
        break

    messages.append({
        "role": "user",
        "content": user_input
    })

    response = client.chat.completions.create(
        model="xxx",
        messages=messages,
        tools=tools
    )

    assistant_message = response.choices[0].message
    assistant_message_dict = clean_message(assistant_message)

    messages.append(assistant_message_dict)

    if assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name == "calculate":
                tool_result = calculate(**function_args)
            else:
                tool_result = f"未知工具：{function_name}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result)
            })

        final_response = client.chat.completions.create(
            model="xxx",
            messages=messages
        )

        final_message = final_response.choices[0].message

        print("AI小猫：", final_message.content)

        messages.append({
            "role": "assistant",
            "content": final_message.content
        })

    else:
        print("AI小猫：", assistant_message.content)
```

这里最关键的是保存：

```text
user 输入
assistant tool_call
tool 结果
assistant 最终回复
```

---

## 13. 总体编写思路

### 第一步：写本地工具函数

```python
def calculate(expression):
    return eval(expression)
```

这一层是真正干活的代码。

### 第二步：写 tools 描述

告诉模型：

```text
我有 calculate 工具。
它能计算表达式。
它需要 expression 参数。
```

### 第三步：准备 messages

```python
messages = [
    {
        "role": "system",
        "content": "你是一只会说话的小猫。"
    }
]
```

### 第四步：接收用户输入

```python
user_input = input("主人：")

messages.append({
    "role": "user",
    "content": user_input
})
```

### 第五步：第一次调用模型

让模型判断这句话是否需要调用工具：

```python
response = client.chat.completions.create(
    model="xxx",
    messages=messages,
    tools=tools
)
```

### 第六步：保存 assistant_message

```python
assistant_message = response.choices[0].message
messages.append(clean_message(assistant_message))
```

这一步不能漏，因为后面的 `role="tool"` 要对应这条 assistant 的 tool_call。

### 第七步：检查有没有 tool_calls

```python
if assistant_message.tool_calls:
    ...
else:
    ...
```

有工具调用就执行工具。没有工具调用就直接输出模型回复。

### 第八步：解析 function arguments

```python
function_args = json.loads(tool_call.function.arguments)
```

转成 Python 字典后：

```python
tool_result = calculate(**function_args)
```

### 第九步：把工具结果放回 messages

```python
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": str(tool_result)
})
```

这一步是在告诉模型：

```text
你刚刚要的工具结果回来了。
```

### 第十步：第二次调用模型，生成最终回复

```python
final_response = client.chat.completions.create(
    model="xxx",
    messages=messages
)
```

这一次通常不需要再传 `tools`，除非你允许它继续调用工具。

### 第十一步：保存最终回复

```python
final_message = final_response.choices[0].message

messages.append({
    "role": "assistant",
    "content": final_message.content
})
```

这一步是为了多轮对话继续保持上下文。

---

## 14. 本阶段犯过的错误和修正

### 14.1 把 tools 理解成官方提供的工具

修正：

```text
tools 只是工具描述。
真正的工具函数要自己写，或者自己接外部 API / MCP / 其他服务。
```

### 14.2 以为模型返回 tool_call 就等于工具已经执行

修正：

```text
tool_call 只是模型发出的调用请求。
Python 代码才是真正执行工具的地方。
```

### 14.3 没有把 assistant_message 放回 messages

修正：

```text
assistant 的 tool_call 是 tool 结果的前置消息。
如果不保存 assistant_message，后面的 role="tool" 就没有对应来源。
```

### 14.4 把 function.arguments 当成 Python 字典

修正：

```text
function.arguments 通常是 JSON 字符串。
要先 json.loads()，再变成 Python 字典。
```

### 14.5 不熟悉 `**function_args`

修正：

```python
calculate(**function_args)
```

等价于：

```python
calculate(expression=function_args["expression"])
```

如果参数多，用 `**` 更省事。

### 14.6 直接 append 对象

修正：

```python
message_dict = assistant_message.model_dump()
message_dict = {k: v for k, v in message_dict.items() if v is not None}
messages.append(message_dict)
```

### 14.7 单轮跑通后，loop 里忘了保存中间结果

修正：

loop 里要保存：

```text
user 输入
assistant tool_call
tool 结果
assistant 最终回复
```

不然多轮对话会断。

---

## 15. 最终版总结

这一天学习了官方 tools 工具调用流程。`tools` 不是平台已经提供好的工具，而是按照 API 文档写出来的工具描述，用来告诉模型：当前有哪些函数可以调用、函数名是什么、参数结构是什么。模型根据 `tools` 判断是否需要调用工具，如果需要，会返回 `CompletionMessageToolCall`，其中包含工具调用 id、函数名和 JSON 格式的 arguments。

真正执行工具的是 Python 代码。代码需要读取 `tool_call.function.name`，判断调用哪个本地函数；再用 `json.loads()` 把 `tool_call.function.arguments` 从 JSON 字符串转成 Python 字典，之后可以用 `**function_args` 直接传参。工具执行完成后，需要把结果用 `role="tool"` 放回 messages，并且带上 `tool_call_id`。

这里最关键的是，`assistant_message` 不能漏加到 messages 里，因为 `role="tool"` 的消息必须对应前面 assistant 发起的 tool_call。如果不保存 `assistant_message`，后续工具结果就找不到前置工具调用。由于 zhipuai 返回的 `assistant_message` 是对象，不适合直接 append，应该先用 `model_dump()` 转成 dict，再清理掉 `None` 等不需要的字段。

单次工具调用跑通后，进入 loop 时要注意保存每一轮中的模型结果，包括用户输入、assistant 的工具调用、tool 的执行结果、最终 assistant 回复。这样 Agent 才能在多轮对话中持续运行，并保持上下文。

---

## 16. 当前阶段你已经理解到的 Agent 核心

```text
Agent = LLM + tools + messages + loop + control logic
```

其中：

```text
LLM：负责理解用户意图和生成自然语言
tools：告诉模型有哪些能力可用
Python 函数：真正执行工具
messages：保存上下文和工具调用链路
loop：让 Agent 持续运行
control logic：负责判断、解析、清洗、分发、兜底
```

这部分已经进入 Agent 的核心：不是单纯会调 API，而是开始会组织“模型判断 → 工具执行 → 结果回填 → 继续对话”的完整链路。
