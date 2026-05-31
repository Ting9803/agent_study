# 放tools清单的地方
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
         "description":"用于读取程序运行目录下指定文件的内容。",
         "parameters":{
             "type":"object",
             "properties":{
                 "file_name":{
                     "type":"string",
                     "description":"需要读取的文件名，如poem.txt"
                 }
             },
             "required":["file_name"]
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
                    "file_name":{
                        "type":"string",
                        "description":"要写入的文件名，如poem.txt"
                    },
                    "content":{
                        "type":"string",
                        "description":"要写入文件的具体内容"
                    }
                },
                "required":["file_name","content"]

            }
        }
    },
{
        "type":"function",
        "function":{
            "name":"append_file",
            "description":"用于把指定内容追加写入到指定的文件中",
            "parameters":{
                "type":"object",
                "properties":{
                    "file_name":{
                        "type":"string",
                        "description":"要追加写入的文件名，如poem.txt"
                    },
                    "content":{
                        "type":"string",
                        "description":"要追加写入文件的具体内容"
                    }
                },
                "required":["file_name","content"]

            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"list_file",
            "description":"列出指定路径下的文件和文件夹",
            "parameters":{
                "type":"object",
                "properties":{
                    "path":{
                        "type":"string",
                        "description":"要查看的路径，默认是当前目录"
                    }
                },
                "required":[]

            }
        }
    },
    {"type": "function",
     "function": {
         "name": "count_file_chars",
         "description": "用于统计指定文件的字数，标点符号和数字等也算在内。",
         "parameters": {
             "type": "object",
             "properties": {
                 "file_name": {
                     "type": "string",
                     "description": "需要读取的文件名，如poem.txt"
                 }
             },
             "required": ["file_name"]
         }
     }
     },


]