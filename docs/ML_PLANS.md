# OptiFreight AI — Machine Learning Plan

## Purpose

Machine learning may rank cargo candidates and estimate uncertainty only after deterministic hard eligibility checks have passed. A model must never turn a failed or unknown candidate into an eligible one.

## Model A — Candidate ranking

- Intended task: learn-to-rank eligible backhaul candidates for an operator/truck/route context.
- Candidate features may include verified route position, payload utilization, cargo category, source reliability, pickup window slack, road excursion, incremental distance, and verified net contribution inputs.
- Candidate labels must be defined from observed outcomes (accepted, completed, cancelled, actual realized contribution) or clearly marked synthetic simulation labels.
- Ranking model candidate: LightGBM LambdaRank, subject to sufficient grouped training data.
- Output: nullable model score plus model version and feature provenance.

## Model B — Delay and cost risk

- Intended task: estimate delivery-delay and incremental-cost uncertainty for otherwise eligible candidates.
- Candidate output: quantiles or calibrated intervals, not a single falsely precise value.
- SynDelay and DataCo may support exploratory/synthetic baseline work, but dataset domain shift and provenance must be documented. Neither dataset is automatically a validated Indian road-freight training set.

## Model C — Optional neural model

- Optional research track. Do not build or claim a neural model until a target, sufficient training data, baseline comparison and evaluation protocol are approved.

## Baseline and evaluation

- Keep a deterministic, transparent baseline for comparison.
- Split by time and/or route/entity to avoid leakage.
- Report ranking metrics (e.g. NDCG@k / MAP@k), delay MAE or quantile loss, calibration, and subgroup performance where sample sizes support it.
- Keep synthetic-trained models visibly labelled as synthetic/demo.
- Persist dataset version, split, feature schema, training code revision, metrics and model artifact hash.

## Current status

No trained model artifacts were present in the inspected project package. Model A/B/C wrappers now return `None` until a trained, versioned artifact is supplied; they do not generate random or fabricated scores. SHAP explanations require an actual trained model. No ML model score is currently returned by the matching API.
