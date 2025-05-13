#!/usr/bi
import os
import json
import random
import argparse
from typing import Dict, List, Tuple

from src.database import load_card_db
from src.fitness import fitness

# == PARAMETERS ==
NP = 16                   # ⬅ UPDATED: population size
DECK_SIZE = 40
F = 1.2
CR = 1.0           # ⬅ UPDATED: crossover rate

MIN_INITIAL_FITNESS = 5.0  # ⬅ UPDATED
MIN_FITNESS         = 10.0  # ⬅ UPDATED

# == FILE PATHS ==
CARD_DB_PATH = os.path.join("data", "blue_eyes_clean.json")
SEEDS_PATH   = os.path.join("data", "seed_decks.json")


def parse_args():
    p = argparse.ArgumentParser(description="Run DE optimizer for Yu-Gi-Oh! decks")
    p.add_argument('-g', '--gens', type=int, default=2,
                   help='Number of generations to run (default=2)')
    return p.parse_args()


def format_deck(deck: Dict[int,int], card_db: Dict[int, Dict]) -> str:
    """
    Return a multi-line string listing each card as:
      Card Name (ID) xCount
    """
    lines = []
    for cid, cnt in deck.items():
        name = card_db.get(cid, {}).get('name', 'UNKNOWN')
        lines.append(f"{name} ({cid}) x{cnt}")
    return "\n".join(lines)


def sanitize_seed_deck(
    deck: Dict[int,int],
    card_db: Dict[int, Dict],
    deck_size: int = DECK_SIZE
) -> Dict[int,int]:
    """
    1) Replace any card not in card_db with random valid cards.
    2) Enforce banlist limits on counts.
    3) Trim or pad to exactly `deck_size` cards.
    """
    sanitized: Dict[int,int] = {}
    valid_ids = list(card_db.keys())

    # 1 & 2: keep only IDs in card_db, cap by banlist; replace invalid ones
    for cid, cnt in deck.items():
        if cid in card_db:
            limit = card_db[cid]['banlist_limit']
            sanitized[cid] = min(cnt, limit)
        else:
            # replace each invalid copy
            for _ in range(cnt):
                new_cid = random.choice(valid_ids)
                lim = card_db[new_cid]['banlist_limit']
                sanitized[new_cid] = min(sanitized.get(new_cid, 0) + 1, lim)

    # 3a: adjust to exact deck_size
    pool = [cid for cid, cnt in sanitized.items() for _ in range(cnt)]
    if len(pool) > deck_size:
        pool = random.sample(pool, deck_size)
    while len(pool) < deck_size:
        cid = random.choice(valid_ids)
        if pool.count(cid) < card_db[cid]['banlist_limit']:
            pool.append(cid)

    # rebuild count dict
    final: Dict[int,int] = {}
    for cid in pool:
        final[cid] = final.get(cid, 0) + 1
    return final


def load_seed_decks(path: str) -> List[Dict[int, int]]:
    if not os.path.isfile(path):
        print(f"[WARN] Seed file not found at: {path}. Continuing without seeds.")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_random_deck(card_db: Dict[int, Dict], deck_size: int = DECK_SIZE) -> Dict[int, int]:
    pool: List[int] = []
    for cid, info in card_db.items():
        pool.extend([cid] * info['banlist_limit'])
    chosen = random.sample(pool, deck_size)
    deck: Dict[int, int] = {}
    for cid in chosen:
        deck[cid] = deck.get(cid, 0) + 1
    return deck


def mutate(a: Dict[int,int], b: Dict[int,int], c: Dict[int,int], card_db: Dict[int, Dict]) -> Dict[int,int]:
    mutant: Dict[int,int] = {}
    all_ids = set(a) | set(b) | set(c)
    for cid in all_ids:
        ac, bc, cc = a.get(cid,0), b.get(cid,0), c.get(cid,0)
        count = round(ac + F * (bc - cc))
        limit = card_db[cid]['banlist_limit']
        mutant[cid] = max(0, min(count, limit))
    # adjust to exact size
    pool = [cid for cid, cnt in mutant.items() for _ in range(cnt)]
    if len(pool) > DECK_SIZE:
        pool = random.sample(pool, DECK_SIZE)
    while len(pool) < DECK_SIZE:
        pool.append(random.choice(list(mutant.keys())))
    # Card swap mutation: with some probability, swap a random card for a new one
    if random.random() < 0.5:  # 50% chance for swap mutation
        idx_to_replace = random.randrange(DECK_SIZE)
        valid_ids = list(card_db.keys())
        new_cid = random.choice(valid_ids)
        pool[idx_to_replace] = new_cid
    new_deck = {}
    for cid in pool:
        new_deck[cid] = new_deck.get(cid, 0) + 1
    return new_deck


