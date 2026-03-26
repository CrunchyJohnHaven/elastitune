import math
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from ..models.contracts import SearchProfile, EvalCase, ConnectionSummary


def compute_dcg(ranked_ids: List[str], relevant_ids: set, k: int = 10) -> float:
    """Compute DCG@k."""
    dcg = 0.0
    for i, doc_id in enumerate(ranked_ids[:k]):
        if doc_id in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)
    return dcg


def compute_ideal_dcg(relevant_count: int, k: int = 10) -> float:
    """Compute ideal DCG@k."""
    idcg = 0.0
    for i in range(min(relevant_count, k)):
        idcg += 1.0 / math.log2(i + 2)
    return idcg


def compute_ndcg(ranked_ids: List[str], relevant_ids: List[str], k: int = 10) -> float:
    """Compute nDCG@k."""
    rel_set = set(relevant_ids)
    dcg = compute_dcg(ranked_ids, rel_set, k)
    idcg = compute_ideal_dcg(len(rel_set), k)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def build_lexical_query(query_text: str, profile: SearchProfile, size: int = 50) -> Dict:
    """Build ES query from search profile."""
    fields_with_boosts = [
        f"{f['field']}^{f['boost']}" for f in profile.lexicalFields
    ]

    should_clauses = [
        {
            "multi_match": {
                "query": query_text,
                "type": profile.multiMatchType,
                "fields": fields_with_boosts,
                "minimum_should_match": profile.minimumShouldMatch,
                "tie_breaker": profile.tieBreaker,
                "fuzziness": profile.fuzziness,
            }
        }
    ]

    if profile.phraseBoost > 0:
        should_clauses.append({
            "multi_match": {
                "query": query_text,
                "type": "phrase",
                "fields": fields_with_boosts,
                "boost": profile.phraseBoost,
            }
        })

    return {
        "size": size,
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        }
    }


def rrf_fuse(lexical_ids: List[str], vector_ids: List[str], k: int = 60) -> List[str]:
    """Reciprocal rank fusion."""
    scores = {}
    for rank, doc_id in enumerate(lexical_ids):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rank + 1 + k)
    for rank, doc_id in enumerate(vector_ids):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rank + 1 + k)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


def weighted_fuse(lexical_hits: List[Dict], vector_hits: List[Dict],
                  lex_weight: float, vec_weight: float) -> List[str]:
    """Weighted score fusion after normalization."""
    def normalize(hits):
        if not hits:
            return {}
        scores = {h['_id']: h['_score'] or 0.0 for h in hits}
        max_s = max(scores.values()) or 1.0
        min_s = min(scores.values())
        return {k: (v - min_s) / (max_s - min_s + 1e-9) for k, v in scores.items()}

    lex_norm = normalize(lexical_hits)
    vec_norm = normalize(vector_hits)

    all_ids = set(lex_norm) | set(vec_norm)
    final = {
        doc_id: lex_weight * lex_norm.get(doc_id, 0.0) + vec_weight * vec_norm.get(doc_id, 0.0)
        for doc_id in all_ids
    }
    return sorted(final.keys(), key=lambda x: final[x], reverse=True)


class Evaluator:
    def __init__(self, es_service, summary: ConnectionSummary):
        self.es = es_service
        self.summary = summary

    async def evaluate(self, profile: SearchProfile, eval_set: List[EvalCase]) -> Tuple[float, List[str]]:
        """Run evaluation. Returns (mean_ndcg10, list_of_failure_query_ids)."""
        if not eval_set:
            return 0.0, []

        ndcg_scores = []
        failures = []

        for case in eval_set:
            try:
                query = build_lexical_query(case.query, profile, size=50)
                result = await self.es.search(self.summary.indexName, query)
                hits = result.get("hits", {}).get("hits", [])
                ranked_ids = [h["_id"] for h in hits]
                ndcg = compute_ndcg(ranked_ids, case.relevantDocIds)
                ndcg_scores.append(ndcg)
                if ndcg < 0.1:
                    failures.append(case.query)
            except Exception:
                ndcg_scores.append(0.0)
                failures.append(case.query)

        mean_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
        return mean_ndcg, failures

    async def evaluate_demo(self, profile: SearchProfile, eval_set: List[EvalCase]) -> Tuple[float, List[str]]:
        """Demo mode evaluation - simulate scores based on profile quality."""
        # Simulate a meaningful score based on profile parameters
        base = 0.41
        score = base

        # Boost contributions
        title_boost = next((f['boost'] for f in profile.lexicalFields if f['field'] in ('title', 'name')), 1.0)
        score += (title_boost - 1.0) * 0.015

        if profile.multiMatchType == 'cross_fields':
            score += 0.008
        elif profile.multiMatchType == 'phrase':
            score += 0.005

        if profile.phraseBoost > 0:
            score += profile.phraseBoost * 0.01

        if profile.minimumShouldMatch == '2<75%':
            score += 0.012

        score = min(score, 0.62)
        score = max(score, 0.38)

        import random
        score += random.gauss(0, 0.005)

        return score, []
