"""Tests for backend.engine.optimizer_search_space."""

from __future__ import annotations

import random

from backend.engine.optimizer_search_space import (
    generate_mutations,
    generate_security_field_mutations,
    pick_mutation,
)
from backend.models.contracts import LexicalFieldEntry, SearchProfile, SearchProfileChange


def _basic_profile(**overrides) -> SearchProfile:
    """Return a minimal SearchProfile with sensible defaults."""
    defaults = dict(
        lexicalFields=[
            LexicalFieldEntry(field="title", boost=1.0),
            LexicalFieldEntry(field="body", boost=2.0),
        ],
        multiMatchType="best_fields",
        minimumShouldMatch="75%",
        tieBreaker=0.0,
        phraseBoost=0.0,
        fuzziness="0",
        useVector=False,
    )
    defaults.update(overrides)
    return SearchProfile(**defaults)


# ── generate_mutations: basic profile ────────────────────────────────────────


class TestGenerateMutationsBasic:
    def test_generates_field_boost_mutations(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        boost_changes = [
            c for _, c in mutations if c.path.startswith("lexicalFields[") and "boost" in c.path
        ]
        assert len(boost_changes) > 0
        # Should have mutations for both fields
        field0 = [c for c in boost_changes if c.path.startswith("lexicalFields[0]")]
        field1 = [c for c in boost_changes if c.path.startswith("lexicalFields[1]")]
        assert len(field0) > 0
        assert len(field1) > 0

    def test_generates_multi_match_type_mutations(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        mm_changes = [c for _, c in mutations if c.path == "multiMatchType"]
        # Current is best_fields, so should get mutations for the other 3 types
        assert len(mm_changes) == 3
        after_values = {c.after for c in mm_changes}
        assert after_values == {"most_fields", "cross_fields", "phrase"}

    def test_generates_minimum_should_match_mutations(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        msm_changes = [c for _, c in mutations if c.path == "minimumShouldMatch"]
        # 75% is the default, so we should see len(MIN_SHOULD_MATCH_VALUES) - 1 mutations
        assert len(msm_changes) == 7

    def test_generates_tie_breaker_mutations(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        tb_changes = [c for _, c in mutations if c.path == "tieBreaker"]
        assert len(tb_changes) > 0

    def test_generates_phrase_boost_mutations(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        pb_changes = [c for _, c in mutations if c.path == "phraseBoost"]
        assert len(pb_changes) > 0

    def test_generates_fuzziness_mutations(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        fuzz_changes = [c for _, c in mutations if c.path == "fuzziness"]
        assert len(fuzz_changes) > 0

    def test_mutation_profiles_differ_from_original(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        for new_profile, change in mutations[:5]:
            assert new_profile != profile


# ── generate_mutations: recently_reverted filtering ──────────────────────────


class TestRecentlyRevertedFiltering:
    def test_filters_out_recently_reverted_paths(self):
        profile = _basic_profile()
        reverted = ["multiMatchType", "minimumShouldMatch"]
        mutations = generate_mutations(profile, [], reverted)
        for _, c in mutations:
            assert c.path not in reverted

    def test_no_filtering_with_empty_reverted_list(self):
        profile = _basic_profile()
        all_mutations = generate_mutations(profile, [], [])
        no_filter_mutations = generate_mutations(profile, [], [])
        assert len(all_mutations) == len(no_filter_mutations)

    def test_filters_field_boost_path(self):
        profile = _basic_profile()
        reverted = ["lexicalFields[0].boost"]
        mutations = generate_mutations(profile, [], reverted)
        for _, c in mutations:
            assert c.path != "lexicalFields[0].boost"
        # Field 1 boosts should still be present
        field1_boosts = [c for _, c in mutations if c.path == "lexicalFields[1].boost"]
        assert len(field1_boosts) > 0


# ── generate_mutations: cross_fields + fuzziness filtering ───────────────────


class TestCrossFieldsFuzzinessFiltering:
    def test_cross_fields_with_auto_fuzziness_filtered(self):
        """When current profile has fuzziness=AUTO, switching to cross_fields should be filtered."""
        profile = _basic_profile(fuzziness="AUTO")
        mutations = generate_mutations(profile, [], [])
        # Any mutation that results in cross_fields + fuzziness != "0" should be excluded
        for new_profile, change in mutations:
            if new_profile.multiMatchType == "cross_fields":
                assert new_profile.fuzziness == "0"

    def test_cross_fields_with_zero_fuzziness_allowed(self):
        """cross_fields with fuzziness=0 should be allowed."""
        profile = _basic_profile(fuzziness="0")
        mutations = generate_mutations(profile, [], [])
        cross_changes = [
            c for p, c in mutations
            if c.path == "multiMatchType" and c.after == "cross_fields"
        ]
        assert len(cross_changes) == 1

    def test_fuzziness_auto_when_cross_fields_filtered(self):
        """When profile is cross_fields, switching fuzziness to AUTO should be filtered."""
        profile = _basic_profile(multiMatchType="cross_fields", fuzziness="0")
        mutations = generate_mutations(profile, [], [])
        for new_profile, _ in mutations:
            if new_profile.multiMatchType == "cross_fields":
                assert new_profile.fuzziness == "0"


# ── generate_mutations: vector mutations ─────────────────────────────────────


class TestVectorMutations:
    def test_no_vector_mutations_when_use_vector_false(self):
        profile = _basic_profile(useVector=False)
        mutations = generate_mutations(profile, [], [])
        vector_paths = {"lexicalWeight", "fusionMethod", "rrfRankConstant", "knnK", "numCandidates"}
        for _, c in mutations:
            assert c.path not in vector_paths

    def test_vector_mutations_present_when_use_vector_true(self):
        profile = _basic_profile(useVector=True)
        mutations = generate_mutations(profile, [], [])
        vector_paths = {"lexicalWeight", "fusionMethod", "rrfRankConstant", "knnK", "numCandidates"}
        found_paths = {c.path for _, c in mutations}
        for vp in vector_paths:
            assert vp in found_paths, f"Expected vector mutation path '{vp}' not found"

    def test_vector_weight_mutations_have_correct_pairs(self):
        profile = _basic_profile(useVector=True, lexicalWeight=0.65, vectorWeight=0.35)
        mutations = generate_mutations(profile, [], [])
        weight_changes = [
            (p, c) for p, c in mutations if c.path == "lexicalWeight"
        ]
        for new_profile, change in weight_changes:
            # lexicalWeight + vectorWeight should roughly sum to 1.0
            assert abs(new_profile.lexicalWeight + new_profile.vectorWeight - 1.0) < 0.01


# ── pick_mutation ─────────────────────────────────────────────────────────────


class TestPickMutation:
    def test_returns_mutation_from_nonempty_list(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        result = pick_mutation(mutations, rng=random.Random(42))
        assert result is not None
        assert len(result) == 2
        assert isinstance(result[1], SearchProfileChange)

    def test_returns_none_for_empty_list(self):
        result = pick_mutation([])
        assert result is None

    def test_deterministic_with_seeded_rng(self):
        profile = _basic_profile()
        mutations = generate_mutations(profile, [], [])
        r1 = pick_mutation(mutations, rng=random.Random(99))
        r2 = pick_mutation(mutations, rng=random.Random(99))
        assert r1[1].path == r2[1].path
        assert r1[1].after == r2[1].after


# ── generate_security_field_mutations ────────────────────────────────────────


class TestGenerateSecurityFieldMutations:
    def test_returns_mutations_for_security_fields(self):
        profile = SearchProfile(
            lexicalFields=[
                LexicalFieldEntry(field="rule.name", boost=1.0),
                LexicalFieldEntry(field="mitre.technique", boost=1.0),
                LexicalFieldEntry(field="severity", boost=1.0),
            ]
        )
        changes = generate_security_field_mutations(profile)
        assert len(changes) > 0
        # Each security field should get mutations for each priority boost != current
        # 3 fields x 4 boosts (all != 1.0) = 12
        assert len(changes) == 12
        for c in changes:
            assert "boost" in c.path
            assert c.after in [2.0, 3.0, 4.0, 5.0]

    def test_returns_empty_for_non_security_fields(self):
        profile = SearchProfile(
            lexicalFields=[
                LexicalFieldEntry(field="title", boost=1.0),
                LexicalFieldEntry(field="body", boost=1.0),
                LexicalFieldEntry(field="description", boost=1.0),
            ]
        )
        changes = generate_security_field_mutations(profile)
        assert changes == []

    def test_mixed_fields_only_mutates_security(self):
        profile = SearchProfile(
            lexicalFields=[
                LexicalFieldEntry(field="title", boost=1.0),
                LexicalFieldEntry(field="source.ip", boost=1.0),
                LexicalFieldEntry(field="description", boost=1.0),
            ]
        )
        changes = generate_security_field_mutations(profile)
        # Only source.ip is security-relevant
        assert len(changes) == 4  # 4 priority boosts != 1.0
        for c in changes:
            assert "lexicalFields[1]" in c.path

    def test_skips_boost_matching_current(self):
        profile = SearchProfile(
            lexicalFields=[
                LexicalFieldEntry(field="category", boost=3.0),
            ]
        )
        changes = generate_security_field_mutations(profile)
        # 3.0 is already the current boost, so only 3 of the 4 priority boosts
        assert len(changes) == 3
        for c in changes:
            assert c.after != 3.0
