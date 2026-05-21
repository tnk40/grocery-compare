"""
run_pipeline.py — Run the full production pipeline end-to-end.

Steps:
  1/4  preprocess  — Load raw store CSVs, clean, save all_products.csv
  2/4  pairs       — Generate training pairs, save training_pairs.csv
  3/4  train       — Fine-tune the sentence transformer, save model
  4/4  export      — Encode all products, save embeddings.npy + catalogue.csv

Usage:
    python run_pipeline.py             # full pipeline
    python run_pipeline.py --skip-train  # skip training (use existing model)
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import preprocess
from pairs import generate_pairs
from train import train_model
from export import export_embeddings

import config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full product-matching pipeline."
    )
    parser.add_argument(
        "--skip-train",
        action="store_true",
        help="Skip fine-tuning and use the existing model in MODEL_DIR.",
    )
    args = parser.parse_args()

    # ── STEP 1/4: Preprocess ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 1/4 — Preprocess")
    print("=" * 60)
    df = preprocess(
        raw_data_dir=config.RAW_DATA_DIR,
        output_dir=config.PROCESSED_DIR,
    )
    print(f"Preprocessed {len(df)} products.")

    # ── STEP 2/4: Generate pairs ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2/4 — Generate training pairs")
    print("=" * 60)
    pairs_df = generate_pairs(df, output_path=config.PAIRS_PATH)
    print(f"Generated {len(pairs_df)} training pairs.")

    # ── STEP 3/4: Train ──────────────────────────────────────────────────────
    if args.skip_train:
        print("\n" + "=" * 60)
        print("STEP 3/4 — Skipped (--skip-train flag set)")
        print("=" * 60)
        print(f"Using existing model at: {config.MODEL_DIR}")
    else:
        print("\n" + "=" * 60)
        print("STEP 3/4 — Fine-tune model")
        print("=" * 60)
        metrics = train_model(
            pairs_path=config.PAIRS_PATH,
            model_dir=config.MODEL_DIR,
        )
        print(
            f"Training complete: PR-AUC={metrics['pr_auc']:.3f}, "
            f"F1={metrics['best_f1']:.3f} @ τ={metrics['threshold']:.2f}"
        )

    # ── STEP 4/4: Export embeddings ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 4/4 — Export embeddings + catalogue")
    print("=" * 60)
    export_embeddings(
        model_dir=config.MODEL_DIR,
        products_path=config.PRODUCTS_PATH,
        embeddings_path=config.EMBEDDINGS_PATH,
        catalogue_path=config.CATALOGUE_PATH,
    )

    print("\n" + "=" * 60)
    print("Pipeline complete.")
    print("=" * 60)
    print(f"  Model:       {config.MODEL_DIR}")
    print(f"  Embeddings:  {config.EMBEDDINGS_PATH}")
    print(f"  Catalogue:   {config.CATALOGUE_PATH}")
    print(f"  Pairs CSV:   {config.PAIRS_PATH}")
    print("Ready to serve — run test_pipeline.py to validate.")


if __name__ == "__main__":
    main()
