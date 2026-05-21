"""
export.py — Encode all products with the fine-tuned model and save the
            embedding matrix + matching product catalogue.

ALIGNMENT INVARIANT: row i of embeddings.npy corresponds to row i of catalogue.csv.
Both files must be regenerated together if either changes.

Run standalone:  python export.py
Import:          from export import export_embeddings
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

import config
from preprocess import strip_store_prefix


def export_embeddings(
    model_dir: str      = config.MODEL_DIR,
    products_path: str  = config.PRODUCTS_PATH,
    embeddings_path: str = config.EMBEDDINGS_PATH,
    catalogue_path: str  = config.CATALOGUE_PATH,
) -> None:
    """
    Encode all products with the fine-tuned model, then save:
    - embeddings.npy  — float32 array of shape (n_products, 384)
    - catalogue.csv   — product metadata aligned row-for-row with embeddings

    Store-prefix stripping is applied before encoding so embeddings represent
    product semantics, not retailer identity. The original name is preserved
    in the catalogue for display.
    """
    os.makedirs(os.path.dirname(embeddings_path), exist_ok=True)

    # ── Load model ───────────────────────────────────────────────────────────
    print(f"Loading fine-tuned model from {model_dir} …")
    model = SentenceTransformer(model_dir)

    # ── Load product catalogue ───────────────────────────────────────────────
    print(f"Loading products from {products_path} …")
    catalogue = pd.read_csv(products_path)
    catalogue = catalogue.dropna(subset=["name"]).reset_index(drop=True)
    print(f"  {len(catalogue)} products from {catalogue['store'].nunique()} stores")

    # ── Build cleaned name list for encoding ─────────────────────────────────
    # Always recompute name_clean so it stays in sync with the current
    # STORE_PREFIXES, even if all_products.csv was built with an older version.
    catalogue["name_clean"] = catalogue["name"].astype(str).apply(strip_store_prefix)

    names_clean = catalogue["name_clean"].astype(str).tolist()

    # ── Encode ───────────────────────────────────────────────────────────────
    print(f"Encoding {len(names_clean)} products …")
    embeddings = model.encode(
        names_clean,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2-normalise: cosine sim = dot product at query time
    )
    embeddings = embeddings.astype(np.float32)

    # ── Save embeddings ──────────────────────────────────────────────────────
    np.save(embeddings_path, embeddings)
    print(f"Saved embeddings: shape {embeddings.shape} → {embeddings_path}")

    # ── Save catalogue ───────────────────────────────────────────────────────
    # Select required columns; add any that may be missing with None
    cols = ["name", "name_clean", "store", "price", "price_per_100", "query", "brand"]
    for col in cols:
        if col not in catalogue.columns:
            catalogue[col] = None
    catalogue[cols].to_csv(catalogue_path, index=False)
    print(f"Saved catalogue:  {len(catalogue)} rows → {catalogue_path}")

    # ── Alignment check ──────────────────────────────────────────────────────
    saved = pd.read_csv(catalogue_path)
    saved_emb = np.load(embeddings_path)
    assert len(saved) == saved_emb.shape[0], (
        f"Alignment error: {len(saved)} catalogue rows vs {saved_emb.shape[0]} embeddings"
    )
    print(f"Alignment check passed: {len(saved)} rows = {saved_emb.shape[0]} embeddings")


if __name__ == "__main__":
    export_embeddings()
    print("\nExport complete.")
