# India HGV routing (OSRM)

## Included code
- `profiles/hgv.lua`: baseline HGV profile using OSRM profile API v4 and the standard OSRM way handlers. It prioritizes `hgv`/`goods` access tags, applies baseline vehicle dimensions/weight, and uses conservative heavy-vehicle speeds.
- `Dockerfile.osrm`: pins the OSRM runtime to `v5.27.1` and installs the custom profile.
- `build_osrm_data.sh`: extracts, partitions and customizes a graph from a locally supplied PBF.
- `docker-compose.osrm.yml`: serves the preprocessed HGV graph on port 5000.

## Build
1. Obtain an OSM PBF that you are permitted to use and place it at `routing/data/india.osm.pbf` (or pass a different local PBF path to the script).
2. Install Docker Desktop with Linux containers and Docker Compose.
3. From the project root run `sh routing/build_osrm_data.sh` (or run the equivalent commands in WSL/Git Bash).
4. Start the server with `docker compose -f routing/docker-compose.osrm.yml up -d`.
5. Test representative corridors and restrictions against field-verified routes before enabling `OSRM_TRUCK_PROFILE_CONFIRMED=true`.

## Important limitations
OSRM applies a profile when the graph is preprocessed, not per request. This graph uses one baseline profile (3.8 m high, 2.6 m wide, 16.5 m long, 49,000 kg). It is not dynamically customized for each registered vehicle. Create and validate separate graph profiles for materially different vehicle classes or use a routing engine that supports per-request vehicle dimensions/weight. The profile can only enforce restrictions represented in the OSM extract and understood by its handlers. Conditional access tags, local police orders, time-of-day city entry windows, temporary closures, bridge/road permits and missing OSM data are not guaranteed to be complete. Unknown restrictions must remain unknown in the application; do not treat an OSRM route as a legal clearance.

The profile is a code-side baseline, not a verified HGV route engine deployment. No PBF data, graph files or representative route validation are included in this ZIP. Do not set `OSRM_TRUCK_PROFILE_CONFIRMED=true` until your own server has been built and audited.
