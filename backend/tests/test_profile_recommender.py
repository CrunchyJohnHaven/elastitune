from __future__ import annotations

from backend.models.contracts import ConnectionSummary, SearchProfile
from backend.services.profile_recommender import ProfileRecommender


def _make_summary(
    index_name: str = "generic-index",
    detected_domain: str = "general",
    fields: list[str] | None = None,
) -> ConnectionSummary:
    if fields is None:
        fields = ["title", "description"]
    return ConnectionSummary(
        clusterName="test-cluster",
        indexName=index_name,
        docCount=1000,
        detectedDomain=detected_domain,  # type: ignore[arg-type]
        primaryTextFields=fields,
        baselineEvalCount=10,
        baselineReady=True,
    )


def _make_profile(fields: list[str] | None = None) -> SearchProfile:
    if fields is None:
        fields = ["title", "description"]
    return SearchProfile(
        lexicalFields=[
            {"field": f, "boost": 2.0 if i == 0 else 1.0}
            for i, f in enumerate(fields)
        ]
    )


class TestProfileRecommenderReturnsValidProfile:
    """Test that recommendations always return a valid SearchProfile."""

    def test_returns_search_profile_instance(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary()
        profile = _make_profile()
        result, _ = rec.recommend(summary, profile)
        assert isinstance(result, SearchProfile)

    def test_returns_tuple_of_profile_and_optional_string(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary()
        profile = _make_profile()
        result = rec.recommend(summary, profile)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], SearchProfile)
        assert result[1] is None or isinstance(result[1], str)

    def test_no_matching_benchmark_returns_baseline_unchanged(self) -> None:
        rec = ProfileRecommender()
        # Use an index name and fields that do not match any benchmark
        summary = _make_summary(index_name="completely-unknown-xyz", detected_domain="general")
        profile = _make_profile(["body_text"])
        result_profile, benchmark_name = rec.recommend(summary, profile)
        # Should return the baseline profile when nothing matches
        assert benchmark_name is None
        assert result_profile is profile

    def test_recommended_profile_has_valid_lexical_fields(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(detected_domain="security")
        profile = _make_profile(["title", "description"])
        result_profile, _ = rec.recommend(summary, profile)
        assert isinstance(result_profile.lexicalFields, list)
        for entry in result_profile.lexicalFields:
            assert hasattr(entry, "field") or isinstance(entry, dict)

    def test_recommended_profile_has_valid_multi_match_type(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(detected_domain="security")
        profile = _make_profile(["title", "description"])
        result_profile, _ = rec.recommend(summary, profile)
        valid_types = {"best_fields", "most_fields", "cross_fields", "phrase"}
        assert result_profile.multiMatchType in valid_types

    def test_result_profile_minimum_should_match_is_string(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(detected_domain="security")
        profile = _make_profile(["title", "description"])
        result_profile, _ = rec.recommend(summary, profile)
        assert isinstance(result_profile.minimumShouldMatch, str)

    def test_result_profile_phrase_boost_is_non_negative(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(detected_domain="security")
        profile = _make_profile(["title", "description"])
        result_profile, _ = rec.recommend(summary, profile)
        assert result_profile.phraseBoost >= 0.0


class TestProfileRecommenderFieldDetection:
    """Test that the _pick_benchmark method correctly detects domains from fields/index names."""

    def test_security_domain_picks_security_siem(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(detected_domain="security")
        profile = _make_profile()
        _, benchmark_name = rec.recommend(summary, profile)
        # If the benchmark file has Security SIEM, it should match; if not, it may be None
        # Either way, the pick_benchmark itself should return "Security SIEM"
        picked = rec._pick_benchmark(summary, profile)
        assert picked == "Security SIEM"

    def test_movie_index_picks_tmdb(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(index_name="movies-catalog", detected_domain="general")
        profile = _make_profile(["title", "overview"])
        picked = rec._pick_benchmark(summary, profile)
        assert picked == "TMDB Movies"

    def test_book_index_picks_books_catalog(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(index_name="book-library", detected_domain="general")
        profile = _make_profile(["title", "description"])
        picked = rec._pick_benchmark(summary, profile)
        assert picked == "Books Catalog"

    def test_product_index_picks_product_store(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(index_name="product-catalog", detected_domain="general")
        profile = _make_profile(["brand", "description"])
        picked = rec._pick_benchmark(summary, profile)
        assert picked == "Product Store"

    def test_workplace_index_picks_workplace_docs(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(index_name="workplace-policies", detected_domain="general")
        profile = _make_profile(["title", "content"])
        picked = rec._pick_benchmark(summary, profile)
        assert picked == "Workplace Docs"

    def test_unknown_index_picks_none(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(index_name="zzz-completely-unknown", detected_domain="general")
        profile = _make_profile(["fieldA", "fieldB"])
        picked = rec._pick_benchmark(summary, profile)
        assert picked is None

    def test_siem_token_in_index_matches_security(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(index_name="siem-logs", detected_domain="general")
        profile = _make_profile(["message", "host"])
        picked = rec._pick_benchmark(summary, profile)
        assert picked == "Security SIEM"

    def test_field_name_cast_director_matches_tmdb(self) -> None:
        rec = ProfileRecommender()
        summary = _make_summary(index_name="entertainment", detected_domain="general")
        profile = _make_profile(["title", "cast"])
        picked = rec._pick_benchmark(summary, profile)
        assert picked == "TMDB Movies"
