"""SHAP explanations are available only for a loaded, trained model."""
class ShapExplainer:
    def __init__(self, model):
        if model is None or not callable(getattr(model, "predict", None)):
            raise ValueError("A trained model with a predict method is required.")
        try:
            import shap
        except ImportError as exc:
            raise RuntimeError("Install the project's ML requirements to enable SHAP.") from exc
        self._explainer = shap.Explainer(model.predict)
    def explain(self, features):
        values=self._explainer(features)
        import numpy as np
        mean_abs=np.abs(values.values).mean(axis=0)
        return {f"feature_{i}":float(v) for i,v in enumerate(mean_abs)}
