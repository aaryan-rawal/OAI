from typing import List
from app.simulator.seed_data import SeedDataGenerator

class ScenarioGenerator:
    def __init__(self, seed_count: int = 100, seed: int = 42):
        self.seed_generator=SeedDataGenerator(count=seed_count,seed=seed)
    def generate_scenarios(self) -> List[dict]:
        return [{"seed":row,"variant":"default","source_type":"synthetic","verification_status":"demonstration"}
                for row in self.seed_generator.generate()]
