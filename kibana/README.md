# ElastiTune Kibana Pack

This folder contains starter Saved Objects for visualizing ElastiTune data inside Kibana.

## Contents

- `elastitune-data-view.ndjson`
- `elastitune-dashboards.ndjson`

## Import

1. Open Kibana.
2. Go to `Stack Management -> Saved Objects`.
3. Import both NDJSON files.
4. If your index prefixes differ from the defaults, edit the imported data view to match your environment.

## Data sources expected

- `elastitune-search-runs-*`
- `elastitune-search-experiments-*`
- `elastitune-committee-runs-*`

## Version note

The saved objects are lightweight starter assets intended for Kibana 8.15.x. If Kibana reports an import-version mismatch, re-export them from your target stack after first import.