def crossover(target: Dict[int,int], mutant: Dict[int,int], card_db: Dict[int, Dict]) -> Dict[int,int]:
    t_list = [cid for cid,cnt in target.items() for _ in range(cnt)]
    m_list = [cid for cid,cnt in mutant.items() for _ in range(cnt)]
    # pad/truncate to DECK_SIZE
    t_list = t_list[:DECK_SIZE] + [random.choice(t_list)]*(DECK_SIZE-len(t_list))
    m_list = m_list[:DECK_SIZE] + [random.choice(m_list)]*(DECK_SIZE-len(m_list))
    trial_list = []
    j_rand = random.randrange(DECK_SIZE)
    for j in range(DECK_SIZE):
        if random.random() < CR or j == j_rand:
            trial_list.append(m_list[j])
        else:
            trial_list.append(t_list[j])
    # GA-style mutation: with small probability, replace a random card
    if random.random() < 0.2:  # 20% chance
        idx_to_replace = random.randrange(DECK_SIZE)
        valid_ids = list(card_db.keys())
        trial_list[idx_to_replace] = random.choice(valid_ids)
    trial = {}
    for cid in trial_list:
        trial[cid] = trial.get(cid, 0) + 1
    return trial


def select_next(pairs: List[Tuple[Dict[int,int],Dict[int,int]]]) -> List[Dict[int,int]]:
    new_pop = []
    for target, trial in pairs:
        new_pop.append(trial if fitness(trial) > fitness(target) else target)
    return new_pop

def de_evolve(
        card_db: Dict[int, Dict],
        init_pop: List[Dict[int, int]],
        gens: int,
        output_file: str,
        milestones: List[int] = None
) -> Tuple[List[Dict[int, int]], Dict[int, float]]:
    """
    Evolves init_pop for `gens` generations.
    Records best fitness at every generation in history.
    Writes results to the specified output file.
    Returns (final_population, history).
    """
    pop = init_pop
    history = {}
    for gen in range(1, gens + 1):
        pairs = []
        for i in range(len(pop)):
            idxs = list(range(len(pop)))
            idxs.remove(i)
            a, b, c = [pop[j] for j in random.sample(idxs, 3)]
            mutant = mutate(a, b, c, card_db)
            trial = crossover(pop[i], mutant, card_db)
            pairs.append((pop[i], trial))

        # Selection
        pop = select_next(pairs)

        # Rescue low-fitness decks
        for i, deck in enumerate(pop):
            if fitness(deck) < MIN_FITNESS:
                others = [j for j in range(len(pop)) if j != i]
                a, b, c = [pop[j] for j in random.sample(others, 3)]
                pop[i] = mutate(a, b, c, card_db)

        # After selection and rescue, inject random decks for exploration
        if gen % 5 == 0:  # every 5 generations (increased frequency)
            idx = random.randrange(len(pop))
            pop[idx] = generate_random_deck(card_db)

        # Print this generation
        print(f"\n=== Generation {gen} ===")
        for idx, deck in enumerate(pop[:100], 1):  # Limit to top 100 decks
            print(f"Deck {idx:2d}: Fitness={fitness(deck):.2f}")
            print(format_deck(deck, card_db))
            print()

        # Record best fitness at every generation
        best_score = max(fitness(deck) for deck in pop)
        history[gen] = best_score

    # Write results to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        count = 0
        for idx, deck in enumerate(pop):
            fit = fitness(deck)
            if fit > 0:
                count += 1
                if count > 100:
                    break
                f.write(f"Deck {count:2d}: Fitness={fit:.2f}\n")
                f.write(format_deck(deck, card_db))
                f.write("\n\n")

    # Record final generation if not already in history
    if gens not in history:
        history[gens] = max(fitness(deck) for deck in pop)

    return pop, history


def main():
    args = parse_args()
    card_db = load_card_db(CARD_DB_PATH)
    seeds = load_seed_decks(SEEDS_PATH)

    # Sanitize seeds
    sanitized = [sanitize_seed_deck(s, card_db) for s in seeds]

    # Build initial population with fitness ≥ MIN_INITIAL_FITNESS
    pop: List[Dict[int, int]] = []
    for deck in sanitized:
        if fitness(deck) >= MIN_INITIAL_FITNESS and len(pop) < NP:
            pop.append(deck)
    while len(pop) < NP:
        candidate = generate_random_deck(card_db)
        if fitness(candidate) >= MIN_INITIAL_FITNESS:
            pop.append(candidate)

    # Gen-0 output
    print("=== Initial Population ===")
    for idx, deck in enumerate(pop, 1):
        print(f"Deck {idx:2d}: Fitness={fitness(deck):.2f}")
        print(format_deck(deck, card_db))
        print()

    # Evolve & capture final population
    output_file = "results_de_evolution.txt"
    final_pop, history = de_evolve(card_db, pop, args.gens, output_file)

    # Print best deck overall
    best_deck = max(final_pop, key=lambda d: fitness(d))
    best_score = fitness(best_deck)
    print("\n=== Best Deck After Evolution ===")
    print(f"Fitness = {best_score:.2f}")
    print(format_deck(best_deck, card_db))

    print(f"\nResults written to '{output_file}'")

    # Plot performance if history is available
    if history:
        import matplotlib.pyplot as plt
        gens = sorted(history.keys())
        scores = [history[g] for g in gens]
        plt.figure()
        plt.plot(gens, scores, marker='o')
        plt.xlabel("Generations")
        plt.ylabel("Best Fitness")
        plt.title("DE Performance ")
        plt.grid(True)
        plt.savefig("de_performance.png")
        plt.show()
        plt.close()
        print("Plot saved as de_performance.png and displayed on screen")


if __name__ == '__main__':
    main()