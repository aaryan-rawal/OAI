"""Deterministic synthetic examples, always labelled as demonstration data."""
import random
from datetime import datetime, timedelta, timezone

class SyntheticSource:
    def __init__(self, num_records: int = 100, seed: int = 42):
        self.num_records=num_records; self.seed=seed
    def generate(self):
        rng=random.Random(self.seed); now=datetime.now(timezone.utc)
        return [{"id":f"synthetic-{i+1}","source_type":"synthetic","verification_status":"demonstration",
                 "commodity_code":f"{rng.randint(1000,9999)}","weight_kg":round(rng.uniform(500,5000),2),
                 "pickup_window_start":(now+timedelta(hours=rng.randint(1,48))).isoformat(),
                 "created_at":now.isoformat()} for i in range(self.num_records)]
