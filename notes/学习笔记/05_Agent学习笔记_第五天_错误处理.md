# Day 5：多工具调用、结构化返回与简单条件流程

## 一、今天完成了什么

今天主要围绕 **多轮 tool call** 继续练习，把原本“能调用工具”的小猫助手，推进到了“能连续调用多个工具、根据工具结果继续处理、最后整合结果回答”的状态。

今天完成的内容包括：

- 修复并测试了 `read_file`、`write_file`、`append_file`、`list_file`、`count_file_chars`、`calculator` 等工具。
- 将工具返回结果统一改成结构化 `dict`。
- 在 `tool_executor.py` 中使用 `json.dumps(result, ensure_ascii=False)` 把工具结果转成字符串，放进 `tool message` 的 `content`。
- 理解了 `description` 和 `tool message content` 的区别。
- 加入了 `task_log`，用于记录本轮工具调用过程。
- 跑通了一个带条件判断的简单 workflow：
  - 统计两个文件字符数
  - 判断总字符数是否超过 100
  - 如果超过，就改写 `poem2.txt`
  - 再重新统计并给出最终结果

---

## 二、核心理解

## 1. tool 的 return 可以返回结构化信息

工具的返回值不一定只能是一个简单结果，也可以包含更多信息，比如：

```python
return {
    "success": True,
    "file": file_name,
    "char_count": char_count,
    "rule": "不统计空格和换行，标点和数字会计入字符数"
}
```

这里面既有结果，也有规则说明。

这样模型拿到工具返回结果后，就能更稳定地回答用户，不容易把“字符数”说成严格意义上的“中文字数”。

---

## 2. description 和 content 作用不同

`description` 是工具调用前给模型看的，类似工具说明书。

例如：

```python
"description": "统计文件字符数。不统计空格和换行，标点和数字会计入字符数。"
```

它帮助模型判断什么时候该调用这个工具，以及这个工具大概怎么用。

`content` 是工具执行后返回给模型看的，属于本次工具调用的实际结果。

例如：

```json
{
  "success": true,
  "file": "poem.txt",
  "char_count": 34,
  "rule": "不统计空格和换行，标点和数字会计入字符数"
}
```

所以同一个规则可以同时写在 `description` 和工具返回值里：

- `description`：调用前说明
- `content`：调用后回执

---

## 3. tool message 的 content 必须是字符串

工具本身可以返回 Python 的 `dict`，但放进 `messages` 里的 `content` 时，需要转成字符串。

推荐写法：

```python
"content": json.dumps(result, ensure_ascii=False)
```

不要直接写：

```python
"content": result
```

也不太推荐长期使用：

```python
"content": str(result)
```

因为 `str(dict)` 是 Python 风格字符串，不是标准 JSON。

---

## 4. tool_executor 只负责分发和包装

现在的分工应该是：

```text
tools.py
负责具体工具逻辑，比如读文件、写文件、统计字符数、计算

tool_schema.py
负责告诉模型有哪些工具、每个工具需要什么参数

tool_executor.py
负责根据模型请求找到对应工具，执行后包装成 tool message

main.py
负责对话循环、messages 管理、多轮请求模型
```

所以不要把某个工具的业务规则硬写进 `tool_executor.py`。

例如 `count_file_chars` 的统计规则，应该写在 `tools.py` 里的 `count_file_chars` 返回值中，而不是写在 executor 里。

---

## 三、今天踩的坑

## 1. `read_file` 报错：unhashable type: 'dict'

报错内容：

```text
TypeError: unhashable type: 'dict'
```

原因是 `return` 外面多包了一层 `{}`，Python 把它当成了 `set`。

错误写法：

```python
return {{
    "success": True,
    "file": file_name,
    "content": content
}}
```

或者：

```python
return {
    {
        "success": True,
        "file": file_name,
        "content": content
    }
}
```

正确写法：

```python
return {
    "success": True,
    "file": file_name,
    "content": content
}
```

只需要一层大括号。

---

## 2. 参数名要统一

虽然这次的问题不是参数名导致的，但仍然要注意：

```text
tool_schema.py 里的参数名
tools.py 里的函数参数名
模型实际传入的 arguments
```

这三个地方要保持一致。

比如统一使用：

```python
file_name
```

那么 schema、函数定义、模型传参都要叫 `file_name`。

---

## 3. 不需要背一堆 Exception

现在阶段不用硬背各种错误类型。

够用写法是统一用：

```python
except Exception as e:
    return {
        "success": False,
        "error_type": type(e).__name__,
        "error": str(e)
    }
```

这样至少能知道：

- 工具失败了
- 失败类型是什么
- 具体报错信息是什么

以后遇到某个错误特别常见，再单独拎出来优化提示就行。

---

## 四、通用工具返回模板

以后写工具时，可以先套这个模板。

### 成功返回

```python
return {
    "success": True,
    "data": result
}
```

### 失败返回

```python
except Exception as e:
    return {
        "success": False,
        "error_type": type(e).__name__,
        "error": str(e)
    }
```

