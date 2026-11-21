"""Deterministic ordering of already eligible candidates; not a route sequence optimizer."""
class GreedyPlanner:
    def __init__(self, candidates): self.candidates = candidates
    def plan(self):
        eligible=[c for c in self.candidates if c.get("eligible") == "pass"]
        return sorted(eligible,key=lambda c:(c.get("baseline_score") is None, -(c.get("baseline_score") or 0), str(c.get("id",""))))
