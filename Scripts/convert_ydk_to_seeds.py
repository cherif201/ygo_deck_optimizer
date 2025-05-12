
import os
import json
from collections import Counter

def parse_ydk_file(path: str) -> dict:
    """
    Parse a .ydk file and return a dict mapping card IDs to counts for the main deck.
    """
    deck_ids = []
    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    try:
        main_index = lines.index('#main') + 1
    except ValueError:
        print(f"[WARN] No '#main' section in {path}")
        return {}

    end_index = len(lines)
    for idx, line in enumerate(lines[main_index:], start=main_index):
        if line.startswith('!') or line.startswith('#side') or line.startswith('#extra'):
            end_index = idx
            break

    for code in lines[main_index:end_index]:
        if code.isdigit():
            deck_ids.append(int(code))

    return dict(Counter(deck_ids))


def convert_directory(input_dir: str, output_file: str):
    """
    Convert all .ydk files in input_dir into a JSON array of deck dicts and save to output_file.
    """
    seed_decks = []
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory '{input_dir}' not found.")

    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.ydk'):
            path = os.path.join(input_dir, filename)
            deck = parse_ydk_file(path)
            if deck:
                seed_decks.append(deck)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(seed_decks, f, indent=2)

    print(f"Converted {len(seed_decks)} decks from '{input_dir}' to '{output_file}'")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert .ydk deck files to JSON seed decks for DE optimization"
    )
    parser.add_argument(
        '--input-dir',
        default='data/seeds_ydk',
        help='Directory containing .ydk files'
    )
    parser.add_argument(
        '--output',
        default='data/seed_decks.json',
        help='Path for the output JSON file'
    )
    args = parser.parse_args()

    convert_directory(args.input_dir, args.output)
