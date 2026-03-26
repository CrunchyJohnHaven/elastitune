from __future__ import annotations

import asyncio

from backend.committee.document_parser import parse_document_bytes
from backend.committee.models import CommitteePersonaView
from backend.committee.personas import build_committee_personas
from backend.committee.reporting import build_export_payload, build_report
from backend.committee.runtime import CommitteeConnectionContext, CommitteeRunContext
from backend.services.persistence_service import PersistenceService
from backend.services.run_manager import RunManager


def test_committee_snapshot_report_and_export_persist(tmp_path) -> None:
    async def scenario() -> None:
        persistence = PersistenceService(db_path=str(tmp_path / "committee-test.db"))
        await persistence.init()

        document = parse_document_bytes(
            "proposal.txt",
            (
                b"Elastic Cloud migration for a large enterprise.\n"
                b"Improve observability, reduce toil, and shorten incident response."
            ),
        )
        persona_build = await build_committee_personas(
            document=document,
            committee_description="",
            provided_personas=None,
            use_seed_personas=False,
            llm_service=None,
        )
        connection = CommitteeConnectionContext(
            connection_id="committee_conn",
            document=document,
            personas=persona_build.personas,
            profile=persona_build.profile,
            evaluation_mode="full_committee",
            warnings=persona_build.warnings,
        )
        persona_views = [
            CommitteePersonaView(
                id=persona.id,
                name=persona.name,
                title=persona.title,
                roleInDecision=persona.roleInDecision,
                authorityWeight=persona.authorityWeight,
                skepticismLevel=persona.skepticismLevel,
                sentiment="neutral",
                currentScore=0.58,
                supportScore=0.54,
                reactionQuote="Promising, but I need more proof.",
                topObjection="Needs tighter proof.",
                riskFlags=[],
                missing=[],
                perSection=[],
                priorities=persona.priorities,
                concerns=persona.concerns,
            )
            for persona in persona_build.personas
        ]
        ctx = CommitteeRunContext(
            run_id="committee_run",
            connection=connection,
            persona_views=persona_views,  # type: ignore[arg-type]
            max_rewrites=2,
            duration_minutes=1,
            auto_stop_on_plateau=True,
        )
        ctx.stage = "completed"
        ctx.started_at = "2026-03-26T12:00:00+00:00"
        ctx.completed_at = "2026-03-26T12:03:00+00:00"
        ctx.metrics.baselineScore = 0.42
        ctx.metrics.currentScore = 0.57
        ctx.metrics.bestScore = 0.57
        ctx.metrics.improvementPct = 35.7
        ctx.metrics.rewritesTested = 2
        ctx.metrics.acceptedRewrites = 1
        ctx.report = build_report(ctx)
        export_payload = build_export_payload(ctx)

        manager = RunManager(persistence=persistence)
        await manager.create_committee_connection(connection.connection_id, connection)
        await manager.create_committee_run(ctx.run_id, ctx)
        await manager._persist_committee_run(ctx.run_id)
        await persistence.save_committee_report(ctx.report)
        await persistence.save_committee_export(export_payload)

        restored_snapshot = await persistence.load_committee_snapshot(ctx.run_id)
        restored_report = await persistence.load_committee_report(ctx.run_id)
        restored_export = await persistence.load_committee_export(ctx.run_id)
        listed_runs = await persistence.list_committee_runs(limit=10, completed_only=True)

        assert restored_snapshot is not None
        assert restored_snapshot.stage == "completed"
        assert restored_snapshot.metrics.bestScore == 0.57
        assert restored_snapshot.document.rawText == ""
        assert restored_report is not None
        assert restored_report.runId == ctx.run_id
        assert restored_export is not None
        assert restored_export.runId == ctx.run_id
        assert restored_export.documentName == document.documentName
        assert listed_runs[0]["run_id"] == ctx.run_id
        assert listed_runs[0]["document_name"] == document.documentName

    asyncio.run(scenario())
