"""
pairs.py — Generate training pairs from the preprocessed product catalogue.

Produces: positive pairs, three types of hard negatives, and easy negatives.
All pairs have name_a/name_b (cleaned, model-facing) and name_a_orig/name_b_orig
(original names, for display).

Run standalone:  python pairs.py
Import:          from pairs import generate_pairs
"""
import itertools
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import config
from preprocess import preprocess


def generate_pairs(
    products_df: pd.DataFrame,
    output_path: str = config.PAIRS_PATH,
) -> pd.DataFrame:
    """
    Generate training pairs and save to CSV.

    Pair types:
    - Positive: cross-store, same query, unit-price ratio >= UNIT_PRICE_POSITIVE_RATIO
    - Hard type 1: same-store, same query, all product combinations (cap 4 per group)
    - Hard type 2: cross-store, same query, unit-price ratio < UNIT_PRICE_NEGATIVE_RATIO
    - Hard type 3: cross-store, same query, price_per_100 ratio > 2
    - Easy: completely different queries, sampled at EASY_NEGATIVE_FRACTION × positives

    Returns the pairs DataFrame.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df = products_df.copy()

    # Ensure unit_price alias exists
    if "unitPrice" in df.columns and "unit_price" not in df.columns:
        df["unit_price"] = df["unitPrice"]

    positive_pairs = []
    hard_type2     = []   # cross-store, low unit-price ratio
    hard_type3     = []   # cross-store, high price_per_100 ratio
    hard_type1     = []   # same-store combinations

    rng = np.random.default_rng(config.RANDOM_SEED)

    for query, grp in df.groupby("query"):
        rows = grp.to_dict("records")

        # ── Cross-store pairs (positives + type-2/3 hard negatives) ──────────
        for a, b in itertools.combinations(rows, 2):
            if a["store"] == b["store"]:
                continue

            pair_base = dict(
                name_a=a["name_clean"], store_a=a["store"],
                name_b=b["name_clean"], store_b=b["store"],
                name_a_orig=a["name"], name_b_orig=b["name"],
                query=query,
            )

            # Unit-price ratio gate
            ua = a.get("unit_price") or a.get("unitPrice")
            ub = b.get("unit_price") or b.get("unitPrice")
            if ua and ub and ua > 0 and ub > 0:
                ratio = min(ua, ub) / max(ua, ub)
                if ratio >= config.UNIT_PRICE_POSITIVE_RATIO:
                    positive_pairs.append({**pair_base, "label": 1})
                elif ratio < config.UNIT_PRICE_NEGATIVE_RATIO:
                    hard_type2.append({**pair_base, "label": 0})

            # price_per_100 ratio gate (type 3 hard negative)
            pa = a.get("price_per_100")
            pb = b.get("price_per_100")
            if (
                pa is not None and pb is not None
                and pd.notna(pa) and pd.notna(pb)
                and float(pa) > 0 and float(pb) > 0
            ):
                p_ratio = max(float(pa), float(pb)) / min(float(pa), float(pb))
                if p_ratio > 2.0:
                    hard_type3.append({**pair_base, "label": 0})

        # ── Same-store hard negatives (type 1, cap at 4 per group) ───────────
        for store, store_grp in grp.groupby("store"):
            store_rows = store_grp.to_dict("records")
            if len(store_rows) < 2:
                continue
            combos = list(itertools.combinations(store_rows, 2))
            if len(combos) > 4:
                chosen_idx = rng.choice(len(combos), size=4, replace=False)
                combos = [combos[i] for i in chosen_idx]
            for a, b in combos:
                hard_type1.append(dict(
                    name_a=a["name_clean"], store_a=a["store"],
                    name_b=b["name_clean"], store_b=b["store"],
                    name_a_orig=a["name"], name_b_orig=b["name"],
                    label=0, query=query,
                ))

    if not positive_pairs:
        raise ValueError(
            "No positive pairs generated. Check that the data has products from "
            "multiple stores for the same query."
        )

    # ── Easy negatives (cross-query sampling) ────────────────────────────────
    np.random.seed(config.RANDOM_SEED)
    easy_pairs  = []
    queries_arr = df["query"].unique()
    n_easy      = int(len(positive_pairs) * config.EASY_NEGATIVE_FRACTION)

    for _ in range(n_easy):
        q1, q2 = np.random.choice(queries_arr, 2, replace=False)
        sub1 = df[df["query"] == q1]
        sub2 = df[df["query"] == q2]
        if len(sub1) == 0 or len(sub2) == 0:
            continue
        r1 = sub1.sample(1).iloc[0]
        r2 = sub2.sample(1).iloc[0]
        easy_pairs.append(dict(
            name_a=r1["name_clean"], store_a=r1["store"],
            name_b=r2["name_clean"], store_b=r2["store"],
            name_a_orig=r1["name"], name_b_orig=r2["name"],
            label=0,
            query=f"{q1}|{q2}",
        ))

    # ── Combine, assign difficulty, deduplicate ───────────────────────────────
    all_hard = hard_type1 + hard_type2 + hard_type3

    pos_df  = pd.DataFrame(positive_pairs)
    hard_df = pd.DataFrame(all_hard) if all_hard else pd.DataFrame(columns=pos_df.columns)
    easy_df = pd.DataFrame(easy_pairs) if easy_pairs else pd.DataFrame(columns=pos_df.columns)

    pos_df["difficulty"]  = "positive"
    hard_df["difficulty"] = "hard"
    easy_df["difficulty"] = "easy"

    pairs_df = pd.concat([pos_df, hard_df, easy_df], ignore_index=True)
    pairs_df = pairs_df.drop_duplicates(subset=["name_a", "name_b"]).reset_index(drop=True)

    pairs_df.to_csv(output_path, index=False)

    print(f"Generated {len(pairs_df)} training pairs → {output_path}")
    print(f"  Positive:      {(pairs_df['difficulty'] == 'positive').sum()}")
    print(f"  Hard negative: {(pairs_df['difficulty'] == 'hard').sum()}")
    print(f"  Easy negative: {(pairs_df['difficulty'] == 'easy').sum()}")

    return pairs_df


if __name__ == "__main__":
    products_path = config.PRODUCTS_PATH
    if os.path.exists(products_path):
        print(f"Loading preprocessed data from {products_path}")
        df = pd.read_csv(products_path)
    else:
        print("Preprocessed data not found — running preprocess.py first …")
        df = preprocess()

    generate_pairs(df)
