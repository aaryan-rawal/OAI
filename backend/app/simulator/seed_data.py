"""Stable synthetic seed generator. Every record is explicitly demonstration-only."""
from datetime import datetime, timedelta, timezone
import random

class SeedDataGenerator:
    def __init__(self, count: int = 100, seed: int = 42):
        self.count=count; self.seed=seed
    def generate(self):
        rng=random.Random(self.seed); now=datetime.now(timezone.utc)
        rows=[]
        for index in range(self.count):
            start=now+timedelta(hours=rng.randint(1,72))
            rows.append({"id":f"synthetic-seed-{index+1}","source_type":"synthetic","verification_status":"demonstration",
                         "weight_kg":round(rng.uniform(250,6000),2),"pickup_window_start":start.isoformat(),
                         "pickup_window_end":(start+timedelta(hours=12)).isoformat()})
        return rows
