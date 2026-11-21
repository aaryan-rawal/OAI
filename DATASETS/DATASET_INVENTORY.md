# Dataset Inventory

This inventory reflects files actually present in the main project copy as of 2026-11-21. Original ZIP archives are retained in the companion `OAI_dataset_source_archives.zip` package, not duplicated here.

| Dataset | Present files | Potential use | Current decision / limitation |
|---|---|---|---|
| DataCo Supply Chain | `raw/DataCoSupplyChainDataset.csv`, `raw/DescriptionDataCoSupplyChain.csv`, sanitized `processed/DataCoSupplyChainDataset_modeling.csv` | Delivery status, shipment timing and delay-risk exploration | Domain is not validated Indian backhaul. Use sanitized modelling copy; direct customer identifiers/passwords excluded. |
| Olist Brazilian e-commerce | 9 CSV files in `extracted/olist/` | Order lifecycle, seller/customer logistics and delivery analytics | Brazil e-commerce data, not direct Indian cargo listings. Review personal/location columns before modelling. |
| SynDelay | Dataset and baseline scripts under `repositories/syndelay/` | Synthetic delivery-delay baseline | Synthetic benchmark with labels 0, 1 and 2; inspect paper/label semantics before mapping to Model B. |
| SimMD multi-depot CVRP | VRP/YAML/PNG instances under `repositories/sim_multi_depot_cvrp/` | Vehicle routing and capacity planning experiments | Simulated instances, not live road routes or freight offers. |
| Supply-chain disruption monitoring | `repositories/supply_chain_disruption_monitoring/README_SOURCE_ARCHIVE.md`; full archive in companion package | Disruption monitoring and supply-network research | Not a cargo-listing source; full repository not expanded to avoid duplicating a large research-results tree. |
| AnonNet | Anonymized nodes/edges under `extracted/anon_network/` | Graph/network analysis | Not truck GPS or cargo listing data. |
| Tokenized access logs | Raw CSV and sanitized modelling copy | Product/category temporal patterns | Not vehicle movement. Exclude IP and URL fields from modelling copy. |
| Belgium OBU | Pending under `incoming/belgium_obu/` | Potential vehicle movement/road-use research | User reports a local download; not uploaded to this workspace, so contents and license remain unverified. |

## Integrity

`manifests/dataset_manifest.json` records source metadata and CSV schemas/row counts. `manifests/file_integrity_manifest.json` records SHA-256 hashes for raw, processed, extracted and retained repository files. Original source archives are in the companion package.

## Data handling

- Raw uploads are preserved for local provenance. Do not publish raw datasets without checking licenses and personal-data fields.
- Use sanitized DataCo and access-log copies for exploratory modelling.
- Never use customer passwords, email addresses, names, direct identifiers, IP addresses or raw URLs as model features.
- Do not map non-Indian e-commerce locations into Indian freight corridors.
- Synthetic sources remain explicitly labelled as demonstration data.
