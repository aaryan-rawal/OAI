# OptiFreight AI — Dataset Registry

This directory separates raw source files, extracted data collections, processed modelling copies, research repositories and provenance manifests. Dataset files are research inputs; they are not automatically treated as live cargo listings.

## Layout

- `raw/` — original uploaded CSV files.
- `extracted/` — extracted data-only collections such as Olist and AnonNet.
- `repositories/` — selected research repositories (SimMD and SynDelay); the large supply-chain disruption-monitoring repository is preserved in the companion source-archive package and can be extracted on demand.
- `processed/` — privacy-filtered, documented modelling copies.
- `source_archives/` — placeholder/documentation. Original uploaded ZIP archives are preserved unchanged in the companion `OAI_dataset_source_archives.zip` package to avoid duplicate compressed copies inside the main project archive.
- `incoming/belgium_obu/` — reserved for the Belgium OBU dataset; it has not yet been uploaded into this workspace.
- `manifests/` — machine-readable inventory and provenance.

## Relevance to OptiFreight AI

| Source | Intended research use | Important limitation |
|---|---|---|
| DataCo Supply Chain | Delivery-delay, shipment, order and supply-chain feature exploration | Not a verified Indian backhaul cargo marketplace; location fields and personal data require careful filtering |
| Olist | Order, seller/customer, product and delivery analytics | Brazil e-commerce data; not direct freight listings for Indian corridors |
| SynDelay | Synthetic delivery-delay modelling and baseline comparison | Synthetic benchmark with three label classes; inspect source semantics before mapping to project targets |
| SimMD / CVRP | Vehicle-routing and capacity-constrained planning research | Simulated instances, not actual freight offers or road-network geometry |
| Supply-chain disruption monitoring | Disruption intelligence and supply-network context | Research repository, not a cargo listing source; full source archive is in the companion package |
| AnonNet | Supply-network graph analysis | Anonymised graph; no truck GPS or cargo listing semantics |
| Tokenized access logs | Product/category temporal behaviour exploration | Web access logs are not vehicle movement or freight data; exclude IP/URL identifiers from modelling |
| Belgium OBU | Potential vehicle movement / road-usage research | Not yet available in this workspace; inspect schema, licence and coordinate/time coverage before use |

## Integrity and privacy

Do not interpret missing values as zero. Do not use customer names, email addresses, passwords, street addresses, IP addresses, or other direct identifiers as model features. Preserve source attribution and licence information. Synthetic records must remain labelled as demonstration data.

See `manifests/dataset_manifest.json` and `manifests/file_integrity_manifest.json`. The Belgium OBU entry is explicitly pending.
