# Kibana Integration

ElastiTune can now persist run artifacts to SQLite and optionally index completed run summaries back into Elasticsearch for Kibana consumption.

## What gets indexed

- Search runs: `elastitune-search-runs-*`
- Search experiments: `elastitune-search-experiments-*`
- Committee runs: `elastitune-committee-runs-*`

Each document includes:

- `@timestamp`
- `event.kind`
- `event.category`
- `event.action`
- `elastitune.product_mode`
- `elastitune.run_id`

Search runs also include connection metadata, headline metrics, and before/after profiles. Search experiment documents include per-experiment deltas and the changed parameter payload. Committee runs include industry profile metadata and persona rollups.

## Configuration

Set these environment variables to enable automatic indexing on run completion:

- `ENABLE_ELASTIC_SINK=true`
- `ELASTIC_SINK_URL=https://your-es-endpoint:9200`
- `ELASTIC_SINK_API_KEY=...`
- `ELASTIC_SINK_SEARCH_RUNS_PREFIX=elastitune-search-runs`
- `ELASTIC_SINK_SEARCH_EXPERIMENTS_PREFIX=elastitune-search-experiments`
- `ELASTIC_SINK_COMMITTEE_RUNS_PREFIX=elastitune-committee-runs`

## Backfill from SQLite

Use the script below to push an already-persisted run into Elasticsearch:

```bash
python3 backend/scripts/push_run_to_es.py --mode search --run-id <run-id>
python3 backend/scripts/push_run_to_es.py --mode committee --run-id <run-id>
```

## Saved Objects

Import the files in [`kibana/`](/tmp/elastitune-codex/kibana) through Kibana Saved Objects. Do not write directly to `.kibana`.

## Security notes

- Use Kibana or Elasticsearch API keys instead of embedding user credentials.
- Search reports are sanitized before persistence; API keys are not stored in SQLite.
- Committee exports omit raw uploaded document text from persisted snapshots, while preserving before/after section diffs for reporting.
