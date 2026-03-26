from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.contracts import ConnectionSummary, SearchProfile


RESULTS_PATH = Path(__file__).resolve().parents[2] / "benchmark_results.json"


class ProfileRecommender:
    def recommend(
        self,
        summary: ConnectionSummary,
        baseline_profile: SearchProfile,
    ) -> tuple[SearchProfile, Optional[str]]:
        benchmark_name = self._pick_benchmark(summary, baseline_profile)
        if not benchmark_name:
            return baseline_profile, None

        benchmark = _load_benchmark_results().get(benchmark_name)
        if not benchmark:
            return baseline_profile, None

        best_profile = SearchProfile.model_validate(benchmark["best_profile"])
        recommended = baseline_profile.model_copy(deep=True)
        recommended.multiMatchType = best_profile.multiMatchType
        recommended.minimumShouldMatch = best_profile.minimumShouldMatch
        recommended.tieBreaker = best_profile.tieBreaker
        recommended.phraseBoost = best_profile.phraseBoost
        recommended.fuzziness = best_profile.fuzziness
        recommended.useVector = baseline_profile.useVector and best_profile.useVector
        recommended.fusionMethod = best_profile.fusionMethod
        recommended.rrfRankConstant = best_profile.rrfRankConstant
        recommended.knnK = best_profile.knnK
        recommended.numCandidates = best_profile.numCandidates
        recommended.vectorWeight = (
            best_profile.vectorWeight if recommended.useVector else 0.0
        )
        recommended.lexicalWeight = (
            best_profile.lexicalWeight if recommended.useVector else 1.0
        )

        benchmark_boosts = {
            item["field"]: item["boost"] for item in best_profile.lexicalFields
        }
        for field in recommended.lexicalFields:
            if field["field"] in benchmark_boosts:
                field["boost"] = benchmark_boosts[field["field"]]

        return recommended, benchmark_name

    def _pick_benchmark(
        self,
        summary: ConnectionSummary,
        baseline_profile: SearchProfile,
    ) -> Optional[str]:
        index = summary.indexName.lower()
        fields = " ".join(
            field["field"].lower() for field in baseline_profile.lexicalFields
        )

        if summary.detectedDomain == "security" or any(
            token in index for token in ["siem", "alert", "threat", "security"]
        ):
            return "Security SIEM"
        if any(token in index for token in ["movie", "tmdb", "film"]) or any(
            token in fields for token in ["overview", "cast", "director"]
        ):
            return "TMDB Movies"
        if any(token in index for token in ["book", "library"]) or any(
            token in fields for token in ["authors", "categories", "published_year"]
        ):
            return "Books Catalog"
        if any(token in index for token in ["workplace", "policy", "hr"]) or any(
            token in fields for token in ["summary", "content", "role_permissions"]
        ):
            return "Workplace Docs"
        if any(token in index for token in ["product", "catalog", "store"]) or any(
            token in fields for token in ["brand", "price", "product_type"]
        ):
            return "Product Store"
        return None


@lru_cache(maxsize=1)
def _load_benchmark_results() -> Dict[str, Dict[str, Any]]:
    if not RESULTS_PATH.exists():
        return {}
    with RESULTS_PATH.open() as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}
