"""
GHAN-Lite Graph Builder — Star expansion of hyperedges for bipartite
ticker↔event graph. Reuses MarketPulse supply-chain relationships.
"""
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class GhanGraphBuilder:
    """Builds bipartite graphs from event-ticker pairs with supply-chain expansion.

    Star expansion: each event becomes a virtual event node connected to:
    (a) its directly mentioned tickers
    (b) their first-degree supply-chain neighbors
    """

    def __init__(self, ticker_dim: int = 64, event_dim: int = 768):
        self.ticker_dim = ticker_dim
        self.event_dim = event_dim
        self._ticker_vocab: Dict[str, int] = {}
        self._supply_chain: Dict[str, List[str]] = {}

    def load_supply_chain(self):
        """Load supply-chain relationships from the database."""
        try:
            from app.services.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT source_ticker, target_ticker FROM relationships")
            for row in cursor.fetchall():
                src, tgt = row[0], row[1]
                if src not in self._supply_chain:
                    self._supply_chain[src] = []
                self._supply_chain[src].append(tgt)
                if tgt not in self._supply_chain:
                    self._supply_chain[tgt] = []
                self._supply_chain[tgt].append(src)
            conn.close()
            logger.info("Loaded supply chain: %d tickers with connections", len(self._supply_chain))
        except Exception as e:
            logger.warning("Could not load supply chain: %s", e)

    def build_ticker_vocab(self, tickers: List[str]):
        self._ticker_vocab = {t: i for i, t in enumerate(sorted(set(tickers)))}

    def build_graph(
        self,
        event_tickers: List[List[str]],
        event_embeddings: np.ndarray,
        labels: np.ndarray,
    ) -> Dict:
        if not self._supply_chain:
            self.load_supply_chain()

        all_tickers = set()
        for tickers in event_tickers:
            all_tickers.update(tickers)
            for t in tickers:
                all_tickers.update(self._supply_chain.get(t, []))

        self.build_ticker_vocab(list(all_tickers))

        n_tickers = len(self._ticker_vocab)
        n_events = len(event_tickers)

        edges = []
        edge_attrs = []

        for event_idx, tickers in enumerate(event_tickers):
            event_neighbors = set()
            for t in tickers:
                event_neighbors.add(t)
                for neighbor in self._supply_chain.get(t, []):
                    event_neighbors.add(neighbor)

            for t in event_neighbors:
                if t in self._ticker_vocab:
                    ticker_idx = self._ticker_vocab[t]
                    edges.append((event_idx + n_tickers, ticker_idx))
                    edges.append((ticker_idx, event_idx + n_tickers))

        edge_index = np.array(edges, dtype=np.int64).T if edges else np.zeros((2, 0), dtype=np.int64)

        ticker_embeddings = np.random.randn(n_tickers, self.ticker_dim).astype(np.float32) * 0.1
        event_proj = np.random.randn(self.event_dim, self.ticker_dim).astype(np.float32) * 0.1
        if event_embeddings.shape[1] == self.event_dim:
            event_embeddings_proj = event_embeddings @ event_proj
        else:
            event_embeddings_proj = event_embeddings[:, :self.ticker_dim]

        x = np.zeros((n_tickers + n_events, self.ticker_dim), dtype=np.float32)
        x[:n_tickers] = ticker_embeddings
        x[n_tickers:] = event_embeddings_proj

        return {
            "edge_index": edge_index,
            "x": x,
            "labels": labels,
            "n_tickers": n_tickers,
            "n_events": n_events,
            "ticker_vocab": self._ticker_vocab,
        }


ghan_graph_builder = GhanGraphBuilder()
