"""Optional learned ranker. Missing/incompatible artifacts produce no score."""
from pathlib import Path
import json
from app.ml_features import FEATURES, FEATURE_SCHEMA_VERSION

class ModelA:
    def __init__(self, model_dir: str | Path | None = None):
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).resolve().parents[3] / "ml" / "models"
        self.model_version = None
        self._model = None
        self._load()

    def _load(self):
        model_path = self.model_dir / "model_a.txt"
        meta_path = self.model_dir / "model_a.metadata.json"
        if not model_path.exists() or not meta_path.exists():
            return
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            target_info = metadata.get("targets", {}).get("label_score", {})
            if metadata.get("feature_schema_version") != FEATURE_SCHEMA_VERSION or tuple(target_info.get("features", [])) != FEATURES:
                return
            if target_info.get("artifact") != model_path.name:
                return
            import lightgbm as lgb
            self._model = lgb.Booster(model_file=str(model_path))
            self.model_version = metadata.get("model_version")
        except Exception:
            self._model = None
            self.model_version = None

    def predict(self, features: dict):
        if self._model is None or any(k not in features for k in FEATURES):
            return None
        try:
            return float(self._model.predict([[float(features[k]) for k in FEATURES]])[0])
        except Exception:
            return None
