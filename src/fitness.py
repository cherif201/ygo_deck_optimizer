import random
from typing import Dict, Set

from src.database import is_card_count_valid, load_card_db


card_db_global = load_card_db()


BLUE_EYES_IDS: Set[int] = {
    
}


PLAYABLE_HAND_IDS: Set[int] = {
    80326401  ,# Wishes for Eyes of Blue ID
    8240199, # Sage with Eyes of Blue ID
    93437091 ,# Bingo Machine, Go!!! ID
    17725109, # Roar of the Blue-Eyes Dragon ID
    17947697 , # Maiden of white ID
    63198739, # Ether Beryl ID
    29095457, # Drillbeam ID
    56506740, # Lordly Lode ID
    48800175,# Melody of Awakening Dragon ID
    33907039 #piri reis map ID
}


MAIDEN_ID = 17947697       # Maiden of white (example)
WISHES_ID = 80326401        # Wishes for Eyes of Blue (example)

# Deck-building rule weights, thresholds, and points
MIN_MONSTERS = 15      # minimum # monsters
REQ_BE_MONSTERS = 8    # minimum # Blue-Eyes monsters
MAX_DECK_SIZE = 40     # deck must not exceed 40 cards
HAND_THRESHOLD = 0.70  # >=70% chance playable (single)
JOINT_THRESHOLD = 0  # any chance to draw both IDs

# Points assigned to each rule
PTS_MONSTERS = 2
PTS_BE_MONSTERS = 3
PTS_DECK_SIZE = 1
PTS_HAND_PLAYABLE = 7
PTS_JOINT_BONUS = 10

# Number of Monte Carlo trials for hand probability
N_HAND_TRIALS = 200


def is_deck_valid(deck: Dict[int, int]) -> bool:
    """
    Quick banlist and size check.
    """
    total = sum(deck.values())
    if total > MAX_DECK_SIZE:
        return False
    for cid, cnt in deck.items():
        if not is_card_count_valid(cid, cnt, card_db_global):
            return False
    return True


def estimate_playable_hand_rate(deck: Dict[int, int], n_trials: int = N_HAND_TRIALS) -> float:
    """
    Monte Carlo: fraction of 5-card hands containing
    at least one ID from PLAYABLE_HAND_IDS.
    """
    pool = []
    for cid, cnt in deck.items():
        pool.extend([cid] * cnt)

    success = 0
    for _ in range(n_trials):
        hand = random.sample(pool, 5)
        if any(c in PLAYABLE_HAND_IDS for c in hand):
            success += 1
    return success / n_trials


def estimate_joint_playable_hand_rate(deck: Dict[int, int], n_trials: int = N_HAND_TRIALS) -> float:
    """
    Monte Carlo: fraction of 5-card hands containing
    both MAIDEN_ID and WISHES_ID.
    """
    pool = []
    for cid, cnt in deck.items():
        pool.extend([cid] * cnt)

    success = 0
    for _ in range(n_trials):
        hand = random.sample(pool, 5)
        if MAIDEN_ID in hand and WISHES_ID in hand:
            success += 1
    return success / n_trials


def compute_deck_score(deck: Dict[int, int]) -> float:
    """
    Evaluate deck against build rules; returns total rule-based score.
    """
    score = 0.0

    
    monster_count = sum(
        cnt for cid, cnt in deck.items()
        if card_db_global[cid]['type'] == 'Monster'
    )
    if monster_count >= MIN_MONSTERS:
        score += PTS_MONSTERS

    
    be_count = sum(deck.get(cid, 0) for cid in BLUE_EYES_IDS)
    if be_count >= REQ_BE_MONSTERS:
        score += PTS_BE_MONSTERS

    total = sum(deck.values())
    if total <= MAX_DECK_SIZE:
        score += PTS_DECK_SIZE

    p_rate = estimate_playable_hand_rate(deck)
    if p_rate >= HAND_THRESHOLD:
        score += PTS_HAND_PLAYABLE

    joint_rate = estimate_joint_playable_hand_rate(deck)
    if joint_rate > JOINT_THRESHOLD:
        score += PTS_JOINT_BONUS

    return score


def fitness(deck: Dict[int, int]) -> float:
    """
    Overall fitness = sum of rule-based scores; invalid decks get -inf.
    """
    if not is_deck_valid(deck):
        return float('-inf')
    return compute_deck_score(deck)
