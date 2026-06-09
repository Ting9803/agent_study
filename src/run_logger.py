import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
RUN_HISTORY_FILE = LOG_DIR / "run_history.jsonl"

def ensure_log_dir():
    """
    确保 logs 目录存在。
    """
    LOG_DIR.mkdir(exist_ok=True)

def save_run_history(
        user_input:str,
        plan:dict,
        final_plan_state:dict,
        task_log:list,
        final_answer:str
) -> None:
    """
       保存一次完整任务执行记录。

       使用 jsonl 格式：
       一行是一条 JSON 记录，方便后续追加、读取和分析。
    """
    ensure_log_dir()

    record = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_input": user_input,
        "plan": plan,
        "final_plan_state": final_plan_state,
        "task_log": normalize_task_log(task_log),
        "final_answer": final_answer
    }

    with open(RUN_HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def try_parse_json(value):
    """
    如果 value 是合法 JSON 字符串，就转成 dict/list。
    如果不是，就原样返回。
    """
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def normalize_task_log(task_log: list) -> list:
    """
    把 task_log 里的 arguments/result 从 JSON 字符串转成 dict。
    这样保存到 run_history.jsonl 以后更容易阅读和分析。
    """
    normalized = []

    for item in task_log:
        new_item = item.copy()

        if "arguments" in new_item:
            new_item["arguments"] = try_parse_json(new_item["arguments"])

        if "result" in new_item:
            new_item["result"] = try_parse_json(new_item["result"])

        normalized.append(new_item)

    return normalized

def load_run_history(limit:int = 5) -> list:
    """
    读取最近 limit 条历史执行记录。
    """
    ensure_log_dir()

    if not RUN_HISTORY_FILE.exists():
        return []

    with open(RUN_HISTORY_FILE,"r",encoding="utf-8") as f:
        lines = f.readlines()

    records = []

    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue

        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return records

if __name__ == "__main__":
    history = load_run_history(3)
    print(json.dumps(history, ensure_ascii=False, indent=2))
