"""
preprocess.py — Load raw store CSVs, clean product names, compute per-100g prices.

Run standalone:  python preprocess.py
Import:          from preprocess import preprocess, strip_store_prefix
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np

import config


# ── Store-prefix stripping ────────────────────────────────────────────────────

def strip_store_prefix(name: str) -> str:
    """Remove store/own-brand prefixes so the model sees product semantics only.

    Applies iteratively until no further prefix can be stripped, handling
    stacked prefixes such as 'Waitrose Duchy Organic Sweetcorn' where
    stripping 'Waitrose' leaves a second strippable prefix 'Duchy Organic'.
    """
    if not isinstance(name, str):
        return name
    while True:
        stripped_any = False
        for prefix in config.STORE_PREFIXES:
            if name.lower().startswith(prefix.lower()):
                candidate = name[len(prefix):].strip(" -\u2013\u2014:,")
                if candidate:
                    name = candidate
                    stripped_any = True
                    break   # restart scan with the shortened name
        if not stripped_any:
            break
    return name


# ── Waitrose brand inference ──────────────────────────────────────────────────

def infer_waitrose_brand(name: str) -> str:
    """Infer Waitrose product brand from naming convention prefix."""
    name = str(name)
    if name.startswith("Essential"):
        return "Waitrose"
    if name.startswith("Duchy Organic"):
        return "Duchy Organic"
    if name.startswith("Waitrose"):
        return "Waitrose"
    return name.split()[0]


# ── Unit-size parser (Sainsbury's price-correction) ──────────────────────────

def parse_unit_size(size_str) -> float | None:
    """
    Parse a unitSize string (e.g. '20g', '0.03 KG', '2 L', '500 ml') into a
    numeric value in the denominator unit used by unitPrice (kg or L).

    Returns None if the string cannot be parsed.
    """
    if pd.isna(size_str):
        return None
    s = str(size_str).strip().lower()
    m = re.match(r"([0-9.]+)\s*(kg|g|l|ml)", s)
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2)
    if unit == "g":
        return value / 1000
    elif unit == "ml":
        return value / 1000
    elif unit in ("kg", "l"):
        return value
    return None


# ── Per-100g price normalisation ─────────────────────────────────────────────

def compute_price_per_100(row) -> float:
    """
    Normalise unitPrice to a per-100 g or per-100 ml basis.

    Returns float('nan') for per-unit/per-pack items and unparseable rows.
    """
    measure = str(row.get("unitPriceMeasure") or "").lower().strip()
    up = row.get("unitPrice")
    if pd.isna(up) or up == 0:
        return float("nan")

    if re.search(r"per\s+100\s+(g|ml)", measure):
        return float(up)

    if re.search(r"per\s+(1\s+)?kg", measure):
        return float(up) / 10.0

    if re.search(r"per\s+(1\s+)?(litre|ltr?|l\b)", measure):
        return float(up) / 10.0

    if re.search(r"per\s+10\s+g", measure):
        return float(up) * 10.0

    return float("nan")


# ── Query relevance filter ────────────────────────────────────────────────────

def query_matches_name(query: str, name: str) -> bool:
    """Return True if at least one word from the query appears in the product name."""
    query_words = set(query.lower().split())
    name_words = set(str(name).lower().split())
    return len(query_words & name_words) > 0


# ── Main preprocess function ─────────────────────────────────────────────────

def preprocess(
    raw_data_dir: str = config.RAW_DATA_DIR,
    output_dir: str = config.PROCESSED_DIR,
) -> pd.DataFrame:
    """
    Load, clean, and save the combined product catalogue.

    Steps:
    1. Load all 5 store CSVs
    2. Infer Waitrose brand column
    3. Concatenate into one DataFrame
    4. Fix broken Sainsbury's prices (unit-price / pack-size swap)
    5. Compute price_per_100
    6. Drop implausibly cheap rows
    7. Add name_clean column
    8. Filter rows where query has no word in common with name
    9. Save to output_dir/all_products.csv

    Returns the cleaned DataFrame.
    """
    os.makedirs(output_dir, exist_ok=True)

    # ── 1. Load CSVs ─────────────────────────────────────────────────────────
    store_files = {
        "aldi":       os.path.join(raw_data_dir, "dataset_aldi.csv"),
        "asda":       os.path.join(raw_data_dir, "dataset_asda.csv"),
        "morrisons":  os.path.join(raw_data_dir, "dataset_morrisons.csv"),
        "sainsburys": os.path.join(raw_data_dir, "dataset_sainsburys.csv"),
        "waitrose":   os.path.join(raw_data_dir, "dataset_waitrose.csv"),
    }

    frames = {}
    for store, path in store_files.items():
        df_store = pd.read_csv(path)
        frames[store] = df_store
        print(f"  Loaded {store}: {len(df_store)} rows, cols={list(df_store.columns)}")

    # ── 2. Infer Waitrose brand ───────────────────────────────────────────────
    if "brand" not in frames["waitrose"].columns:
        frames["waitrose"]["brand"] = frames["waitrose"]["name"].apply(infer_waitrose_brand)

    # ── 3. Drop GTIN + concatenate ───────────────────────────────────────────
    for store, df_s in frames.items():
        df_s.drop(columns=["gtin"], inplace=True, errors="ignore")

    df = pd.concat(list(frames.values()), ignore_index=True)
    print(f"\nCombined catalogue: {len(df)} rows from {df['store'].nunique()} stores")

    # Ensure brand column exists for all stores
    if "brand" not in df.columns:
        df["brand"] = None

    # ── 4. Fix broken Sainsbury's prices ────────────────────────────────────
    # When price ≈ unitPrice for a weighted item, the scraper swapped them.
    # Back-calculate the correct pack price from unitPrice × pack_size.
    mask_sains = (
        (df["store"] == "sainsburys")
        & df["unitPrice"].notna()
        & df["price"].notna()
        & (abs(df["price"] - df["unitPrice"]) < 0.01)
        & (~df["unitPriceMeasure"].fillna("").isin(["per unit", "per each"]))
    )
    parsed_sizes = df.loc[mask_sains, "unitSize"].apply(parse_unit_size)
    corrected = (df.loc[mask_sains, "unitPrice"] * parsed_sizes).round(2)
    valid = parsed_sizes.notna()
    df.loc[mask_sains & valid.reindex(df.index, fill_value=False), "price"] = corrected[valid]
    print(f"Corrected {valid.sum()} Sainsbury's price-swap rows")

    # ── 5. Compute price_per_100 ─────────────────────────────────────────────
    df["price_per_100"] = df.apply(compute_price_per_100, axis=1)
    n_with = df["price_per_100"].notna().sum()
    print(f"price_per_100 computed for {n_with}/{len(df)} products")

    # Alias unitPrice → unit_price for convenience in downstream code
    if "unitPrice" in df.columns and "unit_price" not in df.columns:
        df["unit_price"] = df["unitPrice"]

    # ── 6. Drop implausibly cheap rows ───────────────────────────────────────
    implausible = (
        (df["price"] < 0.10)
        & (df["unitPrice"].fillna(0) < 1.0)
        & (~df["unitPriceMeasure"].fillna("").str.contains("each", case=False, na=False))
    )
    n_dropped = implausible.sum()
    df = df[~implausible].reset_index(drop=True)
    print(f"Dropped {n_dropped} implausibly cheap rows")

    # ── 7. Add name_clean ────────────────────────────────────────────────────
    df["name_clean"] = df["name"].apply(strip_store_prefix)
    n_stripped = (df["name"] != df["name_clean"]).sum()
    print(f"Stripped store prefix from {n_stripped} product names")

    # ── 8. Query–name relevance filter ──────────────────────────────────────
    before = len(df)
    df = df[df.apply(lambda r: query_matches_name(r["query"], r["name"]), axis=1)]
    df = df.reset_index(drop=True)
    print(f"Query filter: {before} → {len(df)} rows")

    # ── 9. Save ──────────────────────────────────────────────────────────────
    out_path = os.path.join(output_dir, "all_products.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved {len(df)} products to {out_path}")
    print(f"Stores: {sorted(df['store'].unique())}")

    return df


if __name__ == "__main__":
    print("=" * 60)
    print("Preprocessing raw grocery data")
    print("=" * 60)
    df = preprocess()
    print(f"\nDone. Shape: {df.shape}")
