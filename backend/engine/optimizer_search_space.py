from typing import List, Dict, Optional, Tuple
import random
from ..models.contracts import SearchProfile, SearchProfileChange

BOOST_VALUES = [0.1, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
MULTI_MATCH_TYPES = ["best_fields", "most_fields", "cross_fields", "phrase"]
MIN_SHOULD_MATCH_VALUES = ["100%", "75%", "2<75%", "3<80%", "50%", "1", "2", "30%"]
TIE_BREAKER_VALUES = [0.0, 0.1, 0.2, 0.3, 0.5]
PHRASE_BOOST_VALUES = [0.0, 0.5, 1.0, 1.5, 2.0]
FUZZINESS_VALUES = ["0", "AUTO"]
LEXVEC_PAIRS = [(0.85, 0.15), (0.75, 0.25), (0.65, 0.35), (0.55, 0.45), (0.45, 0.55)]
FUSION_METHODS = ["weighted_sum", "rrf"]
RRF_RANK_CONSTANTS = [10, 20, 40, 60]
KNN_K_VALUES = [10, 20, 30, 50]
NUM_CANDIDATES_VALUES = [50, 100, 150, 250, 400]
SECURITY_FIELD_TOKENS = ("severity", "mitre", "source", "rule", "category", "tactic")
SECURITY_PRIORITY_BOOSTS = [2.0, 3.0, 4.0, 5.0]


def generate_mutations(
    profile: SearchProfile, experiment_history: List[Dict], recently_reverted: List[str]
) -> List[Tuple[SearchProfile, SearchProfileChange]]:
    """Generate all valid one-step mutations from current profile."""
    mutations = []

    # Field boost mutations
    for i, field_entry in enumerate(profile.lexicalFields):
        current_boost = field_entry.boost
        for new_boost in BOOST_VALUES:
            if new_boost != current_boost:
                new_profile = profile.model_copy(deep=True)
                new_profile.lexicalFields[i] = field_entry.model_copy(
                    update={"boost": new_boost}
                )
                change = SearchProfileChange(
                    path=f"lexicalFields[{i}].boost",
                    before=current_boost,
                    after=new_boost,
                    label=f"{field_entry.field} boost {current_boost} → {new_boost}",
                )
                mutations.append((new_profile, change))

    # multiMatchType
    for val in MULTI_MATCH_TYPES:
        if val != profile.multiMatchType:
            new_profile = profile.model_copy(deep=True)
            new_profile.multiMatchType = val
            change = SearchProfileChange(
                path="multiMatchType",
                before=profile.multiMatchType,
                after=val,
                label=f"multiMatchType {profile.multiMatchType} → {val}",
            )
            mutations.append((new_profile, change))

    # minimumShouldMatch
    for val in MIN_SHOULD_MATCH_VALUES:
        if val != profile.minimumShouldMatch:
            new_profile = profile.model_copy(deep=True)
            new_profile.minimumShouldMatch = val
            change = SearchProfileChange(
                path="minimumShouldMatch",
                before=profile.minimumShouldMatch,
                after=val,
                label=f"minimumShouldMatch {profile.minimumShouldMatch} → {val}",
            )
            mutations.append((new_profile, change))

    # tieBreaker
    for val in TIE_BREAKER_VALUES:
        if val != profile.tieBreaker:
            new_profile = profile.model_copy(deep=True)
            new_profile.tieBreaker = val
            change = SearchProfileChange(
                path="tieBreaker",
                before=profile.tieBreaker,
                after=val,
                label=f"tieBreaker {profile.tieBreaker} → {val}",
            )
            mutations.append((new_profile, change))

    # phraseBoost
    for val in PHRASE_BOOST_VALUES:
        if val != profile.phraseBoost:
            new_profile = profile.model_copy(deep=True)
            new_profile.phraseBoost = val
            change = SearchProfileChange(
                path="phraseBoost",
                before=profile.phraseBoost,
                after=val,
                label=f"phraseBoost {profile.phraseBoost} → {val}",
            )
            mutations.append((new_profile, change))

    # fuzziness
    for val in FUZZINESS_VALUES:
        if val != profile.fuzziness:
            new_profile = profile.model_copy(deep=True)
            new_profile.fuzziness = val
            change = SearchProfileChange(
                path="fuzziness",
                before=profile.fuzziness,
                after=val,
                label=f"fuzziness {profile.fuzziness} → {val}",
            )
            mutations.append((new_profile, change))

    # Vector weights (only if vector enabled)
    if profile.useVector:
        for lex_w, vec_w in LEXVEC_PAIRS:
            if abs(lex_w - profile.lexicalWeight) > 0.01:
                new_profile = profile.model_copy(deep=True)
                new_profile.lexicalWeight = lex_w
                new_profile.vectorWeight = vec_w
                change = SearchProfileChange(
                    path="lexicalWeight",
                    before=profile.lexicalWeight,
                    after=lex_w,
                    label=f"lexical/vector weight {profile.lexicalWeight:.2f}/{profile.vectorWeight:.2f} → {lex_w:.2f}/{vec_w:.2f}",
                )
                mutations.append((new_profile, change))

        for val in FUSION_METHODS:
            if val != profile.fusionMethod:
                new_profile = profile.model_copy(deep=True)
                new_profile.fusionMethod = val
                change = SearchProfileChange(
                    path="fusionMethod",
                    before=profile.fusionMethod,
                    after=val,
                    label=f"fusionMethod {profile.fusionMethod} → {val}",
                )
                mutations.append((new_profile, change))

        for val in RRF_RANK_CONSTANTS:
            if val != profile.rrfRankConstant:
                new_profile = profile.model_copy(deep=True)
                new_profile.rrfRankConstant = val
                change = SearchProfileChange(
                    path="rrfRankConstant",
                    before=profile.rrfRankConstant,
                    after=val,
                    label=f"rrfRankConstant {profile.rrfRankConstant} → {val}",
                )
                mutations.append((new_profile, change))

        for val in KNN_K_VALUES:
            if val != profile.knnK:
                new_profile = profile.model_copy(deep=True)
                new_profile.knnK = val
                change = SearchProfileChange(
                    path="knnK",
                    before=profile.knnK,
                    after=val,
                    label=f"knnK {profile.knnK} → {val}",
                )
                mutations.append((new_profile, change))

        for val in NUM_CANDIDATES_VALUES:
            if val != profile.numCandidates:
                new_profile = profile.model_copy(deep=True)
                new_profile.numCandidates = val
                change = SearchProfileChange(
                    path="numCandidates",
                    before=profile.numCandidates,
                    after=val,
                    label=f"numCandidates {profile.numCandidates} → {val}",
                )
                mutations.append((new_profile, change))

    # Filter out recently reverted paths
    mutations = [(p, c) for p, c in mutations if c.path not in recently_reverted]

    # Filter out invalid combinations (cross_fields doesn't support fuzziness in ES)
    valid_mutations = []
    for p, c in mutations:
        if p.multiMatchType == "cross_fields" and p.fuzziness != "0":
            continue  # ES rejects this combo
        valid_mutations.append((p, c))

    return valid_mutations


def pick_mutation(
    mutations: List[Tuple], rng: Optional[random.Random] = None
) -> Optional[Tuple]:
    """Pick a random mutation from the list."""
    if not mutations:
        return None
    r = rng or random
    return r.choice(mutations)


def generate_security_field_mutations(
    profile: SearchProfile,
) -> List[SearchProfileChange]:
    """Prioritize boosts for security-relevant fields when they are present."""
    changes: List[SearchProfileChange] = []
    for index, field_entry in enumerate(profile.lexicalFields):
        field_name = str(field_entry.field).lower()
        if not any(token in field_name for token in SECURITY_FIELD_TOKENS):
            continue
        current_boost = field_entry.boost
        for new_boost in SECURITY_PRIORITY_BOOSTS:
            if new_boost == current_boost:
                continue
            changes.append(
                SearchProfileChange(
                    path=f"lexicalFields[{index}].boost",
                    before=current_boost,
                    after=new_boost,
                    label=f"{field_entry.field or f'field_{index}'} boost {current_boost} → {new_boost}",
                )
            )
    return changes


def build_hypothesis_text(change: SearchProfileChange) -> str:
    path = change.path
    before = change.before
    after = change.after

    if path.startswith("lexicalFields[") and "boost" in path:
        field_name = change.label.split(" boost", 1)[0]
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            if after > before:
                return f"Increase {field_name} influence so stronger {field_name} matches rise earlier in the ranking."
            return f"Reduce {field_name} influence to let other fields carry more of the ranking signal."

    if path == "multiMatchType":
        descriptions = {
            "cross_fields": "Treat terms as shared across fields so fragmented matches can still rank well.",
            "most_fields": "Reward documents that match across many fields rather than one dominant field.",
            "phrase": "Favor ordered phrase matches when exact wording should matter most.",
            "best_fields": "Bias toward the single strongest field match to sharpen precision.",
        }
        return descriptions.get(
            str(after),
            f"Change the multi-match strategy to {after} and measure the ranking tradeoff.",
        )

    if path == "minimumShouldMatch":
        try:
            before_pct = int(str(before).replace("%", ""))
            after_pct = int(str(after).replace("%", ""))
            if after_pct > before_pct:
                return "Tighten term matching so weaker partial matches fall away and exact intent carries more weight."
            return "Relax term matching so the engine can recover relevant documents that only match part of the query."
        except Exception:
            return (
                "Adjust term-matching strictness to rebalance recall versus precision."
            )

    if path == "phraseBoost":
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            if after > before:
                return "Reward exact phrase matches more strongly when users search with high-intent wording."
            return "Reduce phrase strictness so near-matches are less likely to be over-penalized."

    if path == "fuzziness":
        if str(after) == "AUTO":
            return "Allow tolerant matching so typos, variants, and inflections still surface relevant results."
        return "Turn off fuzzy matching to sharpen exact lexical precision and reduce noisy recall."

    if path == "tieBreaker":
        return "Rebalance how much supporting field matches contribute once one field already matches strongly."

    if path == "vectorWeight":
        if (
            isinstance(before, (int, float))
            and isinstance(after, (int, float))
            and after > before
        ):
            return "Lean harder on semantic similarity to catch concept matches beyond exact wording."
        return "Pull ranking back toward lexical evidence so exact field matches dominate over semantic recall."

    if path == "fusionMethod":
        if str(after) == "rrf":
            return "Switch to reciprocal-rank fusion to blend lexical and vector rankings more conservatively."
        return "Use weighted-score fusion to let relative relevance scores drive the blend directly."

    if path == "rrfRankConstant":
        return "Adjust how aggressively reciprocal-rank fusion rewards higher-ranked documents from each retriever."

    if path == "knnK":
        return "Widen the semantic candidate set to see whether more vector neighbors improve final recall."

    return f"Test whether changing {path} from {before} to {after} improves ranked relevance without hurting the broader query set."
