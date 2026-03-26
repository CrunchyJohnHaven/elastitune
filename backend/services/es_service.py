from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from elasticsearch import AsyncElasticsearch, NotFoundError, ConnectionError as ESConnectionError

logger = logging.getLogger(__name__)


class ESService:
    """Thin async wrapper around the Elasticsearch client."""

    def __init__(self, es_url: str, api_key: Optional[str] = None):
        kwargs: Dict[str, Any] = {
            "verify_certs": False,
            "ssl_show_warn": False,
        }
        if api_key:
            kwargs["api_key"] = api_key

        self.client = AsyncElasticsearch(es_url, **kwargs)
        self.es_url = es_url

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except Exception as exc:
            logger.warning("ES ping failed: %s", exc)
            return False

    async def get_cluster_info(self) -> Dict[str, Any]:
        try:
            info = await self.client.info()
            return dict(info)
        except Exception as exc:
            logger.error("get_cluster_info failed: %s", exc)
            return {}

    async def get_mapping(self, index: str) -> Dict[str, Any]:
        try:
            resp = await self.client.indices.get_mapping(index=index)
            return dict(resp)
        except NotFoundError:
            raise ValueError(f"Index '{index}' not found")
        except Exception as exc:
            logger.error("get_mapping failed for index '%s': %s", index, exc)
            raise

    async def count_docs(self, index: str) -> int:
        try:
            resp = await self.client.count(index=index)
            return int(resp.get("count", 0))
        except Exception as exc:
            logger.error("count_docs failed for index '%s': %s", index, exc)
            return 0

    async def sample_docs(self, index: str, size: int = 50) -> List[Dict[str, Any]]:
        try:
            resp = await self.client.search(
                index=index,
                body={"query": {"function_score": {"random_score": {}}}, "size": size},
                _source=True,
            )
            hits = resp.get("hits", {}).get("hits", [])
            return [{"_id": h["_id"], **h.get("_source", {})} for h in hits]
        except Exception as exc:
            logger.error("sample_docs failed for index '%s': %s", index, exc)
            return []

    async def search(self, index: str, query: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = await self.client.search(index=index, body=query)
            return dict(resp)
        except Exception as exc:
            logger.error("search failed for index '%s': %s", index, exc)
            return {"hits": {"hits": [], "total": {"value": 0}}}

    async def close(self) -> None:
        try:
            await self.client.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Higher-level analysis helpers
    # ------------------------------------------------------------------

    def _walk_properties(
        self, props: Dict[str, Any], prefix: str = ""
    ) -> List[Tuple[str, str]]:
        """Recursively walk mapping properties and return (field_path, type) pairs."""
        results: List[Tuple[str, str]] = []
        for field_name, field_meta in props.items():
            full_path = f"{prefix}.{field_name}" if prefix else field_name
            field_type = field_meta.get("type", "object")
            results.append((full_path, field_type))
            nested = field_meta.get("properties", {})
            if nested:
                results.extend(self._walk_properties(nested, full_path))
        return results

    async def analyze_index(
        self,
        index: str,
        vector_field_override: Optional[str] = None,
        max_sample_docs: int = 120,
    ) -> Dict[str, Any]:
        """
        Perform full index analysis:
        - Detect text fields and vector fields from the mapping
        - Sample docs for domain detection
        Returns a dict with keys: text_fields, vector_field, vector_dims, sample_docs, domain
        """
        mapping = await self.get_mapping(index)

        # Extract the properties for this index
        index_mapping = mapping.get(index, mapping)
        properties = (
            index_mapping.get("mappings", {}).get("properties", {})
        )

        all_fields = self._walk_properties(properties)

        text_fields: List[str] = []
        vector_field: Optional[str] = None
        vector_dims: Optional[int] = None

        for field_path, field_type in all_fields:
            if field_type in ("text", "match_only_text", "annotated_text"):
                text_fields.append(field_path)
            elif field_type in ("dense_vector", "knn_vector"):
                # Pick the first (or overridden) vector field
                dims = None
                # navigate to the field meta
                parts = field_path.split(".")
                meta = properties
                for part in parts:
                    meta = meta.get(part, {}) if isinstance(meta, dict) else {}
                    if meta.get("properties"):
                        meta = meta["properties"]
                dims = meta.get("dims") if isinstance(meta, dict) else None

                if vector_field_override:
                    if field_path == vector_field_override:
                        vector_field = field_path
                        vector_dims = dims
                elif vector_field is None:
                    vector_field = field_path
                    vector_dims = dims

        # Sample docs for domain detection
        docs = await self.sample_docs(index, size=min(max_sample_docs, 50))

        domain = self._detect_domain(docs, text_fields)

        return {
            "text_fields": text_fields,
            "vector_field": vector_field,
            "vector_dims": vector_dims,
            "sample_docs": docs,
            "domain": domain,
        }

    def _detect_domain(
        self, docs: List[Dict[str, Any]], text_fields: List[str]
    ) -> str:
        """Heuristic domain detection from sampled document content."""
        security_keywords = {
            "cve", "vulnerability", "exploit", "patch", "malware", "threat",
            "firewall", "breach", "attack", "ransomware", "phishing",
        }
        dev_keywords = {
            "api", "function", "method", "class", "module", "library",
            "sdk", "endpoint", "parameter", "return", "exception", "import",
        }
        compliance_keywords = {
            "regulation", "compliance", "gdpr", "hipaa", "audit", "policy",
            "requirement", "control", "framework", "standard", "sox", "pci",
        }

        text_blob = ""
        for doc in docs[:30]:
            for field in text_fields[:5]:
                val = doc.get(field, "")
                if isinstance(val, str):
                    text_blob += " " + val.lower()

        words = set(text_blob.split())

        scores = {
            "security": len(words & security_keywords),
            "developer_docs": len(words & dev_keywords),
            "compliance": len(words & compliance_keywords),
            "general": 0,
        }

        best = max(scores, key=lambda k: scores[k])
        return best if scores[best] > 0 else "general"

    async def build_baseline_profile(
        self,
        text_fields: List[str],
        vector_field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build initial SearchProfile-compatible dict from discovered fields."""
        lexical_fields = [
            {"field": f, "boost": 2.0 if i == 0 else 1.0}
            for i, f in enumerate(text_fields[:8])
        ]
        return {
            "lexicalFields": lexical_fields,
            "multiMatchType": "best_fields",
            "minimumShouldMatch": "75%",
            "tieBreaker": 0.0,
            "phraseBoost": 0.0,
            "fuzziness": "0",
            "useVector": vector_field is not None,
            "vectorField": vector_field,
            "vectorWeight": 0.35,
            "lexicalWeight": 0.65,
            "fusionMethod": "weighted_sum",
            "rrfRankConstant": 60,
            "knnK": 20,
            "numCandidates": 100,
        }

    async def execute_profile_query(
        self,
        index: str,
        query_text: str,
        profile: Any,
        size: int = 20,
    ) -> List[str]:
        """
        Execute a search using the given SearchProfile and return a ranked list of doc IDs.
        `profile` should be a SearchProfile model instance or compatible dict.
        """
        from ..models.contracts import SearchProfile

        if isinstance(profile, dict):
            p = SearchProfile(**profile)
        else:
            p = profile

        body = self._build_query_body(query_text, p, size)
        resp = await self.search(index, body)
        hits = resp.get("hits", {}).get("hits", [])
        if not hits and p.useVector:
            logger.warning(
                "Hybrid query returned no hits for '%s'; retrying with lexical-only search",
                query_text,
            )
            fallback_profile = p.model_copy(deep=True)
            fallback_profile.useVector = False
            fallback_profile.vectorWeight = 0.0
            fallback_body = self._build_query_body(query_text, fallback_profile, size)
            resp = await self.search(index, fallback_body)
            hits = resp.get("hits", {}).get("hits", [])
        return [h["_id"] for h in hits]

    async def execute_profile_query_with_hits(
        self,
        index: str,
        query_text: str,
        profile: Any,
        size: int = 5,
    ) -> List[Dict[str, Any]]:
        from ..models.contracts import SearchProfile

        if isinstance(profile, dict):
            p = SearchProfile(**profile)
        else:
            p = profile

        body = self._build_query_body(query_text, p, size)
        resp = await self.search(index, body)
        hits = resp.get("hits", {}).get("hits", [])
        if not hits and p.useVector:
            fallback_profile = p.model_copy(deep=True)
            fallback_profile.useVector = False
            fallback_profile.vectorWeight = 0.0
            fallback_body = self._build_query_body(query_text, fallback_profile, size)
            resp = await self.search(index, fallback_body)
            hits = resp.get("hits", {}).get("hits", [])
        return [self._format_hit_preview(hit) for hit in hits[:size]]

    def build_query_body(
        self,
        query_text: str,
        profile: Any,
        size: int = 20,
    ) -> Dict[str, Any]:
        from ..models.contracts import SearchProfile

        if isinstance(profile, dict):
            p = SearchProfile(**profile)
        else:
            p = profile
        return self._build_query_body(query_text, p, size)

    def _build_query_body(self, query_text: str, p: Any, size: int = 20) -> Dict[str, Any]:
        """Build Elasticsearch query body from a SearchProfile."""
        fields = [
            f"{f['field']}^{f.get('boost', 1.0)}" for f in p.lexicalFields
        ] if p.lexicalFields else ["*"]

        multi_match: Dict[str, Any] = {
            "query": query_text,
            "fields": fields,
            "type": p.multiMatchType,
            "minimum_should_match": p.minimumShouldMatch,
        }
        if p.tieBreaker > 0:
            multi_match["tie_breaker"] = p.tieBreaker
        if p.fuzziness != "0":
            multi_match["fuzziness"] = p.fuzziness

        lexical_query: Dict[str, Any] = {"multi_match": multi_match}

        # Add phrase boost if set
        if p.phraseBoost > 0 and p.lexicalFields:
            top_field = p.lexicalFields[0]["field"] if p.lexicalFields else "_all"
            lexical_query = {
                "bool": {
                    "must": [{"multi_match": multi_match}],
                    "should": [
                        {
                            "match_phrase": {
                                top_field: {
                                    "query": query_text,
                                    "boost": p.phraseBoost,
                                }
                            }
                        }
                    ],
                }
            }

        if p.useVector and p.vectorField:
            # Hybrid: use knn + lexical fusion
            body: Dict[str, Any] = {
                "size": size,
                "query": lexical_query,
                "knn": {
                    "field": p.vectorField,
                    "query_vector_builder": {
                        "text_embedding": {
                            "model_id": ".elser_model_2",
                            "model_text": query_text,
                        }
                    },
                    "k": p.knnK,
                    "num_candidates": p.numCandidates,
                    "boost": p.vectorWeight,
                },
            }
        else:
            body = {"size": size, "query": lexical_query}

        return body

    def _format_hit_preview(self, hit: Dict[str, Any]) -> Dict[str, Any]:
        source = hit.get("_source", {}) if isinstance(hit.get("_source"), dict) else {}
        title = (
            source.get("title")
            or source.get("name")
            or source.get("book_title")
            or source.get("summary")
            or source.get("description")
            or source.get("content")
            or hit.get("_id")
            or "Untitled result"
        )
        excerpt = (
            source.get("description")
            or source.get("summary")
            or source.get("content")
            or ""
        )
        return {
            "docId": str(hit.get("_id", "")),
            "title": str(title)[:140],
            "excerpt": str(excerpt)[:240],
            "score": float(hit.get("_score") or 0.0),
        }
