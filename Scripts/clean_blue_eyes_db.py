
import json
import os

INPUT_PATH  = os.path.join('data', 'selected_main_deck_cards.json')
OUTPUT_PATH = os.path.join('data', 'blue_eyes_clean.json')

def clean_deck_db(input_path: str, output_path: str):
    with open(input_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)

    EXCLUDE_ARCHETYPES = {'Genex', 'Performapal', 'Odd-Eyes', 'Dragunity', 'D/D/D', 'D/D',
                           'D/D/D/D', 'D/D/D/D/D','Photon', 'Malefic', 'Gishki',
                             'Gusto', 'Gem-Knight', 'Fabled', 'Nekroz', 'Noble Knight', 'Aether',}


    cleaned = []
    for card in cards:
        if card.get('archetype') in EXCLUDE_ARCHETYPES:
            continue

        cleaned.append({
            'id': card.get('id'),
            'name': card.get('name'),
            'type': card.get('type'),
            'archetype': card.get('archetype')  
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Nettoyé : {len(cleaned)} cartes écrites dans {output_path}")

if __name__ == '__main__':
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    clean_deck_db(INPUT_PATH, OUTPUT_PATH)
