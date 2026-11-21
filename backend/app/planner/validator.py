"""Fail-closed planner validation."""
class PlannerValidator:
    def __init__(self, candidates): self.candidates = candidates
    def validate(self):
        return [c for c in self.candidates if c.get("eligible") == "pass" and c.get("checks") and all(x.get("verdict") == "pass" for x in c["checks"])]
