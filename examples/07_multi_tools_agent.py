import os
import json
from zhipuai import ZhipuAI
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()

api_key = os.getenv("ZHIPUAI_API_KEY")

if not api_key:
    raise ValueError("请先在 .env 文件中配置 ZHIPUAI_API_KEY")

client = ZhipuAI(api_key=api_key)

def calculator(expression:str):
    """
    执行简单数学计算
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算失败{e}"

def read_file(filename:str):
    """
    读取当前目录下文件
    """
    try:
        #获取当前路径的文件夹
        base_dir = Path(__file__).parent
        #获取函数中指定的文件路径
        file_path = base_dir/filename

        if not file_path.exists():
            return f"文件不存在：{file_path}"
        return file_path.read_text(encoding="utf-8")

    except Exception as e:
        return f"读取失败{e}"


def write_file(filename:str , content:str):
    """
    写入文件到当前项目目录
    """
    try:
        #获取当前路径文件夹
        base_dir = Path(__file__).parent
        #文件路径
        file_path = base_dir/filename
        #写入文件
        file_path.write_text(content,encoding="utf-8")
        return f"已写入文件{file_path}"
    except Exception as e :
        return f"写入失败{e}"

#工具声明内容
tools =[{
    "type":"function",
    "function":{
        "name":"calculator",
        "description":"用于执行数学计算，例如加减乘除、括号运算等。",
        "parameters":{
            "type":"object",
            "properties":{
                "expression":{
                    "type":"string",
                    "description":"需要计算的数学表达式，例如 123*456"
                }
            },
            "required":["expression"]
        }
    }
},
    {"type":"function",
     "function":{
         "name":"read_file",
         "description":"用于读取当前目录下指定文件的内容。",
         "parameters":{
             "type":"object",
             "properties":{
                 "filename":{
                     "type":"string",
                     "description":"需要读取的文件名，如poem.txt"
                 }
             },
             "required":["filename"]
         }
     }
     },
    {
        "type":"function",
        "function":{
            "name":"write_file",
            "description":"用于把指定内容写入到当前项目目录指定的文件中",
            "parameters":{
                "type":"object",
                "properties":{
                    "filename":{
                        "type":"string",
                        "description":"要写入的文件名，如poem.txt"
                    },
                    "content":{
                        "type":"string",
                        "description":"要写入文件的具体内容"
                    }
                },
                "required":["filename","content"]

            }
        }
    }

]

#工具地图（找对应函数）
tool_map= {
    "calculator":calculator,
    "read_file":read_file,
    "write_file":write_file
}



def main():
    messages = [{
        "role": "system",
        "content":
            """假设你是一个可以调用工具的小猫，说话简洁明了，与人交流时需要用小猫语气
               需要计算时调用calculator，
               需要读取文件时调用read_file,
               需要写入文件时调用write_file。
            """
    }]
    while True:
        # 用户输入内容放进message中
        user_input = input("主人：")

        if user_input.lower() in ["q", "quit", "exit"]:
            print("小猫：下次再见喵～")
            break

        messages.append({
            "role": "user",
            "content": user_input
        })
        response = client.chat.completions.create(
            model="glm-4.5-air",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        assistant_response = response.choices[0].message
        # print(assistant_message)

        # 如果有toolcall，那就把它加到上下文里
        if assistant_response.tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": assistant_response.content or "",
                "tool_calls": [
                    tool_calls.model_dump()
                    for tool_calls in assistant_response.tool_calls
                ]
            }
            messages.append(assistant_msg)

            # 开始一个一个toolcall筛查
            for tool_call in assistant_response.tool_calls:
                result = execute_tool_call(tool_call)

                messages.append(result)

            # 拿到的结果要去喂给模型
            response = client.chat.completions.create(
                model="glm-4.5-air",
                messages=messages,
            )

            answer = response.choices[0].message.content
            messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )
            print(f"小猫：{answer}")
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_response.content or ""
                }
            )
            print(f"小猫：{assistant_response.content}")

def execute_tool_call(tool_call):
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)

    # 查工具地图看看应该用哪个工具函数,并调用函数拿到结果
    print("调用工具：", function_name)
    #找不到对应工具
    if function_name not in tool_map:
        return {
            "role":"tool",
            "tool_call_id":tool_call.id,
            "content":f"未知工具：{tool_call}"
        }
    #找得到
    try:
        #先找名字对应的功能函数
        func = tool_map[function_name]
        result = func(**function_args)
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": str(result)
        }
    except Exception as e:
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": f"工具调用错误：{e}"
        }


if __name__ == "__main__":
    main()