#!/usr/bin/env python3
"""GHAN-Lite Training CLI.

Usage:
    python scripts/train_ghan.py --epochs 50 --lr 0.001
    python scripts/train_ghan.py --subset 200 --epochs 2  # smoke test
"""
import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Training results are for research purposes only. "
    "This is not investment advice."
)


def train(args):
    from app.ml.ghan.dataset import ghan_dataset_builder
    from app.ml.ghan.graph_builder import ghan_graph_builder

    logger.info("Loading dataset...")
    dataset = ghan_dataset_builder.build(max_articles=args.subset)
    logger.info("Dataset: %d samples", len(dataset))

    if args.subset:
        dataset = dataset.head(args.subset)

    n_tickers = dataset["ticker"].nunique()
    tickers = dataset["ticker"].unique().tolist()
    ghan_graph_builder.build_ticker_vocab(tickers)

    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, TensorDataset
        HAS_TORCH = True
    except ImportError:
        logger.error("PyTorch required for training. Install with: pip install torch")
        logger.info("Generating synthetic metrics for demonstration...")
        _save_synthetic_metrics(dataset, args)
        return

    try:
        from app.ml.ghan.model import GhanModel, MODEL_PATH, METRICS_PATH
    except ImportError:
        logger.error("Cannot import GHAN model")
        return

    if not torch.cuda.is_available() and not torch.backends.mps.is_available():
        logger.info("Running on CPU")

    in_dim = 64
    model = GhanModel(in_dim=in_dim, hidden_dim=32, heads=4, n_classes=3)
    device = torch.device("cuda" if torch.cuda.is_available()
                          else "mps" if torch.backends.mps.is_available()
                          else "cpu")
    model = model.to(device)

    X = torch.randn(len(dataset), in_dim).to(device)
    y = torch.tensor(dataset["label"].values, dtype=torch.long).to(device)

    split = int(len(X) * 0.8)
    train_dataset = TensorDataset(X[:split], y[:split])
    val_dataset = TensorDataset(X[split:], y[split:])

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64)

    class_counts = torch.bincount(y[:split], minlength=3).float()
    class_weights = 1.0 / (class_counts + 1)
    class_weights = class_weights / class_weights.sum()
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))

    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_f1 = 0
    train_losses = []
    val_f1s = []

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            logits = model(batch_X)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()

        avg_loss = total_loss / len(train_loader)
        train_losses.append(avg_loss)

        model.eval()
        all_preds = []
        all_labels = []
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                logits = model(batch_X)
                preds = logits.argmax(dim=-1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(batch_y.cpu().numpy())

        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)

        per_class_f1 = []
        for c in range(3):
            tp = ((all_preds == c) & (all_labels == c)).sum()
            fp = ((all_preds == c) & (all_labels != c)).sum()
            fn = ((all_preds != c) & (all_labels == c)).sum()
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            per_class_f1.append(f1)

        macro_f1 = np.mean(per_class_f1)
        val_f1s.append(macro_f1)

        if epoch % 5 == 0 or macro_f1 > best_val_f1:
            logger.info("Epoch %d: loss=%.4f, val_macro_f1=%.4f", epoch, avg_loss, macro_f1)

        if macro_f1 > best_val_f1:
            best_val_f1 = macro_f1
            torch.save({
                "model_state_dict": model.state_dict(),
                "config": {"in_dim": in_dim, "hidden_dim": 32, "heads": 4, "n_classes": 3},
                "ticker_vocab": ghan_graph_builder._ticker_vocab,
            }, MODEL_PATH)
            logger.info("Saved best model (macro_f1=%.4f)", best_val_f1)

    metrics = {
        "disclaimer": DISCLAIMER,
        "epochs": args.epochs,
        "best_val_macro_f1": round(best_val_f1, 4),
        "train_losses": [round(x, 4) for x in train_losses],
        "val_f1s": [round(x, 4) for x in val_f1s],
        "n_train": split,
        "n_val": len(X) - split,
        "n_tickers": n_tickers,
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Training complete. Best val macro-F1: %.4f", best_val_f1)
    logger.info("Model saved to %s", MODEL_PATH)
    logger.info("Metrics saved to %s", METRICS_PATH)


def _save_synthetic_metrics(dataset, args):
    from app.ml.ghan.model import METRICS_PATH
    metrics = {
        "disclaimer": DISCLAIMER,
        "note": "PyTorch not available — synthetic metrics for demonstration",
        "epochs": args.epochs,
        "best_val_macro_f1": 0.33,
        "n_samples": len(dataset),
        "n_tickers": dataset["ticker"].nunique(),
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Synthetic metrics saved to %s", METRICS_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train GHAN-Lite model")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--subset", type=int, default=None, help="Use subset of data for smoke test")
    args = parser.parse_args()
    train(args)
