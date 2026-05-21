# matcher

Production Python package for semantic grocery product matching.

Fine-tunes a `sentence-transformers` (`all-MiniLM-L6-v2`) model on cross-store
product pairs to learn a price-aware embedding space. At inference time, a
free-text query is encoded and matched against a pre-built embedding index of
all products using cosine similarity. The package exposes three functions:
`match()` for semantic cross-store lookup, `search()` for exact substring
browse, and `find_substitutes()` for recommending cheaper alternatives within
the same product category.

---

## Prerequisites

- Python 3.10+
- Raw store CSV files in `data/` (see `config.py` for expected filenames)

Install dependencies:

```bash
pip install -r matcher/requirements.txt
```

---

## Run the full pipeline

```bash
# From the project root
python matcher/run_pipeline.py
```

This runs four steps in sequence:

| Step | Script | Output |
|------|--------|--------|
| 1/4 Preprocess | `preprocess.py` | `data/processed/all_products.csv` |
| 2/4 Pairs | `pairs.py` | `data/processed/training_pairs.csv` |
| 3/4 Train | `train.py` | `models/product_matcher/` |
| 4/4 Export | `export.py` | `data/processed/embeddings.npy`, `data/processed/catalogue.csv` |

To skip training and use the existing model (e.g., after adding new store data):

```bash
python matcher/run_pipeline.py --skip-train
```

---

## Validate the pipeline output

```bash
python matcher/test_pipeline.py
```

Runs 12 smoke tests covering artefact existence, schema, embedding alignment,
store-prefix stripping, and all three API functions.

---

## Import from the website backend (FastAPI / Railway)

```python
from matcher.matcher import match, search, find_substitutes

# Semantic cross-store search
results = match("semi skimmed milk", top_k=5)
# [{'name': ..., 'store': ..., 'price': ..., 'similarity': 0.91, 'confident': True}, ...]

# Substring browse with optional store filter
results = search("Lurpak", store="aldi")

# Cheaper same-category alternatives
subs = find_substitutes("Morrisons British Whole Milk 4 Pints", store="morrisons", top_k=5)
```

The model and embeddings are loaded **lazily** on the first call, so the
FastAPI app starts immediately without blocking on disk I/O.

---

## Configuration

All constants and file paths are in `matcher/config.py`. Key values:

| Constant | Value | Meaning |
|----------|-------|---------|
| `TAU_MATCH` | 0.85 | Cosine similarity threshold for "confident" match |
| `TAU_SUBSTITUTION` | 0.50 | Minimum similarity for substitute candidates |
| `CONTRASTIVE_MARGIN` | 1.0 | ContrastiveLoss margin during fine-tuning |
| `BASE_MODEL` | `all-MiniLM-L6-v2` | Backbone sentence transformer |
