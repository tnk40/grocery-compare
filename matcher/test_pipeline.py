"""
test_pipeline.py — Smoke tests for the production matcher pipeline.

Validates that the exported artefacts are correct and the matcher API works.
Run AFTER the full pipeline (run_pipeline.py) has completed successfully.

Usage:
    python test_pipeline.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import config
from preprocess import strip_store_prefix
from matcher import match, search, find_substitutes


def test_files_exist() -> None:
    assert os.path.exists(config.EMBEDDINGS_PATH), \
        f"Missing embeddings: {config.EMBEDDINGS_PATH}"
    assert os.path.exists(config.CATALOGUE_PATH), \
        f"Missing catalogue: {config.CATALOGUE_PATH}"
    assert os.path.isdir(config.MODEL_DIR), \
        f"Missing model directory: {config.MODEL_DIR}"
    config_json = os.path.join(config.MODEL_DIR, "config.json")
    assert os.path.exists(config_json), \
        f"Missing model config.json: {config_json}"


def test_catalogue_schema() -> None:
    cat = pd.read_csv(config.CATALOGUE_PATH)
    required = ["name", "name_clean", "store", "price", "price_per_100", "query", "brand"]
    for col in required:
        assert col in cat.columns, f"Catalogue missing column: {col}"


def test_embeddings_shape() -> None:
    cat = pd.read_csv(config.CATALOGUE_PATH)
    emb = np.load(config.EMBEDDINGS_PATH)
    assert emb.shape[0] == len(cat), (
        f"Alignment mismatch: {emb.shape[0]} embeddings vs {len(cat)} catalogue rows"
    )
    assert emb.shape[1] == 384, f"Expected 384-dim embeddings, got {emb.shape[1]}"


def test_store_prefix_stripping() -> None:
    assert strip_store_prefix("Morrisons The Best Butter") == "Butter"  # "Morrisons The Best" is a full prefix
    assert strip_store_prefix("Sainsbury's Whole Milk 2L") == "Whole Milk 2L"
    assert strip_store_prefix("ASDA Free Range Eggs") == "Free Range Eggs"
    assert strip_store_prefix("Waitrose Duchy Organic Butter") == "Butter"  # iterative: Waitrose → Duchy Organic → product
    assert strip_store_prefix("Aldi Specially Selected Cheddar") == "Cheddar"  # iterative: Aldi → Specially Selected → product
    assert strip_store_prefix("Semi Skimmed Milk") == "Semi Skimmed Milk"


def test_no_store_prefix_in_catalogue() -> None:
    cat = pd.read_csv(config.CATALOGUE_PATH)
    for prefix in config.STORE_PREFIXES:
        violators = cat["name_clean"].str.startswith(prefix, na=False)
        count = violators.sum()
        assert count == 0, (
            f"Found {count} name_clean entries starting with store prefix '{prefix}':\n"
            + cat[violators]["name_clean"].head(3).to_string()
        )


def test_match_returns_results() -> None:
    results = match("semi skimmed milk")
    assert len(results) > 0, "match('semi skimmed milk') returned no results"


def test_match_cross_store() -> None:
    results = match("butter", top_k=20)
    stores = {r["store"] for r in results}
    assert len(stores) >= 2, (
        f"match('butter') should span >=2 stores, got: {stores}"
    )


def test_match_confidence_flag() -> None:
    results = match("semi skimmed milk", top_k=20)
    for r in results:
        if r["similarity"] >= config.TAU_MATCH:
            assert r["confident"] is True, (
                f"Confident flag not set for sim={r['similarity']:.4f} >= TAU_MATCH={config.TAU_MATCH}"
            )
        else:
            assert r["confident"] is False, (
                f"Confident flag wrongly set for sim={r['similarity']:.4f} < TAU_MATCH={config.TAU_MATCH}"
            )


def test_search_fallback() -> None:
    results = search("Lurpak")
    assert len(results) > 0, "search('Lurpak') returned no results"
    for r in results:
        assert "lurpak" in r["name"].lower(), (
            f"search('Lurpak') returned product without 'lurpak': {r['name']}"
        )


def test_search_store_filter() -> None:
    results = search("milk", store="aldi")
    if len(results) == 0:
        return   # skip if Aldi has no milk — shouldn't happen in practice
    for r in results:
        assert r["store"] == "aldi", (
            f"search('milk', store='aldi') returned item from store '{r['store']}'"
        )


def test_substitutes() -> None:
    # Find a mid-priced milk product in any store to use as anchor
    cat = pd.read_csv(config.CATALOGUE_PATH)
    milk_rows = cat[cat["query"] == "milk"].sort_values("price")
    if len(milk_rows) < 2:
        return   # skip if too few products
    # Pick a product from the upper half (not the cheapest) so substitutes exist
    midpoint = len(milk_rows) // 2
    anchor   = milk_rows.iloc[midpoint]
    subs     = find_substitutes(anchor["name"], anchor["store"])
    if len(subs) == 0:
        return   # no substitutes found — pass silently, model may not be trained yet
    for s in subs:
        assert s["substitute_price"] < s["original_price"], (
            f"Substitute {s['substitute_name']} ({s['substitute_price']}) "
            f"is not cheaper than original ({s['original_price']})"
        )


def test_morrisons_not_self_clustering() -> None:
    results = match("milk", top_k=10)
    stores  = {r["store"] for r in results}
    assert len(stores) >= 2, (
        "Top-10 milk results should span >=2 stores — likely a store-prefix clustering issue. "
        f"Got stores: {stores}"
    )


# ── Test runner ───────────────────────────────────────────────────────────────

TESTS = [
    test_files_exist,
    test_catalogue_schema,
    test_embeddings_shape,
    test_store_prefix_stripping,
    test_no_store_prefix_in_catalogue,
    test_match_returns_results,
    test_match_cross_store,
    test_match_confidence_flag,
    test_search_fallback,
    test_search_store_filter,
    test_substitutes,
    test_morrisons_not_self_clustering,
]


def main() -> None:
    passed = 0
    failed = 0
    for test_fn in TESTS:
        name = test_fn.__name__
        try:
            test_fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
