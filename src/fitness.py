from math import comb
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
    33907039, #piri reis map ID
    38120068,  # Trade-In
    48800175,  # Melody of Awakening Dragon
    39701395,  # Cards of Consonance (example)
    
}


MAIDEN_ID = 17947697       # Maiden of white 
WISHES_ID = 80326401        # Wishes for Eyes of Blue 
True_Light_ID = 62089826  # True Light ID

# Deck-building rule weights, thresholds, and points
MIN_MONSTERS = 25      # minimum # monsters
MAX_MONSTERS = 30  # maximum # monsters
REQ_BE_MONSTERS = 8    # minimum # Blue-Eyes monsters
MAX_DECK_SIZE = 40     # deck must not exceed 40 cards
HAND_THRESHOLD = 0.70  # >=70% chance playable (single)
JOINT_THRESHOLD = 0.0  # any chance to draw both IDs

# Points assigned to each rule
PTS_MONSTERS = 2
PTS_BE_MONSTERS = 3
PTS_DECK_SIZE = 1
PTS_HAND_PLAYABLE = 7
PTS_JOINT_BONUS = 10

# Number of Monte Carlo trials for hand probability
N_HAND_TRIALS = 200

# --- SEARCH-ENGINE CONSISTENCY (e.g. Trade-In, Melody, Cards of Consonance) ---
SEARCH_IDS: Set[int] = {
    38120068,  # Trade-In
    48800175,  # Melody of Awakening Dragon
    39701395,  # Cards of Consonance (example)
}
SEARCH_WEIGHT = 5
SEARCH_THRESHOLD = 0.60  # award points if P ≥ 60%

def compute_search_rate(deck: Dict[int,int]) -> float:
    """
    Exact hypergeometric: P(draw ≥1 search card in opening 5).
    """
    total = MAX_DECK_SIZE
    k = sum(deck.get(cid,0) for cid in SEARCH_IDS)
    if k == 0:
        return 0.0
    # hypergeometric C(total-k,5)/C(total,5)
    return 1 - comb(total - k, 5) / comb(total, 5)


# --- SPELL/TRAP BACKROW BALANCE BONUS ---
MIN_BACKROW = 10
MAX_BACKROW = 15
BACKROW_BONUS = 1

def compute_backrow_bonus(deck: Dict[int,int]) -> int:
    """
    Reward a balanced number of Spell/Trap cards.
    """
    backrow = sum(
        cnt for cid,cnt in deck.items()
        if card_db_global[cid]['type'] in ('Spell Card', 'Trap Card')
    )
    return BACKROW_BONUS if MIN_BACKROW <= backrow <= MAX_BACKROW else 0


# --- SYNERGY PAIR / TRIO BONUSES ---
SYNERGY_COMBOS = [
    ({89631139, 30576089}, 3),   # BEWD + Sage with Eyes
    ({89631139, 48800175}, 4),   # BEWD + Melody
    ({30576089, 71039903}, 2),   # Sage + Stone
    # add more as needed…
]

def compute_synergy_bonus(deck: Dict[int,int]) -> int:
    """
    For each defined combo (set of IDs), award points if all are present.
    """
    bonus = 0
    deck_ids = set(deck.keys())
    for combo_ids, pts in SYNERGY_COMBOS:
        if combo_ids.issubset(deck_ids):
            bonus += pts
    return bonus


# --- TWO-CARD COMBO PROBABILITY BONUS (exact) ---
COMBO_A = 48800175  # Melody of Awakening Dragon
COMBO_B = 89631139  # Blue-Eyes White Dragon
COMBO_WEIGHT = 4

def compute_combo_probability(deck: Dict[int,int]) -> float:
    """
    Exact hypergeometric: P(both A and B in opening 5).
    """
    total = MAX_DECK_SIZE
    a_count = deck.get(COMBO_A, 0)
    b_count = deck.get(COMBO_B, 0)
    # sum over exactly one of each in the hand:
    # [C(a_count,1)*C(b_count,1)*C(total-2,3)] / C(total,5)
    if a_count == 0 or b_count == 0:
        return 0.0
    num = comb(a_count,1) * comb(b_count,1) * comb(total-2, 3)
    den = comb(total, 5)
    return num / den

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

    # 1) Monster count rule
    monster_count = sum(
        cnt for cid, cnt in deck.items()
        if card_db_global[cid]['type'] == 'Monster'
    )
    if monster_count >= MIN_MONSTERS:
        score += PTS_MONSTERS

    # 2) Blue-Eyes monster count rule
    be_count = sum(deck.get(cid, 0) for cid in BLUE_EYES_IDS)
    if be_count >= REQ_BE_MONSTERS:
        score += PTS_BE_MONSTERS

    # 3) Deck size rule
    total = sum(deck.values())
    if total <= MAX_DECK_SIZE:
        score += PTS_DECK_SIZE

    # 4) Playable hand rate rule
    p_rate = estimate_playable_hand_rate(deck)
    if p_rate >= HAND_THRESHOLD:
        score += PTS_HAND_PLAYABLE

    # 5) Joint playable hand rate rule
    joint_rate = estimate_joint_playable_hand_rate(deck)
    if joint_rate > JOINT_THRESHOLD:
        score += PTS_JOINT_BONUS

    # 6) Search card rate rule
    search_rate = compute_search_rate(deck)
    if search_rate >= SEARCH_THRESHOLD:
        score += SEARCH_WEIGHT

    # 7) Spell/Trap backrow balance bonus
    score += compute_backrow_bonus(deck)

    # 8) Synergy combos bonus
    score += compute_synergy_bonus(deck)

    # 9) Two-card combo probability bonus
    score += COMBO_WEIGHT * compute_combo_probability(deck)

    # --- Custom point allocations ---
    # 2 pts if Trade-In (38120068) is in the deck
    if deck.get(38120068, 0) > 0:
        score += 2
    # 5 pts if True Light (62089826) is in the deck
    if deck.get(62089826, 0) > 0:
        score += 5
    # 1 pt for each Blue-Eyes White Dragon (89631139)
    score += deck.get(89631139, 0) * 1
    # 1 pt for each Wishes for Eyes of Blue (80326401)
    score += deck.get(80326401, 0) * 1
    # 1 pt for each Maiden of White (17947697)
    score += deck.get(17947697, 0) * 1

    return score


def fitness(deck: Dict[int, int]) -> float:
    """
    Overall fitness = sum of rule-based scores; invalid decks get -inf.
    """
    if not is_deck_valid(deck):
        return float('-inf')
    return compute_deck_score(deck)
