from typing import TypedDict, Literal, Optional


StepStatus = Literal["pending", "running", "done", "failed"]


class PlanStep(TypedDict):
    step: int
    action: str
    tool: Optional[str]


class Plan(TypedDict):
    goal: str
    steps: list[PlanStep]


class PlanStateStep(TypedDict):
    id: int
    action: str
    tool: Optional[str]
    status: StepStatus


class PlanState(TypedDict):
    goal: str
    steps: list[PlanStateStep]