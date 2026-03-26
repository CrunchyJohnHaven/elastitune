from __future__ import annotations

from pathlib import Path
import time
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app


def main() -> int:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200, f"health failed: {health.text}"
        print("ok health")

        search_connect = client.post("/api/connect", json={"mode": "demo"})
        assert search_connect.status_code == 200, f"search connect failed: {search_connect.text}"
        search_connection_id = search_connect.json()["connectionId"]
        print("ok search connect")

        search_run = client.post(
            "/api/runs",
            json={
                "connectionId": search_connection_id,
                "durationMinutes": 1,
                "maxExperiments": 2,
                "personaCount": 4,
                "autoStopOnPlateau": True,
            },
        )
        assert search_run.status_code == 200, f"search run failed: {search_run.text}"
        search_run_id = search_run.json()["runId"]
        search_snapshot = client.get(f"/api/runs/{search_run_id}")
        assert search_snapshot.status_code == 200, f"search snapshot failed: {search_snapshot.text}"
        print("ok search run")

        committee_connect = client.post(
            "/api/committee/connect",
            files={
                "document": (
                    "demo.txt",
                    (
                        b"Accelerating legal operations at SBA. "
                        b"Search.gov provides federal-scale proof. "
                        b"FedRAMP and Carahsoft are available. "
                        b"Schedule a 60-minute discovery session this month."
                    ),
                    "text/plain",
                )
            },
            data={
                "evaluationMode": "full_committee",
                "useSeedPersonas": "true",
                "committeeDescription": "CIO\nGeneral Counsel\nBudget Director\nDistrict Attorney\nOIG Auditor",
            },
        )
        assert committee_connect.status_code == 200, f"committee connect failed: {committee_connect.text}"
        committee_connection_id = committee_connect.json()["connectionId"]
        print("ok committee connect")

        committee_run = client.post(
            "/api/committee/runs",
            json={
                "connectionId": committee_connection_id,
                "durationMinutes": 1,
                "maxRewrites": 4,
                "autoStopOnPlateau": True,
            },
        )
        assert committee_run.status_code == 200, f"committee run failed: {committee_run.text}"
        committee_run_id = committee_run.json()["runId"]

        snapshot_payload = None
        deadline = time.time() + 12.0
        while time.time() < deadline:
            committee_snapshot = client.get(f"/api/committee/runs/{committee_run_id}")
            assert committee_snapshot.status_code == 200, f"committee snapshot failed: {committee_snapshot.text}"
            snapshot_payload = committee_snapshot.json()
            if snapshot_payload.get("stage") == "completed":
                break
            time.sleep(0.5)

        assert snapshot_payload is not None, "committee snapshot never returned"
        assert snapshot_payload.get("stage") == "completed", "committee run did not complete within smoke timeout"
        assert "metrics" in snapshot_payload, "committee snapshot missing metrics"
        assert snapshot_payload["metrics"]["elapsedSeconds"] >= 1, "committee elapsed time never advanced"
        print("ok committee run")

        committee_report = client.get(f"/api/committee/runs/{committee_run_id}/report")
        assert committee_report.status_code == 200, f"committee report failed: {committee_report.text}"
        print("ok committee report")

        committee_export = client.get(f"/api/committee/runs/{committee_run_id}/export")
        assert committee_export.status_code == 200, f"committee export failed: {committee_export.text}"
        print("ok committee export")

    print("all smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
