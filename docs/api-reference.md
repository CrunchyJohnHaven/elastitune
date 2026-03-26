# API Reference

The backend is served under `/api`. WebSocket traffic uses `/ws` without the `/api` prefix.

## Health

### `GET /api/health`

Response:

```json
{ "ok": true, "app": "elastitune", "version": "0.1.0" }
```

## Search mode

### `POST /api/connect`

Request model: `ConnectRequest`

Key fields:

- `mode`: `demo` or `live`
- `esUrl`, `apiKey`, `indexName`
- `llm`
- `uploadedEvalSet`
- `autoGenerateEval`
- `vectorFieldOverride`
- `maxSampleDocs`

Response model: `ConnectResponse`

```json
{
  "connectionId": "uuid",
  "productMode": "search",
  "mode": "live",
  "stage": "ready",
  "summary": { "...": "ConnectionSummary" },
  "warnings": []
}
```

Failure examples:

- `422` when `esUrl` or `indexName` is missing for live mode.
- `404` when the requested index is missing.
- `502` when Elasticsearch cannot be reached or the index analysis fails.

### `GET /api/connect/benchmarks`

Returns:

```json
{
  "reachable": true,
  "presets": [
    {
      "id": "products",
      "label": "Product Store",
      "indexName": "products-catalog",
      "expectedDocCount": 931,
      "docCount": 931,
      "ready": true,
      "setupCommand": "python benchmarks/setup.py --only products-catalog",
      "reachable": true
    }
  ]
}
```

### `POST /api/runs`

Request model: `StartRunRequest`

- `connectionId`
- `durationMinutes`
- `maxExperiments`
- `personaCount`
- `autoStopOnPlateau`
- `previousRunId`

Response model: `StartRunResponse`

```json
{ "runId": "uuid", "productMode": "search", "stage": "starting" }
```

### `GET /api/runs/{run_id}`

Response model: `RunSnapshot`

It includes:

- `summary`
- `searchProfile`
- `recommendedProfile`
- `metrics`
- `personas`
- `experiments`
- `compression`
- `runConfig`
- `startedAt`
- `completedAt`

### `GET /api/runs`

Returns a wrapper object:

```json
{ "runs": [ { "run_id": "uuid", "stage": "completed" } ] }
```

The rows come from the persisted search run table and include:

- `run_id`
- `mode`
- `stage`
- `index_name`
- `cluster_name`
- `baseline_score`
- `best_score`
- `improvement_pct`
- `experiments_run`
- `started_at`
- `completed_at`
- `updated_at`

### `POST /api/runs/{run_id}/stop`

Response model: `StopRunResponse`

### `GET /api/runs/{run_id}/report`

Response model: `ReportPayload`

If the run is still active, the endpoint returns `409`.

### `GET /api/runs/{run_id}/preview-query?queryId=...`

Returns the baseline and optimized query DSL plus hit previews for a single eval query.

### `POST /api/model-compare`

Request model: `ModelCompareRequest`

Response model: `ModelComparisonResult`

## Committee mode

### `POST /api/committee/connect`

Multipart form fields:

- `document`
- `evaluationMode`
- `useSeedPersonas`
- `committeeDescription`
- `industryProfileId`
- `personasJson`
- `llmJson`

Response model: `CommitteeConnectionResponse`

### `POST /api/committee/runs`

Request model: `StartCommitteeRunRequest`

Response model: `StartCommitteeRunResponse`

### `GET /api/committee/runs/{run_id}`

Response model: `CommitteeSnapshot`

### `POST /api/committee/runs/{run_id}/stop`

Response model: `StopCommitteeRunResponse`

### `GET /api/committee/runs/{run_id}/report`

Response model: `CommitteeReport`

### `GET /api/committee/runs/{run_id}/export`

Response model: `CommitteeExportPayload`

## WebSocket

### `GET /ws/runs/{run_id}`

The socket sends:

- an initial `snapshot` event when one exists,
- live delta events such as `run.stage`, `experiment.completed`, `persona.batch`, and `report.ready`,
- and a final `run.complete` event when the run ends.

Failure example:

- `1008` close code when the run does not exist.

## Error shape

Most errors use FastAPI’s default `{"detail": "message"}` shape. The frontend normalizes common status codes into user-friendly copy.
