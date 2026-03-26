from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from ..models.contracts import LlmConfig
from ..committee.models import CommitteePersona, DocumentSection

logger = logging.getLogger(__name__)


class LLMService:
    """Thin async LLM client supporting OpenAI-compatible APIs."""

    def __init__(self, config: LlmConfig):
        self.config = config
        self.available = config.provider != "disabled"

    async def complete(self, system: str, user: str) -> Optional[str]:
        """Call LLM and return text response. Returns None if unavailable or on error."""
        if not self.available:
            return None

        try:
            if self.config.provider == "anthropic":
                return await self._complete_anthropic(system, user)
            return await self._complete_openai_compatible(system, user)
        except Exception as exc:
            logger.warning("LLM complete failed: %s", exc)
            return None

    async def _complete_openai_compatible(
        self, system: str, user: str
    ) -> Optional[str]:
        base_url = (self.config.baseUrl or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.config.apiKey:
            headers["Authorization"] = f"Bearer {self.config.apiKey}"

        body: Dict[str, Any] = {
            "model": self.config.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _complete_anthropic(self, system: str, user: str) -> Optional[str]:
        base_url = (self.config.baseUrl or "https://api.anthropic.com").rstrip("/")
        url = f"{base_url}/v1/messages"
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.config.apiKey:
            headers["x-api-key"] = self.config.apiKey

        body: Dict[str, Any] = {
            "model": self.config.model or "claude-3-5-sonnet-latest",
            "max_tokens": 1400,
            "temperature": 0.5,
            "system": system,
            "messages": [
                {"role": "user", "content": user},
            ],
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            chunks = data.get("content", [])
            if chunks and isinstance(chunks, list):
                return "".join(
                    str(chunk.get("text", ""))
                    for chunk in chunks
                    if isinstance(chunk, dict)
                )
            return None

    async def complete_json(self, system: str, user: str) -> Optional[Any]:
        """Call LLM and parse JSON from response. Returns None on failure."""
        text = await self.complete(system, user)
        if not text:
            logger.warning("LLM JSON completion returned empty text.")
            return None

        # Extract JSON from markdown code blocks if present
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find a raw JSON object/array in the response
            json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    logger.warning("LLM regex JSON extraction also failed.")
            logger.warning("LLM returned non-JSON text: %s", text[:200])
            return None

    async def generate_eval_set(
        self,
        domain: str,
        sample_docs: List[Dict[str, Any]],
        text_fields: List[str],
        count: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Ask the LLM to generate evaluation queries from sample documents.
        Returns a list of dicts with keys: id, query, relevantDocIds, difficulty, personaHint.
        """
        if not self.available:
            return []

        # Build a compact document summary for the prompt
        doc_summaries: List[str] = []
        for i, doc in enumerate(sample_docs[:15]):
            parts = []
            for field in text_fields[:3]:
                val = doc.get(field, "")
                if isinstance(val, str) and val:
                    parts.append(val[:200])
            if parts:
                doc_summaries.append(f"Doc {doc.get('_id', i)}: {' | '.join(parts)}")

        docs_text = "\n".join(doc_summaries)

        system_prompt = (
            f"You are an expert search quality evaluator for a {domain} knowledge base. "
            "Generate realistic evaluation queries that users would actually search for. "
            "Each query must have at least one clearly relevant document from the provided samples."
        )

        user_prompt = (
            f"Here are sample documents from the index:\n{docs_text}\n\n"
            f"Generate {count} evaluation cases as a JSON array. Each item must have:\n"
            '- "id": unique string like "eval_001"\n'
            '- "query": a realistic search query string\n'
            '- "relevantDocIds": array of document IDs that are relevant (from the samples)\n'
            '- "difficulty": "easy", "medium", or "hard"\n'
            '- "personaHint": brief description of the user who would search this\n\n'
            "Return ONLY the JSON array, no other text."
        )

        result = await self.complete_json(system_prompt, user_prompt)
        if isinstance(result, list):
            return result
        return []

    async def generate_personas(
        self,
        domain: str,
        sample_docs: List[Dict[str, Any]],
        text_fields: List[str],
        count: int = 12,
    ) -> List[Dict[str, Any]]:
        """Generate search personas tailored to the connected index."""
        if not self.available:
            return []

        doc_summaries: List[str] = []
        for i, doc in enumerate(sample_docs[:10]):
            parts = []
            for field in text_fields[:3]:
                value = doc.get(field, "")
                if isinstance(value, str) and value:
                    parts.append(f"{field}: {value[:160]}")
            if parts:
                doc_summaries.append(f"Doc {doc.get('_id', i)} | " + " | ".join(parts))

        if not doc_summaries:
            return []

        system_prompt = (
            "You create realistic search personas for a search relevance optimization system. "
            "Return personas that reflect the actual dataset and likely user intents, not generic security roles."
        )
        user_prompt = (
            f"Detected domain: {domain}\n\n"
            "Here are representative documents from the index:\n"
            + "\n".join(doc_summaries)
            + "\n\n"
            f"Generate {count} personas as a JSON array. Each item must contain:\n"
            '- "name"\n'
            '- "role"\n'
            '- "department"\n'
            '- "archetype" (Casual, Power User, or Expert)\n'
            '- "goal"\n'
            '- "queries" (3 realistic search queries this persona would run)\n\n'
            "Return JSON only."
        )

        result = await self.complete_json(system_prompt, user_prompt)
        return result if isinstance(result, list) else []

    async def suggest_experiment(
        self,
        current_profile: Dict[str, Any],
        experiment_history: List[Dict[str, Any]],
        domain: str,
        current_score: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Ask the LLM to suggest the next experiment to run.
        Returns a dict with: path, before, after, label, hypothesis
        """
        if not self.available:
            return None

        history_summary = []
        for exp in experiment_history[-5:]:
            history_summary.append(
                f"  - {exp.get('change', {}).get('label', 'unknown')}: "
                f"delta={exp.get('deltaPercent', 0):.1f}% -> {exp.get('decision', '?')}"
            )

        system_prompt = (
            f"You are an Elasticsearch search quality expert optimizing a {domain} search index. "
            "Suggest the single most promising experiment to run next to improve nDCG@10."
        )

        user_prompt = (
            f"Current profile: {json.dumps(current_profile, indent=2)}\n\n"
            f"Current nDCG@10 score: {current_score:.4f}\n\n"
            f"Recent experiments:\n" + "\n".join(history_summary) + "\n\n"
            "Suggest ONE change to try. Return JSON with keys:\n"
            '- "path": dot-notation field path in the profile (e.g., "tieBreaker")\n'
            '- "before": current value\n'
            '- "after": proposed value\n'
            '- "label": short human-readable label\n'
            '- "hypothesis": one sentence explaining why this should help\n\n'
            "Return ONLY the JSON object."
        )

        return await self.complete_json(system_prompt, user_prompt)

    async def generate_committee_personas(
        self, committee_description: str
    ) -> List[Dict[str, Any]]:
        system_prompt = (
            "You design realistic enterprise buying committees. "
            "Return grounded stakeholder personas with authority weights that sum close to 1.0."
        )
        user_prompt = (
            "Create 4-6 committee personas from this description.\n\n"
            f"{committee_description}\n\n"
            "Return JSON only as an array. Each item must contain: "
            "id, name, title, organization, roleInDecision, authorityWeight, priorities, concerns, "
            "decisionCriteria, likelyObjections, whatWinsThemOver, skepticismLevel, domainExpertise, politicalMotivations."
        )
        result = await self.complete_json(system_prompt, user_prompt)
        return result if isinstance(result, list) else []

    async def evaluate_committee_section(
        self,
        persona: CommitteePersona,
        section: DocumentSection,
    ) -> Optional[Dict[str, Any]]:
        system_prompt = (
            f"You are {persona.name}, {persona.title} at {persona.organization}.\n\n"
            f"Role in decision: {persona.roleInDecision}\n"
            f"Authority weight: {persona.authorityWeight}\n"
            f"Your priorities:\n- " + "\n- ".join(persona.priorities) + "\n\n"
            "Your concerns:\n- " + "\n- ".join(persona.concerns) + "\n\n"
            "Your decision criteria:\n- "
            + "\n- ".join(persona.decisionCriteria)
            + "\n\n"
            "Likely objections:\n- " + "\n- ".join(persona.likelyObjections) + "\n\n"
            "What wins you over:\n- " + "\n- ".join(persona.whatWinsThemOver) + "\n\n"
            f"Skepticism level: {persona.skepticismLevel}/10\n\n"
            "Evaluate honestly. Do not be artificially positive. Return JSON only."
        )
        user_prompt = (
            f"Evaluate this document section.\n\n"
            f"Title: {section.title}\n"
            f"Type: {section.type}\n"
            f"Content:\n---\n{section.content}\n---\n\n"
            "Return this JSON shape only:\n"
            "{\n"
            '  "relevance": 0.0,\n'
            '  "persuasiveness": 0.0,\n'
            '  "evidence_quality": 0.0,\n'
            '  "risk_flags": ["..."],\n'
            '  "missing": ["..."],\n'
            '  "emotional_response": "supportive | cautiously interested | neutral | skeptical | opposed",\n'
            '  "reaction_quote": "...",\n'
            '  "composite_score": 0.0\n'
            "}"
        )
        result = await self.complete_json(system_prompt, user_prompt)
        return result if isinstance(result, dict) else None

    async def rewrite_committee_section(
        self,
        section: DocumentSection,
        parameter_name: str,
        old_value: str,
        new_value: str,
        industry_label: str = "General Enterprise",
        parameter_options: Optional[Dict[str, List[str]]] = None,
    ) -> Optional[str]:
        parameter_lines = [
            "- stat_framing: conservative adds caveats; moderate is balanced; aggressive leads with the biggest number",
            "- proof_point_density: low = 1 proof point; medium = 2; high = 3+",
            "- cta_urgency: soft, firm, direct",
            "- objection_preemption: none, light, heavy",
            "- technical_depth: executive, practitioner, mixed",
            "- risk_narrative: opportunity, threat, balanced",
        ]
        if parameter_options:
            social_values = ", ".join(parameter_options.get("social_proof_type", []))
            specificity_values = ", ".join(parameter_options.get("specificity", []))
            if social_values:
                parameter_lines.append(f"- social_proof_type: {social_values}")
            if specificity_values:
                parameter_lines.append(f"- specificity: {specificity_values}")
        system_prompt = (
            f"You are a professional document editor optimizing a vendor pitch for a {industry_label} buying committee. "
            "Maintain the core argument and factual substance while changing framing, tone, specificity, or proof density."
        )
        user_prompt = (
            f"Current section title: {section.title}\n"
            f"Current section content:\n---\n{section.content}\n---\n\n"
            f"Optimization instruction: change {parameter_name} from {old_value} to {new_value}.\n\n"
            "Parameter definitions:\n" + "\n".join(parameter_lines) + "\n\n"
            "Return only the rewritten section text."
        )
        text = await self.complete(system_prompt, user_prompt)
        if text:
            return text.strip().strip("`")
        return None
