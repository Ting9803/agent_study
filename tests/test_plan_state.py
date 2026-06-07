from src.plan_state import (
    init_plan_state,
    get_next_pending_step,
    update_step_status,
    validate_plan_state,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_DONE
)


def test_plan_state():
    plan = {
        "goal": "测试任务",
        "steps": [
            {
                "step": 1,
                "action": "列出文件",
                "tool": "list_file"
            },
            {
                "step": 2,
                "action": "总结内容",
                "tool": None
            }
        ]
    }

    plan_state = init_plan_state(plan)

    validate_plan_state(plan_state)

    first_step = get_next_pending_step(plan_state)
    assert first_step["id"] == 1
    assert first_step["status"] == STATUS_PENDING

    update_step_status(plan_state, 1, STATUS_RUNNING)
    assert plan_state["steps"][0]["status"] == STATUS_RUNNING

    update_step_status(plan_state, 1, STATUS_DONE)
    assert plan_state["steps"][0]["status"] == STATUS_DONE

    second_step = get_next_pending_step(plan_state)
    assert second_step["id"] == 2

    print("plan_state 测试通过")


if __name__ == "__main__":
    test_plan_state()