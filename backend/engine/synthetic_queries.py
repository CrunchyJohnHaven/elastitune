import json
from typing import List, Dict
from ..models.contracts import EvalCase, ConnectionSummary


class SyntheticQueryGenerator:
    def __init__(self, llm_service=None):
        self.llm = llm_service

    async def generate(
        self,
        summary: ConnectionSummary,
        sample_docs: List[Dict],
        target_count: int = 100,
    ) -> List[EvalCase]:
        """Generate eval cases from sample docs."""
        if self.llm and self.llm.available:
            return await self._llm_generate(summary, sample_docs, target_count)
        return self._heuristic_generate(summary, sample_docs, target_count)

    async def _llm_generate(self, summary, sample_docs, target_count) -> List[EvalCase]:
        """Use LLM to generate queries."""

        # Load prompt template
        from pathlib import Path

        prompt_path = Path(__file__).parent.parent / "prompts" / "synthetic_queries.txt"
        prompt_template = prompt_path.read_text()

        eval_cases = []
        per_doc = max(1, min(2, target_count // max(len(sample_docs), 1)))

        for doc in sample_docs[:target_count]:
            try:
                user_msg = json.dumps(
                    {
                        "domain": summary.detectedDomain,
                        "document": {
                            "id": doc.get("_id", "unknown"),
                            "fields": {
                                k: str(v)[:200]
                                for k, v in doc.get("_source", {}).items()
                            },
                        },
                        "generate_count": per_doc,
                    },
                    indent=2,
                )

                result = await self.llm.complete_json(prompt_template, user_msg)
                if isinstance(result, list):
                    for item in result[:per_doc]:
                        eval_cases.append(
                            EvalCase(
                                id=f"eval_{len(eval_cases):04d}",
                                query=item.get("query", ""),
                                relevantDocIds=item.get(
                                    "relevantDocIds", [doc.get("_id")]
                                ),
                                personaHint=item.get("personaHint"),
                                difficulty=item.get("difficulty", "medium"),
                            )
                        )
                elif isinstance(result, dict) and "query" in result:
                    eval_cases.append(
                        EvalCase(
                            id=f"eval_{len(eval_cases):04d}",
                            query=result["query"],
                            relevantDocIds=result.get(
                                "relevantDocIds", [doc.get("_id")]
                            ),
                            personaHint=result.get("personaHint"),
                            difficulty=result.get("difficulty", "medium"),
                        )
                    )
            except Exception:
                continue

            if len(eval_cases) >= target_count:
                break

        if len(eval_cases) < 10:
            return self._heuristic_generate(summary, sample_docs, target_count)

        return eval_cases[:target_count]

    def _heuristic_generate(
        self, summary: ConnectionSummary, sample_docs: List[Dict], target_count: int
    ) -> List[EvalCase]:
        """Fallback heuristic query generation."""
        eval_cases = []

        title_fields = ["title", "name", "headline", "subject"]
        body_fields = ["message", "description", "body", "content", "text"]

        for doc in sample_docs:
            source = doc.get("_source", {})
            doc_id = doc.get("_id", "unknown")

            # Find title and body
            title_val = None
            for f in title_fields:
                if f in source and source[f]:
                    title_val = str(source[f])[:100]
                    break

            body_val = None
            for f in body_fields:
                if f in source and source[f]:
                    body_val = str(source[f])[:300]
                    break

            if not title_val and not body_val:
                # Use first non-empty string field
                for v in source.values():
                    if isinstance(v, str) and len(v) > 5:
                        title_val = v[:100]
                        break

            if title_val:
                # Short keyword query from title words
                words = [w for w in title_val.split() if len(w) > 3 and w.isalpha()][:4]
                if words:
                    eval_cases.append(
                        EvalCase(
                            id=f"eval_{len(eval_cases):04d}",
                            query=" ".join(words),
                            relevantDocIds=[doc_id],
                            difficulty="easy",
                        )
                    )

            if body_val and len(eval_cases) < target_count:
                # Natural language query from first sentence
                sentences = body_val.split(".")
                first = sentences[0].strip() if sentences else ""
                if 10 < len(first) < 120:
                    eval_cases.append(
                        EvalCase(
                            id=f"eval_{len(eval_cases):04d}",
                            query=first,
                            relevantDocIds=[doc_id],
                            difficulty="medium",
                        )
                    )

            if len(eval_cases) >= target_count:
                break

        return eval_cases[:target_count]
