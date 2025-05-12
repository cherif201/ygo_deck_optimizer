import os
import json
import random
import argparse
from typing import Dict, List, Tuple
from src.database import load_card_db
from src.fitness import fitness




NP = 1000                 # population size
DECK_SIZE = 40            # number of cards per deck
F = 0.8                   # mutation factor
CR = 0.9                  # crossover rate

MIN_INITIAL_FITNESS = 5.0 
MIN_FITNESS = 10.0


CARD_DB_PATH = os.path.join("data", "blue_eyes_clean.json")
SEEDS_PATH   = os.path.join("data", "seed_decks.json")


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

   
    for cid, cnt in deck.items():
        if cid in card_db:
            limit = card_db[cid]['banlist_limit']
            sanitized[cid] = min(cnt, limit)
        else:
            
            for _ in range(cnt):
                new_cid = random.choice(valid_ids)
                lim = card_db[new_cid]['banlist_limit']
                sanitized[new_cid] = min(sanitized.get(new_cid, 0) + 1, lim)

    
    pool = [cid for cid, cnt in sanitized.items() for _ in range(cnt)]
    if len(pool) > deck_size:
        pool = random.sample(pool, deck_size)

    
    while len(pool) < deck_size:
        cid = random.choice(valid_ids)
        if pool.count(cid) < card_db[cid]['banlist_limit']:
            pool.append(cid)

    
    final: Dict[int,int] = {}
    for cid in pool:
        final[cid] = final.get(cid, 0) + 1

    return final


def parse_args():
    parser = argparse.ArgumentParser(description="Run DE optimizer for Yu-Gi-Oh! decks")
    parser.add_argument('-g', '--gens', type=int, default=2,
                        help='Number of generations to run ')
    return parser.parse_args()


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
    pool=[]
    for cid,cnt in mutant.items(): pool.extend([cid]*cnt)
    if len(pool)>DECK_SIZE: pool=random.sample(pool, DECK_SIZE)
    while len(pool)<DECK_SIZE: pool.append(random.choice(list(mutant.keys())))
    new_deck={}
    for cid in pool: new_deck[cid]=new_deck.get(cid,0)+1
    return new_deck


def crossover(target: Dict[int,int], mutant: Dict[int,int]) -> Dict[int,int]:
    t_list = [cid for cid,cnt in target.items() for _ in range(cnt)]
    m_list = [cid for cid,cnt in mutant.items() for _ in range(cnt)]
    t_list = t_list[:DECK_SIZE] + [random.choice(t_list)]*(DECK_SIZE-len(t_list))
    m_list = m_list[:DECK_SIZE] + [random.choice(m_list)]*(DECK_SIZE-len(m_list))
    trial_list=[]
    j_rand=random.randrange(DECK_SIZE)
    for j in range(DECK_SIZE):
        trial_list.append(m_list[j] if (random.random()<CR or j==j_rand) else t_list[j])
    trial={}
    for cid in trial_list: trial[cid]=trial.get(cid,0)+1
    return trial


def select_next(pairs: List[Tuple[Dict[int,int],Dict[int,int]]]) -> List[Dict[int,int]]:
    new_pop=[]
    for target,trial in pairs:
        new_pop.append(trial if fitness(trial)>fitness(target) else target)
    return new_pop


def de_evolve(card_db: Dict[int, Dict], init_pop: List[Dict[int,int]], gens: int):
    pop = init_pop
    for gen in range(1, gens+1):
        pairs=[]
        for i in range(len(pop)):
            idxs=list(range(len(pop))); idxs.remove(i)
            a,b,c = [pop[j] for j in random.sample(idxs,3)]
            mutant = mutate(a,b,c,card_db)
            trial  = crossover(pop[i], mutant)
            pairs.append((pop[i], trial))
        pop = select_next(pairs)
        pop = select_next(pairs)

        
        for i, deck in enumerate(pop):
            if fitness(deck) < MIN_FITNESS:
                
                others = [j for j in range(len(pop)) if j != i]
                a,b,c = [pop[j] for j in random.sample(others, 3)]
                pop[i] = mutate(a, b, c, card_db)
        print(f"\n=== Generation {gen} ===")
        for idx, deck in enumerate(pop,1):
            print(f"Deck {idx:2d}: Fitness={fitness(deck):.2f}")
            print(format_deck(deck, card_db))
            print()

    return pop


def main():
    args = parse_args()
    card_db = load_card_db(CARD_DB_PATH)
    seeds = load_seed_decks(SEEDS_PATH)
    
    sanitized_seeds = [sanitize_seed_deck(s, card_db) for s in seeds]
    pop = sanitized_seeds[:NP] + [
        generate_random_deck(card_db)
        for _ in range(NP - len(sanitized_seeds))
    ]
        
    pop = []
    for s in sanitized_seeds:
        if fitness(s) >= MIN_INITIAL_FITNESS and len(pop) < NP:
            pop.append(s)
    
    while len(pop) < NP:
        deck = generate_random_deck(card_db)
        if fitness(deck) >= MIN_INITIAL_FITNESS:
            pop.append(deck)

    print("=== Initial Population ===")
    for idx, deck in enumerate(pop,1):
        print(f"Deck {idx:2d}: Fitness={fitness(deck):.2f}")
    print(format_deck(deck, card_db))
    print()  
    
     
    final_pop = de_evolve(card_db, pop, args.gens)       

    
    best_deck = max(final_pop, key=lambda d: fitness(d))  
    best_score = fitness(best_deck)
    print("\n=== Best Deck After Evolution ===")           
    print(f"Fitness = {best_score:.2f}")                  
    print(format_deck(best_deck, card_db))   


if __name__=='__main__':
    main()
