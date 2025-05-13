import os
import json
import random
import argparse
from typing import Dict, List, Tuple
from src.database import load_card_db
from src.fitness import fitness
from src.deck_optimiser import (
    sanitize_seed_deck,
    load_seed_decks,
    generate_random_deck,
    format_deck
)

# == GA PARAMETERS ==
NP        = 14           # population size
GENS      = 500        # default # generations
TOUR_SIZE = 3            # tournament selection size
MUT_RATE  = 0.1          # per-gene mutation rate (10% of cards)
ELITE     = 2            # number of top individuals to carry over

#!/usr/bin/env python3
import os
import random
import argparse
from typing import Dict, List, Tuple

from src.database import load_card_db
from src.fitness import fitness
from src.deck_optimiser import (
    sanitize_seed_deck,
    load_seed_decks,
    generate_random_deck,
    format_deck
)

# == GA PARAMETERS ==
NP        = 14      # population size
GENS      = 10000   # default generations
TOUR_SIZE = 3       # tournament selection size
MUT_RATE  = 0.1     # per-slot mutation probability
ELITE     = 2       # count of elites to carry each gen

def parse_args():
    p = argparse.ArgumentParser(description="Run GA optimizer for Yu-Gi-Oh! decks")
    p.add_argument('-g', '--gens', type=int, default=GENS,
                   help='Number of generations to run')
    return p.parse_args()

def tournament_selection(pop: List[Dict[int,int]], k: int) -> Dict[int,int]:
    aspirants = random.sample(pop, k)
    return max(aspirants, key=fitness)

def uniform_crossover(p1: Dict[int,int], p2: Dict[int,int]) -> Dict[int,int]:
    # Flatten each parent into a 40-slot list
    slots1 = [cid for cid,cnt in p1.items() for _ in range(cnt)]
    slots2 = [cid for cid,cnt in p2.items() for _ in range(cnt)]
    # Build child slot-by-slot
    child_slots = []
    for i in range(40):
        if random.random() < 0.5 and i < len(slots1):
            child_slots.append(slots1[i])
        elif i < len(slots2):
            child_slots.append(slots2[i])
        else:
            child_slots.append(random.choice(slots1 + slots2))
    # Collapse back to counts
    child = {}
    for cid in child_slots:
        child[cid] = child.get(cid,0) + 1
    return child

def mutate_deck(deck: Dict[int,int], card_db: Dict[int,Dict]) -> Dict[int,int]:
    # Flatten
    slots = [cid for cid,cnt in deck.items() for _ in range(cnt)]
    # Random slot-swaps
    for i in range(len(slots)):
        if random.random() < MUT_RATE:
            slots[i] = random.choice(list(card_db.keys()))
    # Rebuild counts, enforcing banlist limits
    newd = {}
    for cid in slots:
        lim = card_db[cid]['banlist_limit']
        newd[cid] = min(newd.get(cid,0) + 1, lim)
    # Fix deck size to exactly 40
    flat = [cid for cid,cnt in newd.items() for _ in range(cnt)]
    if len(flat) > 40:
        flat = random.sample(flat, 40)
    while len(flat) < 40:
        flat.append(random.choice(list(card_db.keys())))
    final = {}
    for cid in flat:
        final[cid] = final.get(cid,0) + 1
    return final

def run_ga(
    card_db: Dict[int,Dict],
    seeds: List[Dict[int,int]],
    gens: int
) -> Tuple[List[Dict[int,int]], List[float]]:
    """
    Runs the GA for `gens` generations.
    Returns (final_population, avg_fitnesses_per_generation).
    """
    # 1) Sanitize seeds + initial population
    sanitized = [sanitize_seed_deck(s, card_db) for s in seeds]
    pop = sanitized[:NP]
    while len(pop) < NP:
        pop.append(generate_random_deck(card_db))

    print("=== GA Initial Population ===")
    for i, d in enumerate(pop,1):
        print(f"Deck {i:2d}: Fitness={fitness(d):.2f}")
    print()

    # 2) Evolution loop
    avg_fitnesses: List[float] = []
    for gen in range(1, gens+1):
        # a) Elitism
        pop = sorted(pop, key=fitness, reverse=True)
        next_pop = pop[:ELITE]

        # b) Generate the rest
        while len(next_pop) < NP:
            p1 = tournament_selection(pop, TOUR_SIZE)
            p2 = tournament_selection(pop, TOUR_SIZE)
            child = uniform_crossover(p1, p2)
            child = mutate_deck(child, card_db)
            # ⬅ enforce banlist & deck-size
            child = sanitize_seed_deck(child, card_db)
            next_pop.append(child)
        pop = next_pop

        # c) Record average fitness
        avg = sum(fitness(d) for d in pop) / len(pop)
        avg_fitnesses.append(avg)

        # d) Logging
        if gen <= 5 or gen % (gens//10 if gens>=10 else 1) == 0:
            best = fitness(pop[0])
            print(f"Gen {gen:5d}: Best={best:.2f}, Avg={avg:.2f}")

    # 3) Final best deck
    best_deck = pop[0]
    print("\n=== GA Best Deck ===")
    print(f"Fitness = {fitness(best_deck):.2f}")
    print(format_deck(best_deck, card_db))

    return pop, avg_fitnesses

def main():
    args    = parse_args()
    card_db = load_card_db(os.path.join("data","blue_eyes_clean.json"))
    seeds   = load_seed_decks(os.path.join("data","seed_decks.json"))

    final_pop, avg_fitnesses = run_ga(card_db, seeds, args.gens)

    # ─── Plot average fitness over generations ───
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib not installed; skipping plot.")
    else:
        gens = list(range(1, args.gens+1))
        plt.figure()
        plt.plot(gens, avg_fitnesses, marker='o')
        plt.xlabel("Generation")
        plt.ylabel("Average Fitness")
        plt.title("GA: Average Fitness per Generation")
        plt.grid(True)
        plt.show()

if __name__ == '__main__':
    main()

