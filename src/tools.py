import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
#目前有的tools
def calculator(expression:str):
    """
    执行简单计算
    :param expression:
    :return:
    """
    try:
        result = eval(expression)

        return {
            "success": True,
            "expression": expression,
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "expression": expression,
            "error_type": type(e).__name__,
            "error": str(e)
        }
def read_file(file_name:str):
    """
    读取文件
    :param file_name:
    :return:
    """
    try:
        file_name = BASE_DIR/file_name
        if not file_name.exists():
            return {
                "success": False,
                "file": str(file_name),
                "error_type": "FileNotFoundError",
                "error": "文件不存在"
            }

        if file_name.is_dir():
            return {
                "success": False,
                "file": str(file_name),
                "error_type": "IsADirectoryError",
                "error": "这是一个文件夹，不是文件。请先使用 list_file 查看该目录下的文件。"
            }


        with open(file_name,"r",encoding="utf-8") as f:
            return {
                    "success": True,
                    "file": str(file_name),
                    "content": f.read()

            }

    except Exception as e:
        return {
            "success": False,
            "file": str(file_name),
            "error_type": type(e).__name__,
            "error": str(e)
        }

def write_file(file_name:str, content:str):
    """
    写入文件
    :param file_name:
    :param content:
    :return:
    """
    try:
        file_name = BASE_DIR / file_name
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "file": str(file_name),
            "message": "文件写入成功"
        }

    except Exception as e:
        return {
            "success": False,
            "file": str(file_name),
            "error_type": type(e).__name__,
            "error": str(e)
        }
def append_file(file_name:str, content:str):
    """
    追加写入文件
    :param file_name:
    :param content:
    :return:
    """
    try:
        file_name = BASE_DIR / file_name
        with open(file_name, "a", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "file": str(file_name),
            "message": "文件写入成功"
        }

    except Exception as e:
        return {
            "success": False,
            "file": str(file_name),
            "error_type": type(e).__name__,
            "error": str(e)
        }

def list_file(path: str = ".") -> dict:
    dir_path = BASE_DIR / path

    try:
        if not dir_path.exists():
            return {
                "success": False,
                "dir": str(dir_path),
                "error_type": "FileNotFoundError",
                "error": "目录不存在"
            }

        if not dir_path.is_dir():
            return {
                "success": False,
                "dir": str(dir_path),
                "error_type": "NotADirectoryError",
                "error": "这个路径不是目录，不能列出文件"
            }

        items = []

        for item in dir_path.iterdir():
            if item.is_dir():
                items.append(f"[dir] {item.name}")
            else:
                items.append(f"[file] {item.name}")

        return {
            "success": True,
            "dir": str(dir_path),
            "files": "\n".join(items)
        }

    except Exception as e:
        return {
            "success": False,
            "dir": str(dir_path),
            "error_type": type(e).__name__,
            "error": str(e)
        }


def count_file_chars(file_name:str):
    """
    读取文件字数，去掉空格和换行
    :param file_name:
    :return:
    """
    try:
        file_name = BASE_DIR / file_name
        with open(file_name, "r", encoding="utf-8") as f:
            content = f.read()

        char_count = sum(1 for ch in content if not ch.isspace())


        return {
            "success": True,
            "file": str(file_name),
            "char_count": char_count,
            "rule": "不统计空格和换行，标点和数字会计入字符数"
        }

    except Exception as e:
        return {
            "success": False,
            "file": str(file_name),
            "error_type": type(e).__name__,
            "error": str(e)
        }