"""Training-side import of the backend's authoritative feature contract."""
from backend.app.ml_features import FEATURES, RISK_FEATURES, FEATURE_SCHEMA_VERSION, build_features

__all__ = ["FEATURES", "RISK_FEATURES", "FEATURE_SCHEMA_VERSION", "build_features"]
