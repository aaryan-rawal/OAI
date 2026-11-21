"""Reproducible LightGBM training entry point; intentionally not run during build.

Model A: regression ranker trained against an owner-approved `label_score`.
Model B: quantile regressors for `delay_minutes` and `incremental_cost_inr`.
Inputs must be curated, labelled, point-in-time-safe CSVs, never raw logs directly.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from ml.features import FEATURES, RISK_FEATURES, FEATURE_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[2]
QUANTILES = (0.1, 0.5, 0.9)


def split_indices(frame: pd.DataFrame, seed: int = 42, validation_fraction: float = 0.2):
    """Deterministic holdout; prefer an explicit time/entity split during final experiments."""
    rng = np.random.default_rng(seed)
    indices = np.arange(len(frame))
    rng.shuffle(indices)
    cut = max(1, int(len(indices) * (1 - validation_fraction)))
    return indices[:cut], indices[cut:]


def pinball_loss(actual, predicted, quantile: float) -> float:
    error = np.asarray(actual) - np.asarray(predicted)
    return float(np.mean(np.maximum(quantile * error, (quantile - 1) * error)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["a", "b"], required=True)
    parser.add_argument("--input", required=True, help="Curated labelled CSV; never point this at raw logs directly.")
    parser.add_argument("--output-dir", default=str(ROOT / "ml" / "models"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    import lightgbm as lgb

    if args.model == "a":
        targets = [("label_score", "regression", FEATURES)]
    else:
        targets = [("delay_minutes", "quantile", RISK_FEATURES),
                   ("incremental_cost_inr", "quantile", RISK_FEATURES)]
    all_metadata = {"model": f"model_{args.model}", "model_version": f"model_{args.model}-1.0.0",
                    "feature_schema_version": FEATURE_SCHEMA_VERSION, "trained_at_utc": pd.Timestamp.utcnow().isoformat(),
                    "seed": args.seed, "targets": {}}
    for target, mode, feature_names in targets:
        required = [*feature_names, target]
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise SystemExit(f"Missing required labelled columns for {target}: {', '.join(missing)}")
        clean = frame[required].replace([np.inf, -np.inf], np.nan).dropna()
        if len(clean) < 100:
            raise SystemExit(f"At least 100 complete labelled rows are required for {target}.")
        X, y = clean[list(feature_names)].astype(float), clean[target].astype(float)
        train_idx, valid_idx = split_indices(clean, args.seed)
        if not len(valid_idx):
            raise SystemExit("Validation split is empty.")
        train = lgb.Dataset(X.iloc[train_idx], label=y.iloc[train_idx])
        valid = lgb.Dataset(X.iloc[valid_idx], label=y.iloc[valid_idx], reference=train)
        if mode == "regression":
            params = {"objective": "regression", "metric": "rmse", "verbosity": -1,
                      "seed": args.seed, "feature_fraction_seed": args.seed,
                      "bagging_seed": args.seed, "deterministic": True, "force_col_wise": True}
            booster = lgb.train(params, train, num_boost_round=500, valid_sets=[valid],
                                callbacks=[lgb.early_stopping(40, verbose=False), lgb.log_evaluation(0)])
            pred = booster.predict(X.iloc[valid_idx], num_iteration=booster.best_iteration)
            error = pred - y.iloc[valid_idx].to_numpy()
            metrics = {"mae": float(np.mean(np.abs(error))), "rmse": float(np.sqrt(np.mean(error ** 2)))}
            filename = "model_a.txt"
            booster.save_model(str(out / filename))
            all_metadata["targets"][target] = {"artifact": filename, "features": list(feature_names),
                                                "metrics": metrics, "train_rows": int(len(train_idx)),
                                                "validation_rows": int(len(valid_idx)), "best_iteration": int(booster.best_iteration)}
        else:
            target_metrics = {}
            for q in QUANTILES:
                params = {"objective": "quantile", "alpha": q, "metric": "quantile", "verbosity": -1,
                          "seed": args.seed, "feature_fraction_seed": args.seed,
                          "bagging_seed": args.seed, "deterministic": True, "force_col_wise": True}
                booster = lgb.train(params, train, num_boost_round=500, valid_sets=[valid],
                                    callbacks=[lgb.early_stopping(40, verbose=False), lgb.log_evaluation(0)])
                pred = booster.predict(X.iloc[valid_idx], num_iteration=booster.best_iteration)
                suffix = f"p{int(q * 100):02d}"
                filename = f"model_b_{target}_{suffix}.txt"
                booster.save_model(str(out / filename))
                target_metrics[suffix] = {"artifact": filename, "pinball_loss": pinball_loss(y.iloc[valid_idx], pred, q),
                                          "best_iteration": int(booster.best_iteration)}
            all_metadata["targets"][target] = {"features": list(feature_names), "train_rows": int(len(train_idx)),
                                                "validation_rows": int(len(valid_idx)), "quantiles": target_metrics}
    (out / f"model_{args.model}.metadata.json").write_text(json.dumps(all_metadata, indent=2), encoding="utf-8")
    print(json.dumps(all_metadata, indent=2))


if __name__ == "__main__":
    main()
