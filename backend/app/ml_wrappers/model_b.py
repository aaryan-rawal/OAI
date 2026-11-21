"""Optional delay/cost quantile models; outputs intervals, never eligibility."""
from pathlib import Path
import json
from app.ml_features import RISK_FEATURES, FEATURE_SCHEMA_VERSION

class ModelB:
    quantiles = ("p10", "p50", "p90")

    def __init__(self, model_dir: str | Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).resolve().parents[3] / "ml" / "models"
        self.model_version = None
        self._models = {}
        self._load()

    def _load(self):
        metadata_path = self.model_dir / "model_b.metadata.json"
        if not metadata_path.exists():
            return
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
                return
            import lightgbm as lgb
            loaded = {}
            for target in ("delay_minutes", "incremental_cost_inr"):
                target_info = metadata.get("targets", {}).get(target, {})
                if tuple(target_info.get("features", [])) != RISK_FEATURES:
                    return
                for q in self.quantiles:
                    artifact = target_info.get("quantiles", {}).get(q, {}).get("artifact")
                    if not artifact or not (self.model_dir / artifact).exists():
                        return
                    loaded[(target, q)] = lgb.Booster(model_file=str(self.model_dir / artifact))
            self._models = loaded
            self.model_version = metadata.get("model_version")
        except Exception:
            self._models = {}
            self.model_version = None

    def predict(self, features: dict):
        if not self._models or any(key not in features for key in RISK_FEATURES):
            return None
        row = [[float(features[key]) for key in RISK_FEATURES]]
        try:
            result = {}
            for target in ("delay_minutes", "incremental_cost_inr"):
                result[target] = {q: float(self._models[(target, q)].predict(row)[0]) for q in self.quantiles}
            return result
        except Exception:
            return None
