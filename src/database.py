import json
import requests
import os
from typing import List, Dict, Any

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'blue_eyes_clean.json')

BANLIST_MAPPING = {
    "Forbidden": 0,
    "Limited": 1,
    "Semi-Limited": 2,
    "Unlimited": 3
}


def load_card_db(path: str = None) -> Dict[int, Dict[str, Any]]:
    """
    Load a JSON file of cards and return a dict mapping card_id to:
      - name: str
      - type: str
      - banlist_limit: int
    Defaults to blue_eyes_clean.json in data/ if path is None.
    """
    if path is None:
        path = DEFAULT_DB_PATH
    path = os.path.abspath(path)
    with open(path, 'r', encoding='utf-8') as f:
        cards = json.load(f)

    card_db: Dict[int, Dict[str, Any]] = {}
    for card in cards:
        cid = int(card.get('id'))
        status = card.get('banlist_status', 'Unlimited')
        limit = BANLIST_MAPPING.get(status, 3)
        card_db[cid] = {
            'name': card.get('name'),
            'type': card.get('type'),
            'banlist_limit': limit
        }
    return card_db


def is_card_count_valid(card_id: int, count: int, card_db: Dict[int, Dict[str, Any]]) -> bool:
    """
    Return True if count is between 1 and banlist_limit for card_id in card_db.
    """
    info = card_db.get(card_id)
    if not info:
        return False
    return 1 <= count <= info['banlist_limit']



# API endpoints
API_ALL_URL   = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
API_BE_SPELLS = "https://db.ygoprodeck.com/api/v7/cardinfo.php?type=spell%20card&archetype=Blue-Eyes"
API_BE_TRAPS  = "https://db.ygoprodeck.com/api/v7/cardinfo.php?type=trap%20card&archetype=Blue-Eyes"

# Types to exclude (Extra Deck and Pendulum cards)
EXTRA_DECK_TYPES = ["Fusion", "XYZ", "Synchro", "Link", "Pendulum"]
# Desired monster races
DESIRED_RACES     = ["Dragon", "Spellcaster"]
# Specific subtypes to exclude
EXCLUDE_SUBTYPES  = ["Equip Spell", "Ritual Spell", "Ritual Monster"]
# Explicit cards to always include
EXPLICIT_INCLUDES = ["Piri Reis Map", "Wishes for Eyes of Blue", "Roar Of The Blue-Eyed Dragons"]


def fetch_cards(url: str) -> List[Dict[str, Any]]:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data.get('data', [])


def filter_main_deck(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove Extra Deck / Pendulum cards."""
    return [c for c in cards
            if not any(extra in c.get('type', '') for extra in EXTRA_DECK_TYPES)]


def filter_monsters(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only monsters of desired races."""
    return [c for c in cards
            if 'Monster' in c.get('type', '') and c.get('race') in DESIRED_RACES]


def filter_spells_traps(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only Blue-Eyes spells/traps or explicit includes."""
    filtered = []
    for c in cards:
        ctype = c.get('type', '')
        name  = c.get('name')
        arche = c.get('archetype')
        if ('Spell' in ctype or 'Trap' in ctype) and (arche == 'Blue-Eyes' or name in EXPLICIT_INCLUDES):
            filtered.append(c)
    return filtered


def filter_exclude_subtypes(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Exclude cards whose type contains any EXCLUDE_SUBTYPES."""
    return [c for c in cards
            if not any(sub in c.get('type', '') for sub in EXCLUDE_SUBTYPES)]


def filter_banned(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Exclude cards forbidden in TCG banlist."""
    return [c for c in cards
            if c.get('banlist_info', {}).get('ban_tcg') != 'Forbidden']


def save_cards(cards: List[Dict[str, Any]], path: str) -> None:
    """Save a list of card dicts to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    all_cards    = fetch_cards(API_ALL_URL)
    main_deck    = filter_main_deck(all_cards)
    be_spells    = fetch_cards(API_BE_SPELLS)
    be_traps     = fetch_cards(API_BE_TRAPS)
    monsters     = filter_monsters(main_deck)
    spells_traps = filter_spells_traps(be_spells + be_traps)
    combined     = filter_exclude_subtypes(monsters + spells_traps)
    for name in EXPLICIT_INCLUDES:
        if not any(c.get('name') == name for c in combined):
            card = next((c for c in all_cards if c.get('name') == name), None)
            if card:
                combined.append(card)
    final_cards  = filter_banned(combined)
    save_cards(final_cards, os.path.join('data', 'selected_main_deck_cards.json'))
    print(f"Final pool: {len(final_cards)} cards saved.")
