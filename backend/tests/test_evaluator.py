from __future__ import annotations

import math

from backend.engine.evaluator import compute_ndcg, compute_dcg, compute_ideal_dcg


class TestComputeNdcg:
    """Tests for the compute_ndcg() function."""

    def test_perfect_score_when_all_relevant_at_top(self) -> None:
        """All relevant docs ranked first should yield nDCG = 1.0."""
        relevant = ["doc1", "doc2", "doc3"]
        ranked = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        score = compute_ndcg(ranked, relevant, k=10)
        assert abs(score - 1.0) < 1e-9

    def test_zero_when_no_relevant_docs_found(self) -> None:
        """No relevant doc in ranked list should yield nDCG = 0.0."""
        relevant = ["doc_relevant"]
        ranked = ["doc_a", "doc_b", "doc_c"]
        score = compute_ndcg(ranked, relevant, k=10)
        assert score == 0.0

    def test_zero_for_empty_eval_set(self) -> None:
        """Empty relevant set should return 0.0 (IDCG is 0, guard triggers)."""
        score = compute_ndcg(["doc1", "doc2"], [], k=10)
        assert score == 0.0

    def test_zero_for_empty_ranked_list(self) -> None:
        """No ranked docs means no DCG, so nDCG = 0.0."""
        score = compute_ndcg([], ["doc1"], k=10)
        assert score == 0.0

    def test_penalizes_relevant_docs_at_lower_ranks(self) -> None:
        """Relevant doc at rank 1 should score higher than at rank 5."""
        relevant = ["doc1"]

        ranked_top = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        score_top = compute_ndcg(ranked_top, relevant, k=10)

        ranked_low = ["doc2", "doc3", "doc4", "doc5", "doc1"]
        score_low = compute_ndcg(ranked_low, relevant, k=10)

        assert score_top > score_low

    def test_score_is_between_zero_and_one(self) -> None:
        relevant = ["doc1", "doc2"]
        ranked = ["doc3", "doc1", "doc4", "doc2", "doc5"]
        score = compute_ndcg(ranked, relevant, k=10)
        assert 0.0 <= score <= 1.0

    def test_single_relevant_doc_at_rank_1_is_1(self) -> None:
        """Single relevant doc at position 1 should give nDCG = 1.0."""
        score = compute_ndcg(["doc1"], ["doc1"], k=10)
        assert abs(score - 1.0) < 1e-9

    def test_relevant_doc_beyond_k_not_counted(self) -> None:
        """Relevant doc ranked beyond k should not be counted."""
        relevant = ["doc_rel"]
        ranked = ["doc_a", "doc_b", "doc_rel"]  # at rank 3 (0-indexed 2)
        score_k2 = compute_ndcg(ranked, relevant, k=2)
        assert score_k2 == 0.0

        score_k3 = compute_ndcg(ranked, relevant, k=3)
        assert score_k3 > 0.0

    def test_multiple_relevant_partial_match(self) -> None:
        """Partial matches should produce a score strictly between 0 and 1."""
        relevant = ["doc1", "doc2", "doc3"]
        ranked = ["doc1", "doc4", "doc5", "doc6", "doc7"]
        score = compute_ndcg(ranked, relevant, k=10)
        assert 0.0 < score < 1.0


class TestComputeDcg:
    """Tests for the compute_dcg() helper."""

    def test_dcg_single_relevant_at_rank_1(self) -> None:
        dcg = compute_dcg(["doc1"], {"doc1"}, k=10)
        expected = 1.0 / math.log2(2)
        assert abs(dcg - expected) < 1e-9

    def test_dcg_no_relevant(self) -> None:
        dcg = compute_dcg(["doc1", "doc2"], {"doc_rel"}, k=10)
        assert dcg == 0.0

    def test_dcg_empty_ranked(self) -> None:
        dcg = compute_dcg([], {"doc1"}, k=10)
        assert dcg == 0.0


class TestComputeIdealDcg:
    """Tests for the compute_ideal_dcg() helper."""

    def test_idcg_zero_relevant(self) -> None:
        idcg = compute_ideal_dcg(0, k=10)
        assert idcg == 0.0

    def test_idcg_one_relevant(self) -> None:
        idcg = compute_ideal_dcg(1, k=10)
        expected = 1.0 / math.log2(2)
        assert abs(idcg - expected) < 1e-9

    def test_idcg_more_relevant_than_k(self) -> None:
        """Relevant count > k: only k positions contribute."""
        idcg_k5 = compute_ideal_dcg(100, k=5)
        idcg_exact = compute_ideal_dcg(5, k=5)
        assert abs(idcg_k5 - idcg_exact) < 1e-9
