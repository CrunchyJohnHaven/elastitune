from typing import Dict, Any, List, Tuple, Optional


def detect_text_fields(mapping: Dict[str, Any]) -> List[str]:
    """Extract all text-type fields from an ES mapping."""
    fields = []

    def _walk(props: Dict, prefix: str = ""):
        for name, conf in props.items():
            full = f"{prefix}{name}" if not prefix else f"{prefix}.{name}"
            field_type = conf.get("type", "")
            if field_type in ("text",):
                fields.append(full)
            elif field_type == "object" or ("properties" in conf):
                _walk(conf.get("properties", {}), full + ".")

    # Handle ES mapping structure
    if "mappings" in mapping:
        mapping = mapping["mappings"]
    props = mapping.get("properties", {})
    _walk(props)
    return fields


def detect_vector_field(mapping: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """Return (field_name, dims) for the first dense_vector field found."""

    def _walk(props: Dict, prefix: str = "") -> Tuple[Optional[str], Optional[int]]:
        for name, conf in props.items():
            full = f"{prefix}{name}" if not prefix else f"{prefix}.{name}"
            field_type = conf.get("type", "")
            if field_type == "dense_vector":
                dims = conf.get("dims")
                return full, dims
            if field_type == "object" or ("properties" in conf):
                result = _walk(conf.get("properties", {}), full + ".")
                if result[0] is not None:
                    return result
        return None, None

    if "mappings" in mapping:
        mapping = mapping["mappings"]
    props = mapping.get("properties", {})
    return _walk(props)


def detect_domain(field_names: List[str], sample_text: str) -> str:
    """Detect domain: security, developer_docs, compliance, or general."""
    text = (sample_text + " ".join(field_names)).lower()

    security_terms = ["alert", "rule", "host", "ip", "user", "process", "malware",
                      "incident", "authentication", "firewall", "threat", "attack",
                      "soc", "cve", "vulnerability", "detection"]
    dev_terms = ["api", "sdk", "endpoint", "request", "response", "error",
                 "deployment", "container", "code", "library", "function", "method"]
    compliance_terms = ["policy", "control", "regulation", "audit", "evidence",
                        "exception", "risk", "privacy", "retention", "compliance"]

    def score(terms):
        return sum(1 for t in terms if t in text)

    scores = {
        "security": score(security_terms),
        "developer_docs": score(dev_terms),
        "compliance": score(compliance_terms),
    }

    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best
    return "general"


def build_baseline_profile(text_fields: List[str], vector_field: Optional[str] = None,
                            vector_dims: Optional[int] = None) -> Dict:
    """Build default search profile for detected fields."""
    # Priority field name matching
    priority = {
        "title": 3.0, "name": 3.0, "headline": 3.0, "subject": 3.0,
        "summary": 2.0, "abstract": 2.0,
        "description": 1.5, "message": 1.5, "excerpt": 1.5,
        "body": 1.0, "content": 1.0, "text": 1.0,
    }

    lexical_fields = []
    for f in text_fields[:8]:  # cap at 8 fields
        basename = f.split(".")[-1].lower()
        boost = priority.get(basename, 1.0)
        lexical_fields.append({"field": f, "boost": boost})

    return {
        "lexicalFields": lexical_fields,
        "multiMatchType": "best_fields",
        "minimumShouldMatch": "75%",
        "tieBreaker": 0.0,
        "phraseBoost": 0.0,
        "fuzziness": "0",
        "useVector": bool(vector_field),
        "vectorField": vector_field,
        "vectorWeight": 0.35 if vector_field else 0.0,
        "lexicalWeight": 0.65 if vector_field else 1.0,
        "fusionMethod": "weighted_sum",
        "rrfRankConstant": 60,
        "knnK": 20,
        "numCandidates": 100,
    }
