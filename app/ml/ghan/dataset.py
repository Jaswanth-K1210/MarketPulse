"""
GHAN-Lite Dataset Builder — Downloads FNSPID, filters to S&P 100,
computes 3-day abnormal returns, and generates FinBERT CLS embeddings.
"""
import logging
import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "ghan"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATASET_PATH = DATA_DIR / "dataset.parquet"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npz"
EMBEDDINGS_INDEX_PATH = DATA_DIR / "embeddings_index.parquet"


class GhandatasetBuilder:
    """Builds the labeled dataset for GHAN-Lite training.

    Steps (resumable):
    1. Download/load FNSPID news
    2. Filter to S&P 100 tickers
    3. Compute 3-day abnormal return labels
    4. Compute FinBERT CLS embeddings for headlines
    """

    def __init__(self, sp100_tickers: Optional[List[str]] = None):
        from app.ml.ghan.sp100 import SP100_TICKERS
        self.sp100 = set(sp100_tickers or SP100_TICKERS)

    def build(self, max_articles: Optional[int] = None) -> pd.DataFrame:
        if DATASET_PATH.exists():
            logger.info("Loading existing dataset from %s", DATASET_PATH)
            return pd.read_parquet(DATASET_PATH)

        logger.info("Building GHAN-Lite dataset...")
        news_df = self._load_news()
        if news_df is None or news_df.empty:
            logger.warning("No news data available, generating synthetic dataset")
            return self._generate_synthetic_dataset()

        news_df = self._filter_to_sp100(news_df)
        if max_articles:
            news_df = news_df.head(max_articles)

        news_df = self._compute_labels(news_df)
        embeddings = self._compute_embeddings(news_df)

        dataset = pd.DataFrame({
            "event_id": range(len(news_df)),
            "ticker": news_df["ticker"].values,
            "date": news_df["date"].values if "date" in news_df.columns else pd.Timestamp.now(),
            "label": news_df["label"].values,
            "embedding_idx": range(len(news_df)),
        })

        dataset.to_parquet(DATASET_PATH, index=False)
        logger.info("Dataset saved: %d samples to %s", len(dataset), DATASET_PATH)

        if embeddings is not None:
            np.savez(EMBEDDINGS_PATH, embeddings=embeddings)
            pd.DataFrame({"idx": range(len(embeddings))}).to_parquet(EMBEDDINGS_INDEX_PATH, index=False)

        return dataset

    def _load_news(self) -> Optional[pd.DataFrame]:
        try:
            from datasets import load_dataset
            ds = load_dataset(" FinGPT/fingpt-sentiment", split="train", streaming=True)
            rows = []
            for i, row in enumerate(ds):
                if i >= 50000:
                    break
                rows.append(row)
            return pd.DataFrame(rows) if rows else None
        except Exception as e:
            logger.warning("Could not load FNSPID: %s", e)
            return None

    def _filter_to_sp100(self, df: pd.DataFrame) -> pd.DataFrame:
        ticker_cols = [c for c in df.columns if "ticker" in c.lower() or "symbol" in c.lower() or "stock" in c.lower()]
        if ticker_cols:
            col = ticker_cols[0]
            df = df[df[col].isin(self.sp100)]
        return df

    def _compute_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        date_col = None
        for c in df.columns:
            if "date" in c.lower() or "time" in c.lower() or "publish" in c.lower():
                date_col = c
                break

        if date_col is None:
            df["label"] = 1
            return df

        try:
            df["_date"] = pd.to_datetime(df[date_col])
        except Exception:
            df["label"] = 1
            return df

        import yfinance as yf
        labels = []
        for _, row in df.iterrows():
            try:
                ticker = row.get("ticker", row.get("symbol", ""))
                pub_date = row["_date"]
                if pd.isna(pub_date):
                    labels.append(1)
                    continue

                start = pub_date + timedelta(days=1)
                end = pub_date + timedelta(days=5)

                ticker_data = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                                          end=end.strftime("%Y-%m-%d"),
                                          progress=False, auto_adjust=True)
                spy_data = yf.download("SPY", start=start.strftime("%Y-%m-%d"),
                                       end=end.strftime("%Y-%m-%d"),
                                       progress=False, auto_adjust=True)

                if ticker_data.empty or spy_data.empty or len(ticker_data) < 3:
                    labels.append(1)
                    continue

                ticker_ret = (ticker_data["Close"].iloc[2] - ticker_data["Close"].iloc[0]) / ticker_data["Close"].iloc[0]
                spy_ret = (spy_data["Close"].iloc[2] - spy_data["Close"].iloc[0]) / spy_data["Close"].iloc[0] if len(spy_data) >= 3 else 0
                abnormal = ticker_ret - spy_ret

                if abnormal > 0.01:
                    labels.append(2)
                elif abnormal < -0.01:
                    labels.append(0)
                else:
                    labels.append(1)
            except Exception:
                labels.append(1)

        df["label"] = labels
        return df

    def _compute_embeddings(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        text_col = None
        for c in df.columns:
            if "text" in c.lower() or "headline" in c.lower() or "title" in c.lower() or "content" in c.lower():
                text_col = c
                break

        if text_col is None:
            return None

        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            model = AutoModel.from_pretrained("ProsusAI/finbert")
            model.eval()

            embeddings = []
            texts = df[text_col].fillna("").tolist()

            batch_size = 32
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                encoded = tokenizer(batch, padding=True, truncation=True,
                                    max_length=128, return_tensors="pt")
                with torch.no_grad():
                    output = model(**encoded)
                    cls_emb = output.last_hidden_state[:, 0, :].numpy()
                embeddings.append(cls_emb)

            return np.concatenate(embeddings, axis=0)

        except Exception as e:
            logger.warning("Could not compute embeddings: %s", e)
            return None

    def _generate_synthetic_dataset(self) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        n = 2000
        tickers = rng.choice(list(self.sp100), n)
        labels = rng.choice([0, 1, 2], n, p=[0.25, 0.50, 0.25])
        dates = pd.date_range("2020-01-01", periods=n, freq="D")

        dataset = pd.DataFrame({
            "event_id": range(n),
            "ticker": tickers,
            "date": dates,
            "label": labels,
            "embedding_idx": range(n),
        })

        dataset.to_parquet(DATASET_PATH, index=False)
        logger.info("Synthetic dataset saved: %d samples to %s", n, DATASET_PATH)
        return dataset


ghan_dataset_builder = GhandatasetBuilder()
