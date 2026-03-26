# API Reference

This document summarizes the public HTTP and WebSocket surface used by the frontend.

## Base URL

All HTTP routes are mounted under `/api`.

## Health

### `GET /api/health`

Response:

```json
{
  "ok": true,
  "app": "elastitune",
  "version": "0.1.0"
}
```

Failure cases:

- This endpoint is intentionally simple and should only fail on server startup or runtime issues.

## Search Mode

### `POST /api/connect`

Request model: `ConnectRequest`

- `mode`: `demo` or `live`
- `esUrl`: required for live mode
- `apiKey`: optional Elasticsearch API key
- `indexName`: required for live mode
- `llm`: optional `LlmConfig`
- `uploadedEvalSet`: optional list of `EvalCase`
- `autoGenerateEval`: whether to generate an eval set when one is not uploaded
- `vectorFieldOverride`: optional field name override
- `maxSampleDocs`: maximum sample docs to include in the connection summary

Response model: `ConnectResponse`

- `connectionId`
- `productMode: "search"`
- `mode`
- `stage`
- `summary`
- `warnings`

Common failures:

- `422` when required live-mode fields are missing or invalid.
- `502` when Elasticsearch cannot be reached or the index analysis fails.
- `404` when a benchmark index is missing and the setup command should be run first.

### `GET /api/connect/benchmarks`

Returns a summary of bundled benchmark readiness.

Response shape:

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

### `GET /api/runs/{runId}`

Response model: `RunSnapshot`

This returns the current live snapshot for a run.

### `GET /api/runs`

Query parameters:

- `limit`
- `indexName`
- `completedOnly`

Response:

```json
{
  "runs": []
}
```

The list is populated from persistence when available.

### `POST /api/runs/{runId}/stop`

Response model: `StopRunResponse`

### `GET /api/runs/{runId}/report`

Response model: `ReportPayload`

Returns the persisted report for completed runs or the in-memory report for active runs that have finished.

### `GET /api/runs/{runId}/preview-query`

Query parameters:

- `queryId`

Response model: `QueryPreviewPayload`

This endpoint is used by the report screen to show per-query results and query bodies.

## Committee Mode

### `POST /api/committee/connect`

Multipart form fields:

- `document`: uploaded file
- `evaluationMode`
- `useSeedPersonas`
- `committeeDescription`
- `industryProfileId`
- `personasJson`
- `llmJson`

Response model: `CommitteeConnectionResponse`

Common failures:

- `422` when the document is empty, parsing fails, or persona JSON is invalid.

### `POST /api/committee/runs`

Request model: `StartCommitteeRunRequest`

Response model: `StartCommitteeRunResponse`

### `GET /api/committee/runs/{runId}`

Response model: `CommitteeSnapshot`

### `POST /api/committee/runs/{runId}/stop`

Response model: `StopCommitteeRunResponse`

### `GET /api/committee/runs/{runId}/report`

Response model: `CommitteeReport`

### `GET /api/committee/runs/{runId}/export`

Response model: `CommitteeExportPayload`

## WebSocket

### `WS /api/ws/runs/{runId}`

The WebSocket endpoint streams live run updates for both search and committee mode.

Typical event envelope:

```json
{
  "type": "metrics.tick",
  "payload": {}
}
```

Common event types:

- `snapshot`
- `run.stage`
- `experiment.completed`
- `rewrite.completed`
- `committee.persona.batch`
- `metrics.tick`
- `committee.report.ready`
- `run.complete`
- `ping`

If the run cannot be found, the socket closes with a policy violation.

## Notes On Schemas

The backend schemas live in:

- [`backend/models/contracts.py`](../backend/models/contracts.py)
- [`backend/committee/models.py`](../backend/committee/models.py)

The frontend mirror types live in:

- [`frontend/src/types/contracts.ts`](../frontend/src/types/contracts.ts)
- [`frontend/src/types/committee.ts`](../frontend/src/types/committee.ts)
