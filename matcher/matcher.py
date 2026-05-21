"""
matcher.py — Production matching API for the grocery price comparison website.

Import in the FastAPI backend:
    from matcher.matcher import match, search, find_substitutes

Model and embeddings are loaded lazily on first call (not on import), so the
web server starts up immediately without blocking on the ~1s model load.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

import config
from preprocess import strip_store_prefix


# ── Lazy-loaded module-level state ───────────────────────────────────────────
_model:      SentenceTransformer | None = None
_embeddings: np.ndarray | None          = None
_catalogue:  pd.DataFrame | None        = None


def _load() -> None:
    """Load model, embeddings, and catalogue once on first call."""
    global _model, _embeddings, _catalogue
    if _model is not None:
        return
    _model = SentenceTransformer(config.MODEL_DIR)
    _embeddings = np.load(config.EMBEDDINGS_PATH).astype(np.float32)
    _catalogue  = pd.read_csv(config.CATALOGUE_PATH)
    # Re-normalise embeddings in case they weren't exported normalised
    norms = np.linalg.norm(_embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)   # avoid div-by-zero for zero vectors
    _embeddings = _embeddings / norms


def match(query: str, top_k: int = 5) -> list[dict]:
    """
    Encode a free-text query and return the closest products across all stores.

    Only returns products with cosine similarity >= TAU_SUBSTITUTION.
    Results are sorted by similarity descending.

    Each result dict:
        name, name_clean, store, price, price_per_100, similarity, confident
    The 'confident' flag is True when similarity >= TAU_MATCH, indicating the
    product is essentially an exact cross-store match rather than a near-match.
    """
    _load()
    query_clean = strip_store_prefix(query)
    query_emb   = _model.encode(
        [query_clean], normalize_embeddings=True, show_progress_bar=False
    )[0].astype(np.float32)

    sims = np.dot(_embeddings, query_emb)   # shape (n_products,)

    # Filter to the substitution band and above
    mask    = sims >= config.TAU_SUBSTITUTION
    indices = np.where(mask)[0]

    if len(indices) == 0:
        return []

    # Sort by similarity descending, take top_k
    sorted_idx = indices[np.argsort(-sims[indices])][:top_k]

    results = []
    for i in sorted_idx:
        row = _catalogue.iloc[int(i)]
        sim = float(sims[i])
        p100 = row.get("price_per_100")
        results.append({
            "name":        row["name"],
            "name_clean":  row["name_clean"],
            "store":       row["store"],
            "price":       float(row["price"]),
            "price_per_100": float(p100) if pd.notna(p100) else None,
            "similarity":  round(sim, 4),
            "confident":   sim >= config.TAU_MATCH,
        })

    return results


def search(query: str, store: str = None, top_k: int = 20) -> list[dict]:
    """
    Case-insensitive substring search on product names.

    This is the manual fallback when the model isn't confident, or when the user
    wants to browse a specific store's catalogue. Results are sorted by price.

    Args:
        query: substring to search for in product names
        store: optional store name to filter results (lowercase, e.g. 'aldi')
        top_k: maximum number of results to return
    """
    _load()
    mask = _catalogue["name"].str.contains(query, case=False, na=False, regex=False)
    if store:
        mask = mask & (_catalogue["store"] == store.lower())
    filtered = _catalogue[mask].copy()
    filtered = filtered.sort_values("price").head(top_k)

    results = []
    for _, row in filtered.iterrows():
        p100 = row.get("price_per_100")
        results.append({
            "name":          row["name"],
            "name_clean":    row.get("name_clean", row["name"]),
            "store":         row["store"],
            "price":         float(row["price"]),
            "price_per_100": float(p100) if pd.notna(p100) else None,
            "brand":         row.get("brand"),
            "query":         row.get("query"),
        })

    return results


def find_substitutes(
    product_name: str,
    store: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Find cheaper substitution candidates for a given product.

    A valid substitute must:
    - Be in the same product category (same 'query' value)
    - Cost less than the original
    - Have cosine similarity in (TAU_SUBSTITUTION, TAU_MATCH) —
      above the lower band (semantically relevant) but below the upper band
      (not an exact duplicate)

    Results are ranked by per-100g saving where available, otherwise by
    cosine similarity (descending).

    Each result dict:
        substitute_name, substitute_store, substitute_price, original_price,
        saving, saving_pct, cosine_similarity, saving_per_100
    """
    _load()

    product_name_clean = strip_store_prefix(product_name)

    # Find query product row in catalogue (match by original name + store)
    query_rows = _catalogue[
        (_catalogue["name"] == product_name) & (_catalogue["store"] == store)
    ]
    if len(query_rows) == 0:
        return []

    query_idx      = query_rows.index[0]
    query_row      = query_rows.iloc[0]
    query_price    = float(query_row["price"])
    query_category = query_row["query"]
    query_p100     = query_row.get("price_per_100")

    # Use the row index to look up the query embedding (row-aligned with _embeddings)
    if query_idx >= len(_embeddings):
        return []
    query_emb = _embeddings[int(query_idx)]

    # Vectorised filtering
    sims         = np.dot(_embeddings, query_emb)
    cat_mask     = (_catalogue["query"] == query_category).values
    price_mask   = (_catalogue["price"] < query_price).values
    self_mask    = ~(
        (_catalogue["name"] == product_name) & (_catalogue["store"] == store)
    ).values
    sim_mask     = (sims >= config.TAU_SUBSTITUTION) & (sims < config.TAU_MATCH)
    combined     = cat_mask & price_mask & self_mask & sim_mask

    candidate_indices = np.where(combined)[0]
    if len(candidate_indices) == 0:
        return []

    results = []
    for i in candidate_indices:
        row  = _catalogue.iloc[int(i)]
        sim  = float(sims[i])
        cand_p100 = row.get("price_per_100")
        saving_per_100 = None
        if (
            query_p100 is not None and cand_p100 is not None
            and pd.notna(query_p100) and pd.notna(cand_p100)
        ):
            try:
                saving_per_100 = round(float(query_p100) - float(cand_p100), 4)
            except (TypeError, ValueError):
                pass

        results.append({
            "substitute_name":  row["name"],
            "substitute_store": row["store"],
            "substitute_price": float(row["price"]),
            "original_price":   query_price,
            "saving":           round(query_price - float(row["price"]), 2),
            "saving_pct":       round(
                (query_price - float(row["price"])) / query_price * 100, 1
            ),
            "cosine_similarity": round(sim, 4),
            "saving_per_100":   saving_per_100,
        })

    if not results:
        return []

    df_res = pd.DataFrame(results)
    if df_res["saving_per_100"].notna().any():
        df_res = df_res.sort_values("saving_per_100", ascending=False)
    else:
        df_res = df_res.sort_values("cosine_similarity", ascending=False)

    return df_res.head(top_k).to_dict("records")
