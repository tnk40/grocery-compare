"""
train.py — Fine-tune all-MiniLM-L6-v2 on product-matching pairs.

Uses ContrastiveLoss with margin=1.0 (config.CONTRASTIVE_MARGIN).
Trains ONE model with ONE configuration — no sweeps, no ablations.

Run standalone:  python train.py
Import:          from train import train_model
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import torch

from datasets import Dataset
from sentence_transformers import SentenceTransformer, losses
from sentence_transformers.evaluation import BinaryClassificationEvaluator
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments
from sklearn.metrics import average_precision_score, f1_score
from sklearn.model_selection import train_test_split

import config


def _make_hf_dataset(df: pd.DataFrame) -> Dataset:
    """Convert a pairs DataFrame to a HuggingFace Dataset for SentenceTransformerTrainer."""
    return Dataset.from_dict({
        "sentence1": df["name_a"].fillna("").astype(str).tolist(),
        "sentence2": df["name_b"].fillna("").astype(str).tolist(),
        "label":     df["label"].astype(float).tolist(),
    })


def train_model(
    pairs_path: str = config.PAIRS_PATH,
    model_dir: str  = config.MODEL_DIR,
) -> dict:
    """
    Fine-tune the sentence transformer on product-matching pairs.

    Steps:
    1. Load pairs from CSV
    2. Stratified 80/20 train/test split
    3. Build HuggingFace Datasets
    4. Load base model (all-MiniLM-L6-v2)
    5. Create ContrastiveLoss with margin=1.0
    6. Create BinaryClassificationEvaluator on test split
    7. Train with SentenceTransformerTrainer
    8. Save model to model_dir
    9. Evaluate on test split and return metrics

    Returns dict with keys: pr_auc, best_f1, threshold.
    """
    os.makedirs(model_dir, exist_ok=True)

    # ── Load pairs ───────────────────────────────────────────────────────────
    pairs_df = pd.read_csv(pairs_path)
    print(f"Loaded {len(pairs_df)} pairs from {pairs_path}")
    print(f"  Positive: {(pairs_df['label'] == 1).sum()}")
    print(f"  Negative: {(pairs_df['label'] == 0).sum()}")

    # ── Stratified train/test split ──────────────────────────────────────────
    train_df, test_df = train_test_split(
        pairs_df,
        test_size=0.2,
        random_state=config.RANDOM_SEED,
        stratify=pairs_df["label"],
    )
    print(f"\nTrain: {len(train_df)} | Test: {len(test_df)}")

    train_dataset = _make_hf_dataset(train_df)
    test_dataset  = _make_hf_dataset(test_df)

    # ── Device detection ─────────────────────────────────────────────────────
    device = (
        "cuda" if torch.cuda.is_available()
        else "mps" if torch.backends.mps.is_available()
        else "cpu"
    )
    print(f"Device: {device}")

    # ── Model + loss ─────────────────────────────────────────────────────────
    model = SentenceTransformer(config.BASE_MODEL)

    train_loss = losses.ContrastiveLoss(
        model=model,
        margin=config.CONTRASTIVE_MARGIN,
        distance_metric=losses.SiameseDistanceMetric.EUCLIDEAN,
    )

    # ── Evaluator ────────────────────────────────────────────────────────────
    evaluator = BinaryClassificationEvaluator(
        sentences1=test_df["name_a"].fillna("").astype(str).tolist(),
        sentences2=test_df["name_b"].fillna("").astype(str).tolist(),
        labels=test_df["label"].astype(int).tolist(),
        name="grocery-matching",
        show_progress_bar=False,
    )

    # ── Training arguments ───────────────────────────────────────────────────
    training_args = SentenceTransformerTrainingArguments(
        output_dir=model_dir,
        num_train_epochs=config.NUM_EPOCHS,
        per_device_train_batch_size=config.BATCH_SIZE,
        per_device_eval_batch_size=config.BATCH_SIZE,
        learning_rate=config.LEARNING_RATE,
        warmup_ratio=config.WARMUP_RATIO,
        fp16=(device == "cuda"),
        eval_strategy="epoch",
        save_strategy="no",
        logging_steps=50,
        report_to="none",
    )

    trainer = SentenceTransformerTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        loss=train_loss,
        evaluator=evaluator,
    )

    print(f"\nStarting fine-tuning: {config.NUM_EPOCHS} epochs, "
          f"margin={config.CONTRASTIVE_MARGIN}, lr={config.LEARNING_RATE} …")
    trainer.train()

    # ── Save model ───────────────────────────────────────────────────────────
    model.save(model_dir)
    print(f"\nModel saved to {model_dir}")

    # ── Final evaluation ─────────────────────────────────────────────────────
    print("\nEvaluating on test split …")
    names_a = test_df["name_a"].fillna("").astype(str).tolist()
    names_b = test_df["name_b"].fillna("").astype(str).tolist()
    y_true  = test_df["label"].values

    emb_a = model.encode(names_a, batch_size=64, normalize_embeddings=True,
                         convert_to_numpy=True, show_progress_bar=False)
    emb_b = model.encode(names_b, batch_size=64, normalize_embeddings=True,
                         convert_to_numpy=True, show_progress_bar=False)
    sims = (emb_a * emb_b).sum(axis=1)

    pr_auc = float(average_precision_score(y_true, sims))

    thresholds   = np.arange(0.0, 1.01, 0.01)
    best_f1      = 0.0
    best_thresh  = 0.5
    for tau in thresholds:
        preds = (sims >= tau).astype(int)
        if preds.sum() == 0:
            continue
        f1 = f1_score(y_true, preds, zero_division=0)
        if f1 > best_f1:
            best_f1, best_thresh = f1, float(tau)

    print(f"\nFinal metrics on test split:")
    print(f"  PR-AUC:    {pr_auc:.4f}")
    print(f"  Best F1:   {best_f1:.4f}  at threshold {best_thresh:.2f}")

    return {"pr_auc": pr_auc, "best_f1": best_f1, "threshold": best_thresh}


if __name__ == "__main__":
    metrics = train_model()
    print(f"\nTraining complete: PR-AUC={metrics['pr_auc']:.3f}, "
          f"F1={metrics['best_f1']:.3f} @ τ={metrics['threshold']:.2f}")
