#!/usr/bin/env sh
set -eu
# Place a legally sourced India/region .osm.pbf at routing/data/india.osm.pbf first.
# Run from the OAI project root. This preprocesses a truck-profile graph; it does not
# certify OSM restriction completeness or a specific vehicle's legal access.
PBF="${1:-routing/data/india.osm.pbf}"
[ -f "$PBF" ] || { echo "Missing PBF: $PBF" >&2; exit 2; }
docker compose -f routing/docker-compose.osrm.yml build osrm
docker compose -f routing/docker-compose.osrm.yml run --rm osrm osrm-extract -p /opt/hgv.lua "/data/$(basename "$PBF")" -o /data/india-hgv
docker compose -f routing/docker-compose.osrm.yml run --rm osrm osrm-partition /data/india-hgv
docker compose -f routing/docker-compose.osrm.yml run --rm osrm osrm-customize /data/india-hgv
echo "HGV graph built at routing/data/india-hgv.osrm*"
