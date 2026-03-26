from __future__ import annotations

from backend.models.runtime import ConnectionContext
from backend.services.demo_service import DemoService


class TestDemoServiceCreateConnection:
    """Tests for DemoService.create_connection()."""

    def test_returns_connection_context(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_test")
        assert isinstance(conn, ConnectionContext)

    def test_connection_has_summary(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_test")
        assert conn.summary is not None

    def test_summary_has_cluster_name(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_test")
        assert isinstance(conn.summary.clusterName, str)
        assert conn.summary.clusterName != ""

    def test_summary_has_index_name(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_test")
        assert isinstance(conn.summary.indexName, str)
        assert conn.summary.indexName != ""

    def test_summary_has_doc_count(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_test")
        assert isinstance(conn.summary.docCount, int)
        assert conn.summary.docCount > 0

    def test_summary_has_baseline_eval_count(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_test")
        # baselineEvalCount must be a non-negative integer
        assert isinstance(conn.summary.baselineEvalCount, int)
        assert conn.summary.baselineEvalCount >= 0

    def test_connection_id_is_stored(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("my_conn_id")
        assert conn.connection_id == "my_conn_id"

    def test_mode_is_demo(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_demo")
        assert conn.mode == "demo"

    def test_eval_set_is_non_empty(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_eval")
        assert len(conn.eval_set) > 0

    def test_baseline_profile_is_present(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_profile")
        assert conn.baseline_profile is not None
        assert len(conn.baseline_profile.lexicalFields) > 0


class TestDemoServiceExperiments:
    """Tests for demo experiments data."""

    def test_experiments_count_is_at_least_8(self) -> None:
        """The fallback data has 8 experiments; the real JSON file may have more."""
        svc = DemoService()
        experiments = svc.experiments
        assert len(experiments) >= 8

    def test_each_experiment_has_required_fields(self) -> None:
        svc = DemoService()
        required_keys = {
            "experimentId",
            "timestamp",
            "hypothesis",
            "change",
            "baselineScore",
            "candidateScore",
            "deltaAbsolute",
            "deltaPercent",
            "decision",
            "durationMs",
        }
        for exp in svc.experiments:
            for key in required_keys:
                assert key in exp, f"Missing key {key!r} in experiment {exp.get('experimentId')}"

    def test_experiments_have_valid_decisions(self) -> None:
        svc = DemoService()
        valid_decisions = {"kept", "reverted"}
        for exp in svc.experiments:
            assert exp["decision"] in valid_decisions

    def test_experiments_are_returned_as_copy(self) -> None:
        svc = DemoService()
        first = svc.experiments
        expected_count = len(first)
        second = svc.experiments
        # Mutating the returned list should not affect the next call
        first.clear()
        assert len(second) == expected_count


class TestDemoServicePersonas:
    """Tests for demo personas data."""

    def test_personas_fallback_count_is_24(self) -> None:
        svc = DemoService()
        # The fallback list has exactly 24 entries; unless a JSON file is loaded
        # with more, build_personas(24) should return 24 personas.
        personas = svc.build_personas(24)
        assert len(personas) == 24

    def test_personas_are_persona_view_models(self) -> None:
        from backend.models.contracts import PersonaViewModel

        svc = DemoService()
        personas = svc.build_personas(5)
        for p in personas:
            assert isinstance(p, PersonaViewModel)

    def test_each_persona_has_queries(self) -> None:
        svc = DemoService()
        personas = svc.build_personas(10)
        for p in personas:
            assert len(p.queries) > 0

    def test_requesting_fewer_personas_returns_correct_count(self) -> None:
        svc = DemoService()
        personas = svc.build_personas(5)
        assert len(personas) == 5


class TestDemoConnectionSummaryFields:
    """Tests that connection summary contains the expected top-level fields."""

    def test_cluster_name_field_present(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_fields")
        assert hasattr(conn.summary, "clusterName")

    def test_index_name_field_present(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_fields")
        assert hasattr(conn.summary, "indexName")

    def test_doc_count_field_present(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_fields")
        assert hasattr(conn.summary, "docCount")

    def test_baseline_eval_count_field_present(self) -> None:
        svc = DemoService()
        conn = svc.create_connection("conn_fields")
        assert hasattr(conn.summary, "baselineEvalCount")
