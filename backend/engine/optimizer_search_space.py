from typing import List, Dict, Any, Optional, Tuple
import copy
import random
from ..models.contracts import SearchProfile, SearchProfileChange

BOOST_VALUES = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
MULTI_MATCH_TYPES = ["best_fields", "most_fields", "cross_fields", "phrase"]
MIN_SHOULD_MATCH_VALUES = ["100%", "75%", "2<75%", "3<80%", "50%"]
TIE_BREAKER_VALUES = [0.0, 0.1, 0.2, 0.3, 0.5]
PHRASE_BOOST_VALUES = [0.0, 0.5, 1.0, 1.5, 2.0]
FUZZINESS_VALUES = ["0", "AUTO"]
LEXVEC_PAIRS = [(0.85, 0.15), (0.75, 0.25), (0.65, 0.35), (0.55, 0.45), (0.45, 0.55)]
FUSION_METHODS = ["weighted_sum", "rrf"]
RRF_RANK_CONSTANTS = [10, 20, 40, 60]
KNN_K_VALUES = [10, 20, 30, 50]
NUM_CANDIDATES_VALUES = [50, 100, 150, 250, 400]


def generate_mutations(profile: SearchProfile, experiment_history: List[Dict],
                       recently_reverted: List[str]) -> List[Tuple[SearchProfile, SearchProfileChange]]:
    """Generate all valid one-step mutations from current profile."""
    mutations = []

    # Field boost mutations
    for i, field_entry in enumerate(profile.lexicalFields):
        current_boost = field_entry['boost']
        for new_boost in BOOST_VALUES:
            if new_boost != current_boost:
                new_profile = profile.model_copy(deep=True)
                new_profile.lexicalFields[i] = dict(field_entry)
                new_profile.lexicalFields[i]['boost'] = new_boost
                change = SearchProfileChange(
                    path=f"lexicalFields[{i}].boost",
                    before=current_boost,
                    after=new_boost,
                    label=f"{field_entry['field']} boost {current_boost} → {new_boost}"
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
                label=f"multiMatchType {profile.multiMatchType} → {val}"
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
                label=f"minimumShouldMatch {profile.minimumShouldMatch} → {val}"
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
                label=f"tieBreaker {profile.tieBreaker} → {val}"
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
                label=f"phraseBoost {profile.phraseBoost} → {val}"
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
                label=f"fuzziness {profile.fuzziness} → {val}"
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
                    label=f"lexical/vector weight {profile.lexicalWeight:.2f}/{profile.vectorWeight:.2f} → {lex_w:.2f}/{vec_w:.2f}"
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
                    label=f"fusionMethod {profile.fusionMethod} → {val}"
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
                    label=f"rrfRankConstant {profile.rrfRankConstant} → {val}"
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
                    label=f"knnK {profile.knnK} → {val}"
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
                    label=f"numCandidates {profile.numCandidates} → {val}"
                )
                mutations.append((new_profile, change))

    # Filter out recently reverted paths
    mutations = [(p, c) for p, c in mutations if c.path not in recently_reverted]

    return mutations


def pick_mutation(mutations: List[Tuple], rng: Optional[random.Random] = None) -> Optional[Tuple]:
    """Pick a random mutation from the list."""
    if not mutations:
        return None
    r = rng or random
    return r.choice(mutations)
