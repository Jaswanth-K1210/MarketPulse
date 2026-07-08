"""
Supply-Chain GNN (Graph Neural Network) Service
================================================
Implements message-passing shock propagation through a weighted supply-chain graph.

Architecture:
  - Static graph: hardcoded real-world edges (supplier → customer, competitor pairs)
  - Message passing: multi-hop propagation with edge-weight attenuation
  - Each hop attenuates the shock by DECAY_FACTOR
  - Negative edges = competitor relationship (inverted shock direction)

For training a full PyTorch Geometric GNN on Colab:
  See docs/gnn_training_colab.md (train once, download weights, load here for inference).
  This module works standalone without PyG; PyG weights can be loaded via load_weights().
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Supply-chain edge table ───────────────────────────────────────────────────
# (source, target, weight)
# weight > 0  → supplier / dependency  (shock flows downstream)
# weight < 0  → competitor            (shock inverts: negative news for one = positive for other)
_EDGES: List[Tuple[str, str, float]] = [
    # Semiconductor foundry
    ("TSM",  "AAPL",  0.85),   # TSMC → Apple (primary SoC)
    ("TSM",  "NVDA",  0.90),   # TSMC → Nvidia (dominant fab)
    ("TSM",  "AMD",   0.80),   # TSMC → AMD
    ("TSM",  "QCOM",  0.75),   # TSMC → Qualcomm
    ("TSM",  "AVGO",  0.65),   # TSMC → Broadcom
    ("TSM",  "MRVL",  0.60),
    # Lithography monopoly
    ("ASML", "TSM",   0.95),   # ASML EUV → TSMC
    ("ASML", "INTC",  0.88),
    ("ASML", "SSNLF", 0.82),   # Samsung
    # CPU / GPU competition
    ("INTC", "AMD",  -0.60),   # Competitors
    ("AMD",  "NVDA", -0.45),   # GPU competitors
    ("INTC", "NVDA", -0.30),
    # AI compute ecosystem
    ("NVDA", "MSFT",  0.50),   # Azure H100 dependency
    ("NVDA", "META",  0.55),   # Meta AI infra
    ("NVDA", "GOOGL", 0.45),
    ("NVDA", "AMZN",  0.45),
    ("NVDA", "ORCL",  0.40),
    # Apple supply chain
    ("AAPL", "QCOM",  0.55),   # Modem supplier
    ("AAPL", "AVGO",  0.60),   # Wi-Fi / RF chips
    ("AAPL", "SNPS",  0.40),
    # Cloud / hyperscaler competition
    ("MSFT", "GOOGL", -0.35),
    ("AMZN", "MSFT",  -0.30),
    ("GOOGL","META",  -0.25),
    # Aerospace & defence
    ("BA",   "GE",    0.60),   # GE engines on Boeing planes
    ("BA",   "RTX",   0.55),   # Raytheon avionics
    ("BA",   "SPR",   0.80),   # Spirit AeroSystems (fuselage)
    ("RTX",  "GE",   -0.40),   # Defence competitors
    # Energy
    ("XOM",  "CVX",  -0.40),
    ("XOM",  "COP",  -0.35),
    # Automotive / EV
    ("TSLA", "PANASONIC", 0.65),  # Battery supplier
    ("TSLA", "TM",   -0.50),   # Toyota competitor
    # Memory
    ("MU",   "AAPL",  0.40),
    ("MU",   "NVDA",  0.35),
    ("MU",   "TSM",   0.30),
    # Networking
    ("CSCO", "MSFT",  0.35),
    ("CSCO", "AMZN",  0.30),
]

# ── Graph construction ────────────────────────────────────────────────────────

def _build_adj(edges: List[Tuple[str, str, float]]) -> Dict[str, List[Tuple[str, float]]]:
    """
    Build bidirectional adjacency list.
    Forward edges use the full weight; reverse edges use 0.25× (upstream is less affected).
    Negative (competitor) edges propagate in reverse direction.
    """
    adj: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for src, tgt, w in edges:
        adj[src].append((tgt,  w))
        # Upstream exposure: if a customer has bad news, supplier feels ~25% of the impact
        adj[tgt].append((src,  w * 0.25 if w > 0 else w * 0.15))
    return dict(adj)


_ADJ = _build_adj(_EDGES)
_ALL_NODES = list({n for e in _EDGES for n in e[:2]})

# ── PyTorch Geometric optional layer ─────────────────────────────────────────

_pyg_model   = None
_pyg_weights = None


def load_weights(path: str):
    """
    Load trained GNN weights from a file produced on Colab.
    File format: torch.save({'node_embed': ..., 'linear': ...}, path)
    When weights are loaded, propagate_shock() uses them to adjust raw propagation scores.
    """
    global _pyg_model, _pyg_weights
    try:
        import torch
        _pyg_weights = torch.load(path, map_location="cpu")
        logger.info("GNN weights loaded from %s", path)
    except Exception as exc:
        logger.warning("Could not load GNN weights: %s", exc)


# ── Core message-passing engine ───────────────────────────────────────────────

DECAY        = 0.55    # each hop attenuates shock by this factor
MIN_IMPACT   = 0.005   # prune negligible impacts
PRICE_SCALE  = 0.15    # FinBERT score ±1.0 → max direct price impact ±15 %
                       # Empirically: TSMC halt → AAPL ~-10-15 %, NVDA ~-12-18 %


def propagate_shock(
    shocked_ticker: str,
    shock_score: float,   # FinBERT score: -1 .. +1
    depth: int = 3,
) -> Dict[str, float]:
    """
    Propagate a sentiment shock from shocked_ticker through the supply-chain graph.

    Returns: {ticker: impact_score}  (same range as shock_score, attenuated by hops)
    Positive shock_score (good news) → customers / dependents also improve.
    Negative shock_score (bad news)  → same.
    Competitor edges invert the sign.
    """
    visited: Dict[str, float] = {shocked_ticker: shock_score}
    queue   = [(shocked_ticker, shock_score, 0)]

    while queue:
        node, current_score, level = queue.pop(0)
        if level >= depth:
            continue

        for neighbor, weight in _ADJ.get(node, []):
            propagated = current_score * weight * (DECAY ** level)
            if abs(propagated) < MIN_IMPACT:
                continue

            if neighbor in visited:
                # Keep the larger-magnitude impact
                if abs(propagated) > abs(visited[neighbor]):
                    visited[neighbor] = propagated
            else:
                visited[neighbor] = propagated
                queue.append((neighbor, propagated, level + 1))

    # Remove source — we return ONLY affected neighbours
    visited.pop(shocked_ticker, None)

    # Optional PyG weight adjustment
    if _pyg_weights is not None:
        try:
            import torch, numpy as np
            # Multiply raw scores by learned node importance if available
            embed = _pyg_weights.get("node_embed")
            if embed is not None:
                node_list = _pyg_weights.get("node_list", _ALL_NODES)
                idx_map   = {n: i for i, n in enumerate(node_list)}
                for ticker in list(visited):
                    i = idx_map.get(ticker)
                    if i is not None:
                        scale          = float(torch.sigmoid(embed[i]).mean())
                        visited[ticker] = visited[ticker] * (0.5 + scale)
        except Exception:
            pass

    return {t: round(s, 4) for t, s in visited.items()}


def get_portfolio_impact(
    portfolio: List[str],
    shocked_ticker: str,
    shock_score: float,
    current_prices: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    High-level call: propagate a shock and summarise impact on a specific portfolio.
    Returns a structured dict consumed by Agent 4 and the Monte Carlo service.
    """
    all_impacts = propagate_shock(shocked_ticker, shock_score)

    # Include the shocked ticker itself if it is in the portfolio
    if shocked_ticker in portfolio:
        all_impacts[shocked_ticker] = shock_score

    port_impacts: Dict[str, float] = {t: all_impacts[t] for t in portfolio if t in all_impacts}

    # Weighted average impact (equal-weight portfolio for now)
    n      = max(len(portfolio), 1)
    avg    = sum(port_impacts.values()) / n

    # Dollar impact estimate (if prices are provided)
    dollar_impact = {}
    if current_prices:
        for ticker, score in port_impacts.items():
            px = current_prices.get(ticker, 0)
            dollar_impact[ticker] = round(px * score, 2)

    return {
        "shocked_ticker":        shocked_ticker,
        "shock_score":           round(shock_score, 4),
        "shock_label":           "negative" if shock_score < -0.1 else "positive" if shock_score > 0.1 else "neutral",
        "portfolio_impacts":     {t: round(v * 100 * PRICE_SCALE, 2) for t, v in port_impacts.items()},
        "all_chain_impacts":     {t: round(v * 100 * PRICE_SCALE, 2) for t, v in all_impacts.items()},
        "affected_count":        len(port_impacts),
        "avg_portfolio_impact":  round(avg * 100 * PRICE_SCALE, 2),
        "dollar_impact":         dollar_impact,
        "propagation_depth":     3,
        "graph_nodes":           len(_ALL_NODES),
        "graph_edges":           len(_EDGES),
    }


def get_supply_chain_neighbours(ticker: str, depth: int = 1) -> Dict[str, List[dict]]:
    """Return direct graph neighbours for display in the frontend."""
    result = {"suppliers": [], "customers": [], "competitors": []}
    for src, tgt, w in _EDGES:
        if src == ticker and w > 0:
            result["customers"].append({"ticker": tgt, "weight": w})
        elif tgt == ticker and w > 0:
            result["suppliers"].append({"ticker": src, "weight": w})
        elif src == ticker and w < 0:
            result["competitors"].append({"ticker": tgt, "weight": abs(w)})
        elif tgt == ticker and w < 0:
            result["competitors"].append({"ticker": src, "weight": abs(w)})
    return result