稍微完整一点可以写成：

```python
def xxx_tool(...):
    try:
        result = ...

        return {
            "success": True,
            "data": result,
            "meta": {}
        }

    except Exception as e:
        return {
            "success": False,
            "error_type": type(e).__name__,
            "error": str(e)
        }
```

其中：

```text
success：工具是否执行成功
data：真正的结果
meta：补充信息，比如文件名、统计规则等
error_type：错误类型
error：错误内容
```

---

## 五、tool_executor 当前推荐结构

`tool_executor.py` 的核心逻辑是：

```python
from tools import calculator, read_file, write_file, list_file, append_file, count_file_chars
import json

tool_map = {
    "calculator": calculator,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "list_file": list_file,
    "count_file_chars": count_file_chars
}

def execute_tool_call(tool_call):
    function_name = tool_call.function.name
    print(f"调用工具：{function_name}")

    try:
        function_args = json.loads(tool_call.function.arguments)
    except Exception as e:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps({
                "success": False,
                "tool_name": function_name,
                "error_type": type(e).__name__,
                "error": str(e)
            }, ensure_ascii=False)
        }

    if function_name not in tool_map:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps({
                "success": False,
                "tool_name": function_name,
                "error_type": "UnknownTool",
                "error": f"未知工具：{function_name}"
            }, ensure_ascii=False)
        }

    try:
        result = tool_map[function_name](**function_args)
        print(result)

        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, ensure_ascii=False)
        }

    except Exception as e:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps({
                "success": False,
                "tool_name": function_name,
                "arguments": function_args,
                "error_type": type(e).__name__,
                "error": str(e)
            }, ensure_ascii=False)
        }
```

这里最重要的是：

```python
result = tool_map[function_name](**function_args)
```

它表示根据模型请求的工具名，从 `tool_map` 中取出对应函数，并把模型传来的参数拆开传进去。

---

## 六、task_log 的作用

今天加了 `task_log`，用于记录每轮用户输入下，模型调用了哪些工具。

示例结构：

```python
task_log.append({
    "tool_name": tool_call.function.name,
    "arguments": tool_call.function.arguments,
    "result": tool_message["content"]
})
```

最终打印：

```python
print("本轮工具调用记录：")
for item in task_log:
    print(item)
```

更清晰一点可以加编号：

```python
print("本轮工具调用记录：")
for index, item in enumerate(task_log, start=1):
    print(f"{index}. {item}")
```

它的作用是帮助观察：

```text
模型请求了什么工具
传了什么参数
工具返回了什么
这些结果怎么一步步影响后续回答
```

这对后面学习 MCP、RAG、Agent workflow 很重要。

---

## 七、今天跑通的关键测试

## 测试 1：读取并统计两个文件

用户输入：

```text
你帮我读取一下 poem.txt 和 poem2.txt，然后算一下里面分别有多少字，再相加看看
```

工具流程：

```text
read_file
read_file
count_file_chars
count_file_chars
calculator
最终回答
```

结果：

```text
poem.txt：34 个字符
poem2.txt：72 个字符
总计：106 个字符
```

---

## 测试 2：条件判断并改写文件

用户输入：

```text
分别统计它们的字符数。
如果总字符数超过 100，就把 poem2.txt 改写成 30 字以内的小猫诗；
如果没有超过 100，就保持不变。
最后重新统计两个文件的总字符数，并告诉我最终结果。
```

工具流程：

```text
count_file_chars poem.txt
count_file_chars poem2.txt
write_file poem2.txt
count_file_chars poem.txt
count_file_chars poem2.txt
最终回答
```

结果：

```text
初始：
poem.txt：34 个字符
poem2.txt：119 个字符

因为总字符数超过 100，所以改写 poem2.txt。

最终：
poem.txt：34 个字符
poem2.txt：19 个字符
总计：53 个字符
```

这个测试说明已经跑通了一个简单的条件分支 workflow：

```text
读取状态
→ 统计状态
→ 判断条件
→ 修改文件
→ 再次验证
→ 输出最终结果
```

---

## 八、今天的阶段性结论

今天已经完成第五天核心目标：

```text
多工具调用：完成
结构化 tool return：完成
json.dumps 回传 tool message：完成
task_log 调用记录：完成
条件判断 + 改写 + 复查：完成
```

现在的小猫助手已经不只是“能调用工具”，而是可以完成一个简单的 agent workflow。

---

## 九、下一步

第六天可以开始做：

```text
简单 planner / 任务状态管理
```

目标是让 agent 从“模型自己临时决定下一步”，升级到：

```text
先理解任务目标
记录当前任务状态
根据中间结果更新状态
判断任务是否完成
最后输出总结
```

可以尝试的方向：

- 给任务生成简单计划
- 用 `task_state` 记录任务目标和完成情况
- 每次工具调用后更新状态
- 让最终回答基于状态总结
- 逐步过渡到更像 workflow 的结构
