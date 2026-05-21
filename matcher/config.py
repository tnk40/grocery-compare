"""
config.py — All constants and file paths for the production pipeline.

All other modules import from here. No hardcoded values anywhere else.
"""
import os
from pathlib import Path

# ── Matcher package directory (same directory as this file) ─────────────────
_BASE = Path(__file__).resolve().parent

# ── Model ────────────────────────────────────────────────────────────────────
BASE_MODEL        = "all-MiniLM-L6-v2"
CONTRASTIVE_MARGIN = 1.0
NUM_EPOCHS        = 5
BATCH_SIZE        = 32
LEARNING_RATE     = 2e-5
WARMUP_RATIO      = 0.1
RANDOM_SEED       = 42

# ── Matching thresholds ──────────────────────────────────────────────────────
TAU_MATCH         = 0.85   # above this = same product (identical across stores)
TAU_SUBSTITUTION  = 0.50   # between TAU_SUBSTITUTION and TAU_MATCH = substitution candidate

# ── Pair generation ──────────────────────────────────────────────────────────
UNIT_PRICE_POSITIVE_RATIO = 0.75   # min unit-price ratio for positive pair
UNIT_PRICE_NEGATIVE_RATIO = 0.50   # max unit-price ratio for hard negative pair
EASY_NEGATIVE_FRACTION    = 1 / 3  # easy negatives as fraction of positives

# ── Paths (absolute, derived from this file's location) ─────────────────────
RAW_DATA_DIR    = str(_BASE / "data")
PROCESSED_DIR   = str(_BASE / "data" / "processed")
MODEL_DIR       = str(_BASE / "models" / "product_matcher")
EMBEDDINGS_PATH = str(_BASE / "data" / "processed" / "embeddings.npy")
CATALOGUE_PATH  = str(_BASE / "data" / "processed" / "catalogue.csv")
PAIRS_PATH      = str(_BASE / "data" / "processed" / "training_pairs.csv")
PRODUCTS_PATH   = str(_BASE / "data" / "processed" / "all_products.csv")

# ── Store prefixes to strip ──────────────────────────────────────────────────
STORE_PREFIXES = sorted([
    # Waitrose
    "Essential Waitrose & Partners",
    "Essential Waitrose",
    "Waitrose & Partners",
    "Waitrose Duchy Organic",
    "Duchy Organic",
    "Cooks' Ingredients",
    "No.1",
    "Essential",
    "Waitrose",
    # Sainsbury's
    "Sainsbury's Taste the Difference",
    "Sainsbury's SO Organic",
    "Sainsbury's Hubbard's",
    "Stamford Street Co.",
    "by Sainsbury's",
    "Sainsbury's",
    "Sainsburys",
    # Morrisons
    "Morrisons The Best",
    "Morrisons Savers",
    "Market Street",
    "Morrisons",
    "Morrison's",
    # ASDA
    "JUST ESSENTIALS by ASDA",
    "Exceptional by ASDA",
    "The BAKERY at ASDA",
    "ASDA Extra Special",
    "ASDA Just Essentials",
    "ASDA Smart Price",
    "ASDA",
    "Asda",
    # Aldi
    "EVERYDAY ESSENTIALS",
    "Specially Selected",
    "Nature's Pick",
    "Cowbelle",
    "COWBELLE",
    "Brooklea",
    "Aldi",
    "Lidl",
], key=len, reverse=True)
