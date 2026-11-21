from typing import Iterable
from app.explain.human_readable import human_readable_decision

def build_decision_log(decision_ids: Iterable[str]) -> str:
    return "\n".join(["# Decision Summary", *[f"- {code}: {human_readable_decision(code)}" for code in decision_ids]])
