"""Hard eligibility gate. ML is never called for failed or unknown candidates."""
class Gating:
    def is_allowed(self, candidate: dict) -> bool:
        checks = candidate.get("checks")
        return bool(checks) and candidate.get("eligible") == "pass" and all(c.get("verdict") == "pass" for c in checks)
