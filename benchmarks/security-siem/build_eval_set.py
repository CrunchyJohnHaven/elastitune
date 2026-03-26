#!/usr/bin/env python3
"""Build eval set using actual Elasticsearch search results for ground truth."""

import json
import requests

ES_URL = "http://localhost:9200"
INDEX = "security-siem"

EVAL_QUERIES = [
    {"id": "siem_eval_001", "query": "ransomware lateral movement encryption", "difficulty": "medium", "personaHint": "SOC analyst investigating ransomware spread"},
    {"id": "siem_eval_002", "query": "phishing credential harvest office365", "difficulty": "medium", "personaHint": "email security analyst"},
    {"id": "siem_eval_003", "query": "powershell encoded command execution fileless", "difficulty": "easy", "personaHint": "endpoint security engineer"},
    {"id": "siem_eval_004", "query": "DNS tunneling data exfiltration covert channel", "difficulty": "medium", "personaHint": "network security analyst"},
    {"id": "siem_eval_005", "query": "brute force authentication failure active directory", "difficulty": "easy", "personaHint": "identity security analyst"},
    {"id": "siem_eval_006", "query": "privilege escalation kernel exploit linux", "difficulty": "medium", "personaHint": "Linux security engineer"},
    {"id": "siem_eval_007", "query": "supply chain compromise software update trojanized", "difficulty": "hard", "personaHint": "threat intelligence analyst"},
    {"id": "siem_eval_008", "query": "cloud IAM policy modification unauthorized access", "difficulty": "medium", "personaHint": "cloud security engineer"},
    {"id": "siem_eval_009", "query": "cobalt strike beacon command and control C2", "difficulty": "easy", "personaHint": "threat hunter"},
    {"id": "siem_eval_010", "query": "LSASS credential dumping mimikatz pass-the-hash", "difficulty": "easy", "personaHint": "incident responder"},
    {"id": "siem_eval_011", "query": "webshell web server backdoor remote code execution", "difficulty": "medium", "personaHint": "web security analyst"},
    {"id": "siem_eval_012", "query": "VPN zero-day exploit remote code execution", "difficulty": "hard", "personaHint": "vulnerability management analyst"},
    {"id": "siem_eval_013", "query": "insider threat data theft departing employee DLP", "difficulty": "medium", "personaHint": "insider threat analyst"},
    {"id": "siem_eval_014", "query": "kubernetes container escape privilege escalation RBAC", "difficulty": "hard", "personaHint": "cloud native security engineer"},
    {"id": "siem_eval_015", "query": "APT nation state espionage campaign government", "difficulty": "hard", "personaHint": "senior threat intelligence analyst"},
    {"id": "siem_eval_016", "query": "business email compromise wire transfer fraud BEC", "difficulty": "medium", "personaHint": "fraud analyst"},
    {"id": "siem_eval_017", "query": "Log4Shell log4j remote code execution JNDI", "difficulty": "easy", "personaHint": "application security engineer"},
    {"id": "siem_eval_018", "query": "kerberoasting service ticket active directory attack", "difficulty": "medium", "personaHint": "active directory security specialist"},
    {"id": "siem_eval_019", "query": "DLL sideloading defense evasion signed binary proxy", "difficulty": "hard", "personaHint": "malware analyst"},
    {"id": "siem_eval_020", "query": "S3 bucket data exposure cloud misconfiguration AWS", "difficulty": "medium", "personaHint": "cloud security posture management analyst"},
]

eval_set = []
for eq in EVAL_QUERIES:
    resp = requests.get(f"{ES_URL}/{INDEX}/_search", json={
        "query": {
            "multi_match": {
                "query": eq["query"],
                "fields": ["title^3", "description^2", "tags^2", "mitre_technique"],
                "type": "best_fields",
                "minimum_should_match": "30%"
            }
        },
        "size": 50,
        "_source": ["title", "severity", "source"]
    })
    hits = resp.json()["hits"]["hits"]

    if not hits:
        relevant_ids = []
        top_score = 0
    else:
        max_score = hits[0]["_score"]
        top_score = max_score
        threshold = max_score * 0.40
        relevant_ids = [h["_id"] for h in hits if h["_score"] >= threshold]
        # Ensure minimum 2, maximum 10
        if len(relevant_ids) < 2:
            relevant_ids = [h["_id"] for h in hits[:3]]
        if len(relevant_ids) > 10:
            relevant_ids = relevant_ids[:10]

    eval_entry = {
        "id": eq["id"],
        "query": eq["query"],
        "relevantDocIds": relevant_ids,
        "difficulty": eq["difficulty"],
        "personaHint": eq["personaHint"],
    }
    eval_set.append(eval_entry)
    count = len(relevant_ids)
    print(f"  {eq['id']}: \"{eq['query']}\" -> {count} relevant docs (top score: {top_score:.1f})")

with open("/Users/johnbradley/Desktop/ElastiTune/benchmarks/security-siem/eval-set.json", "w") as f:
    json.dump(eval_set, f, indent=2)

print(f"\nWrote {len(eval_set)} eval queries to eval-set.json")
