import matplotlib.pyplot as plt
from src.database import load_card_db
from src.deck_optimiser import (
    sanitize_seed_deck,
    load_seed_decks,
    generate_random_deck,
    de_evolve
)
from src.fitness import fitness, MIN_INITIAL_FITNESS, NP
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup
card_db = load_card_db()
seeds = load_seed_decks("data/seed_decks.json")
sanitized = [sanitize_seed_deck(s, card_db) for s in seeds]
def build_initial_pop():
    pop = []
    for s in sanitized:
        if fitness(s) >= MIN_INITIAL_FITNESS and len(pop) < NP:
            pop.append(s)
    while len(pop) < NP:
        deck = generate_random_deck(card_db)
        if fitness(deck) >= MIN_INITIAL_FITNESS:
            pop.append(deck)
    return pop

initial_pop = build_initial_pop()

# Run once for 10k gens
final_pop, history = de_evolve(card_db, initial_pop, gens=500, milestones=None)

# --- Build a line of best fitness at every generation ---
all_gens = list(range(1, 501))
best_scores = []
best_so_far = float('-inf')
for gen in all_gens:
    if gen in history:
        best_so_far = max(best_so_far, history[gen])
    best_scores.append(best_so_far)

plt.figure()
plt.plot(all_gens, best_scores, label='Best Fitness So Far')
plt.xlabel("Generations")
plt.ylabel("Best Fitness")
plt.title("DE Performance (Best Fitness Over Time)")
plt.grid(True)
plt.legend()
plt.savefig("de_performance.png")
plt.show()
plt.close()
print("Plot saved as de_performance.png and displayed on screen")
