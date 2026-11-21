# OptiFreight AI — ML Development Package

## Status

The ML serving/training scaffolding is implemented. No model has been trained or tested in this build, and no model artifact is shipped. This is deliberate: the project owner wants the remaining rule, routing and integration work completed before the dedicated training/evaluation phase.

## Models

- **Model A — candidate ranking:** LightGBM regression ranker scaffold, trained only from an owner-approved `label_score` derived from observed outcomes or explicitly labelled simulation outcomes. Ranking labels and grouped query structure still need to be finalized. Baseline remains available.
- **Model B — delay and incremental-cost uncertainty:** LightGBM quantile-regression scaffold for p10/p50/p90 estimates of `delay_minutes` and `incremental_cost_inr`. It does not emit a single falsely precise point estimate.
- **Model C — optional neural model:** not implemented/trained; requires explicit approval, sufficient labelled data, and baseline evidence.

## Feature contract

The serving contract lives in `backend/app/ml_features.py`; `ml/features.py` re-exports it for training. Version: `1.0`.

Missing values are not zero-filled. A model returns no prediction when required features are unavailable. Model A requires all ranking features; Model B excludes the net-contribution feature to reduce target leakage risk.

## Training data requirements

- Curated point-in-time feature rows, with provenance and label definitions.
- Model A: `label_score` must represent an approved observed or explicitly simulated ranking outcome.
- Model B: `delay_minutes` and `incremental_cost_inr` must be measured/derived labels with documented definitions.
- Use time-, route-, or entity-aware holdouts to avoid leakage. The current script's deterministic random validation split is a development scaffold only; final evaluation must use the approved holdout design.
- Synthetic datasets and synthetic labels must be labelled as synthetic. They are not proof of Indian road-freight performance.

## Dataset suitability notes

- **SynDelay:** supplied dataset has 155,488 rows and a three-class `label` with values 0, 1 and 2. Its README identifies it as a synthetic delivery-delay prediction dataset. The project must inspect the source paper/label semantics before mapping those classes to Model B; do not coerce it into binary delay risk.
- **DataCo:** useful for exploratory supply-chain/shipping-delay and operational features, but domain and target alignment must be checked.
- **Olist:** e-commerce order/shipping context; not direct backhaul cargo or Indian road-freight ground truth.
- **Belgium OBU:** user has downloaded the Kaggle dataset but it is not present in this workspace yet. Inspect schema, license, temporal coverage, vehicle identifiers and privacy before deciding on features. GPS traces alone do not provide a cargo-match success label.
- **SimMD / AnonNet / disruption monitoring:** research references or route/network/disruption context; not automatically supervised matching labels.

## Commands (do not run until training data is approved)

From project root:

```powershell
python -m ml.training.train_models --model a --input data/processed/model_a_labeled.csv
python -m ml.training.train_models --model b --input data/processed/model_b_labeled.csv
```

Artifacts and metadata are written to `ml/models/`. Keep large artifacts out of Git unless the owner explicitly chooses Git LFS or a model registry. Every model must record feature schema version, dataset version, seed, split, target definition, metrics, training timestamp and artifact hash.
