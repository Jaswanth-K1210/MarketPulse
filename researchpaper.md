# MarketPulse-X — Research Implementation Audit & Paper Survey

**Compiled:** 2026-08-14
**Re-verified:** 2026-08-23 — see the status update below before reading §1–§3, which are partly superseded.

---

## 0. Status update (2026-08-23)

The §1–§3 audit below was accurate when compiled but is now out of date. Every
claim was re-checked against running code, not module names. Corrections:

| §  | Audit claim (2026-08-14) | Verified state (2026-08-23) |
|----|--------------------------|------------------------------|
| §2.4 | Isolation Forest **ABSENT** | **BUILT** — `app/ml/anomaly_detector.py:20`, real `sklearn.IsolationForest` |
| §2 (cross-cutting) | Backtester single-pass, no slippage/costs | **BUILT** — `backtester.py:23` (`slippage_bps=5.0`, `commission_bps=10.0`), `walk_forward()`, exposed at `intelligence.py:626` |
| §1 | `retrain()` accepts feedback and ignores it | **FIXED** — `risk_scorer.py:269` pulls unincorporated feedback from the DB |
| §3 | GHAN-Lite: 0 of 7 components built | **5 of 7 exist** — `app/ml/ghan/{dataset,graph_builder,model,sp100}.py`, `scripts/train_ghan.py`, `scripts/evaluate_impact_models.py`, `tests/test_ghan.py`. Scorer lives in `model.py:90`, not `scorer.py`; `docs/ghan_evaluation.md` still absent |
| §2 (cross-cutting) | Disclaimer **ABSENT** | Was present but duplicated across four modules with divergent wording, and missing from the alpha score. **Now consolidated** — see below |

### What the audit got right, and what it missed

The headline finding — *"the shape of an ML system with heuristics inside"* —
still holds, and had in fact **reproduced itself one level up inside GHAN**:

- `torch` and `torch_geometric` were declared in `requirements.txt` but installed
  in neither venv.
- FNSPID was never downloaded. `dataset.py:46` fell through to
  `_generate_synthetic_dataset()`, so the committed `data/ghan/dataset.parquet`
  is 2,000 rows of `np.random.default_rng(42)`.
- `scripts/train_ghan.py:49` detects the missing torch and writes
  `_save_synthetic_metrics()`, whose own note reads *"PyTorch not available —
  synthetic metrics for demonstration."*
- `app/ml/models/ghan.pt` does not exist, so `GHANScorer` (`model.py:99`) always
  falls back to `risk_scorer` — the synthetically-trained LightGBM.

**Root cause, and the thing the audit under-weighted:** the venv had never been
reinstalled from `requirements.txt`. `yfinance` was pinned at `>=1.5.0` but
**0.2.32 was installed**, and Yahoo's chart API had changed underneath it —
every price call returned zero rows. That single stale pin cascaded through
technical analysis, short interest, options flow, corporate actions, the
backtester, *and* GHAN's label computation.

Measured before the fix, against live AAPL: **1 of 12 OSINT services returned
real data.** The alpha aggregator nonetheless returned `-1.25 / "NEUTRAL"`,
because `alpha_aggregator.py` applied fixed weights unconditionally — four dead
sources each scored `0.0`, spent their weight, and dragged the composite toward
neutral, with nothing in the response indicating the data was missing.

### Remediation completed (2026-08-23)

1. **Environment restored.** Consolidated on `venv/`; `yfinance` 0.2.32 → 1.6.0
   (pin raised to `>=1.6.0`); `networkx` installed. `pandas-ta` and
   `vaderSentiment` were removed from `requirements.txt` — nothing imports them,
   and `pandas-ta`'s pinned build fails on numpy 2.x.
2. **Dead sources repaired.**
   - `fda_trials` — ClinicalTrials.gov v1 was retired (404). Rewritten against
     **v2**, with enum normalisation so the existing scorer keeps working.
   - `earnings_transcripts` — SeekingAlpha returns 403 to unauthenticated
     clients. **Motley Fool** added as the primary source (full transcript text,
     no auth); SeekingAlpha retained as fallback.
   - `retail_sentiment` — Reddit's `search.json` returns 403 and the
     Pushshift/PullPush mirrors 429. Added the **Atom feed** path plus
     throttling, `Retry-After`-aware backoff, and an optional authenticated
     (`praw`) path.
3. **Alpha score made honest.** `alpha_aggregator` now renormalises weights over
   sources that actually returned data, reports
   `coverage: {live, missing, weight_fraction, sufficient}`, and withholds the
   directional call as `INSUFFICIENT_DATA` below 50% coverage. The five fetches
   now run concurrently via `asyncio.gather` instead of in series.
4. **Disclaimer consolidated.** Four divergent copies replaced by
   `app/core/disclaimer.py`; `DisclaimerHeaderMiddleware` attaches `X-Disclaimer`
   to every response including errors; the alpha-score payload carries it; the
   frontend banner extracted to `DisclaimerBanner.jsx` over a shared constant.
5. **Honest degradation** for what cannot be fixed without credentials — these
   now return `available: false` with an `error` explaining why, instead of
   zeros that read as real answers.

**Result: 10 of 12 OSINT services live** (was 1). Full suite: 120 passed,
2 skipped.

### Still outstanding

| Item | Blocker |
|---|---|
| `patents` | PatentsView's legacy endpoint was retired; the replacement needs a free API key — set `PATENTSVIEW_API_KEY` |
| `twitter_sentiment` | Public Nitter instances are defunct (nitter.net serves an empty timeline, others 403) — set `NITTER_INSTANCES` to a working instance |
| Reddit reliability | Unauthenticated feeds allow ~1 request per burst per IP; set `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` for a usable rate limit |
| GHAN as a real model | Needs `torch` + real FNSPID. Untouched by this pass — it remains a fallback scorer, and its committed dataset is still synthetic |
| MLflow, Black-Litterman, CVaR objective, regime-gated allocation | Not started (§2, §5 below) |
| Leakage-clean evaluation window | §4.3 below — still unaddressed, and still blocks any credible backtest claim |

> **Note on `TestClient`:** the installed `httpx` 0.28 / `starlette` combination
> breaks `fastapi.testclient` (`Client.__init__() got an unexpected keyword
> argument 'app'`). Endpoint verification in this pass was done against a live
> uvicorn process instead.

---

# Original audit (2026-08-14)

**Sources audited:**
- `MarketPulse-X_ ML, Quant Finance, and RL Implementation Blueprint.pdf` (25 algorithms, 3 phases; self-dated "current as of May 2026")
- `docs/superpowers/specs/2026-07-13-ghan-impact-scorer-design.md` (GHAN-Lite spec, arXiv:2409.00438)

**Method:** every algorithm in the blueprint was grepped against `app/`, `scripts/`, and `tests/`, and each hit was opened and read. Status reflects what the code actually does, not what module names suggest.

> Sections 1–3 and 5 are preserved as written on 2026-08-14. Where §0 above
> contradicts them, §0 is current.

## 1. Headline finding

**There is no model training anywhere in this codebase.**

```
grep -rlE "\.backward\(\)|optimizer\.step|nn\.Module|DataLoader" app/ scripts/
→ (no matches)
```

The only fitted model in the repo is `app/ml/models/risk_lgbm.pkl`, and it is trained on 3,000 rows generated by a hand-written formula:

```python
# app/ml/risk_scorer.py:91
base = (sev / 3.0) * 0.4 + abs(sent) * 0.3 + ((5 - tier) / 4.0) * 0.15
```

This is the exact problem the GHAN spec named "rule-laundering, not learning." The model has never seen a market outcome. Its `retrain(feedback_rows)` method (line 209) **accepts a feedback argument and ignores it** — it calls `_train_and_save()`, which regenerates the same synthetic distribution. The weekly APScheduler retrain is therefore a no-op dressed as continuous learning.

Everything below follows from this: the platform has the *shape* of an ML system (services named `gnn_service`, `risk_scorer`, `regime_detector`) with heuristics inside.

---

## 2. Blueprint audit — all 25 algorithms

Legend: **BUILT** = implemented as specified · **INVALID** = implemented but scientifically unsound · **STUB** = the name exists, the method does not · **ABSENT** = no code

| # | Algorithm | Pri | Status | Evidence |
|---|---|---|---|---|
| 1 | FinBERT fine-tune | P0 | **STUB** | `finbert_service.py` runs stock `ProsusAI/finbert` zero-shot. No fine-tune, no event-type head, no severity head, no CLS embeddings exported |
| 2 | LightGBM + SHAP risk scorer | P0 | **INVALID** | `risk_scorer.py` — real LightGBM + SHAP, trained on synthetic formula output; `retrain()` discards feedback |
| 3 | HMM regime detection | P0 | **BUILT** | `regime_detector.py` — genuine `GaussianHMM(n_components=4)` with rule fallback |
| 4 | Isolation Forest / LSTM-AD | P0 | **ABSENT** | no `IsolationForest` anywhere |
| 5 | Black-Litterman + ML views | P0 | **ABSENT** | `portfolio_optimizer.py` hand-rolls `optimize_mean_variance`; no PyPortfolioOpt, no BL, no Ledoit-Wolf |
| 6 | Kalman filter | P1 | **ABSENT** | — |
| 7 | Contextual bandits (LinUCB/Thompson) | P1 | **ABSENT** | LangGraph routing is static |
| 8 | **Heterogeneous GNN (R-GCN/GAT/HGT)** | **P0** | **STUB** | `gnn_service.py` is hand-written adjacency propagation. No PyG, no `GATConv`, no message passing, no training. Optionally multiplies scores by `torch.sigmoid(embed)` from a weights file that does not exist |
| 9 | Temporal Fusion Transformer | P1 | **ABSENT** | — |
| 10 | GARCH-LSTM (GINN) | P1 | **ABSENT** | `arch` declared in requirements, never imported |
| 11 | Causal Forests / Double ML | P1 | **ABSENT** | no `econml` |
| 12 | KG embeddings (RotatE/ComplEx) | P2 | **ABSENT** | no `pykeen` |
| 13 | Fama-French + ML factor model | P2 | **ABSENT** | — |
| 14 | N-BEATS / N-HiTS | P2 | **ABSENT** | `neuralforecast` declared, never imported |
| 15 | Louvain community detection | P2 | **ABSENT** | `python-louvain` declared, never imported |
| 16 | CVaR optimization | P1 | **PARTIAL** | CVaR is *computed and reported* (`monte_carlo_service.py:95`, `portfolio_optimizer.py:156`) but never used as an optimization **objective** |
| 17 | Hierarchical Risk Parity | P2 | **ABSENT** | — |
| 18 | Regime-switching Markowitz | P2 | **ABSENT** | HMM exists but does not gate any allocation |
| 19 | PPO portfolio agent (FinRL) | P1 | **ABSENT** | — |
| 20 | SAC allocation | P2 | **ABSENT** | — |
| 21 | Double-Dueling DQN execution | P2 | **ABSENT** | — |
| 22 | Hierarchical RL (HRPM) | P2 | **ABSENT** | — |
| 23 | MARL / QMIX / CORY | P2 | **ABSENT** | — |
| 24 | RLHF / DPO | P2 | **ABSENT** | — |
| 25 | Composite reward shaping | P1 | **ABSENT** | no RL of any kind exists |

**Score: 1 built · 1 built-but-invalid · 2 stubs · 1 partial · 20 absent.**

Phase 1 (the "quick wins") is ~1.5 of 7 done. Phases 2 and 3 are untouched. **Zero of the seven P0 items are both built and sound.**

### Cross-cutting engineering recommendations — also outstanding

| Recommendation | Status |
|---|---|
| Walk-forward backtest harness **before** any RL | **ABSENT.** `backtester.py` is single-pass (`buy_and_hold`, `sma_crossover`, `alpha_momentum`) with **no walk-forward, no slippage, no transaction costs** — the blueprint calls this out as the #1 cause of RL-trading failure |
| MLflow experiment tracking from day 1 | **ABSENT** |
| ML services as separate FastAPI microservices | **ABSENT** — all in-process |
| "Advisory only, not investment advice" disclaimer | **ABSENT** — no disclaimer in backend or frontend, despite the app emitting trade recommendations. This is the blueprint's explicit regulatory note and is the cheapest item on this entire list |

---

## 3. GHAN-Lite spec — 0 of 7 components built *(superseded: 5 of 7 now exist — see §0)*

`docs/superpowers/specs/2026-07-13-ghan-impact-scorer-design.md` is marked **Status: Approved**. Nothing was implemented:

| § | Component | Path | Exists |
|---|---|---|---|
| 1 | Dataset builder | `app/ml/ghan/dataset.py` | ✗ |
| 2 | Graph builder (star expansion) | `app/ml/ghan/graph_builder.py` | ✗ |
| 3 | Model (GATConv bipartite) | `app/ml/ghan/model.py` | ✗ |
| 4 | Training CLI | `scripts/train_ghan.py` | ✗ |
| 5 | Evaluation harness | `scripts/evaluate_impact_models.py` | ✗ |
| 6 | Scorer integration | `app/ml/ghan/scorer.py` | ✗ |
| 7 | Tests | `tests/test_ghan.py` | ✗ |

The directory `app/ml/ghan/` does not exist. `docs/ghan_evaluation.md` does not exist. The spec's premise was re-verified against current code and **still holds exactly** — so the spec is not stale, just unexecuted. It remains the single highest-value piece of work available, because it converts the project's central weakness (a synthetic-trained scorer) into its report narrative.

---

## 4. Newer and adjacent papers

The blueprint self-dates to **May 2026**; it is now **August 2026**. The following are either successors to its citations or fill gaps it left. These were not in the original document.

### 4.1 Direct successor to the GHAN base paper — *use this instead*

**CSHT — "From News to Returns: A Granger-Causal Hypergraph Transformer on the Sphere"** ([arXiv:2510.04357](https://arxiv.org/abs/2510.04357), [ACM ICAIF '25](https://dl.acm.org/doi/10.1145/3768292.3770414))

By **Harit, Sun & Yu — two of the three authors of GHAN (arXiv:2409.00438) itself.** This is the same research line, one generation on: it keeps the hyperspherical geometry but replaces undirected hyperedges with **Granger-causal directional hyperedges** plus causally-masked Transformer attention. Evaluated on S&P 500, 2018–2023, including the COVID shock, outperforming baselines on return prediction, regime classification, and top-asset ranking.

**Why it matters here:** the causal masking directly addresses the weakest assumption in the existing GHAN-Lite spec (undirected event↔ticker edges), and the directional hyperedge construction maps onto MarketPulse's supply-chain relationship table more naturally than star expansion does — supplier→customer *is* a directed edge. Consider retargeting the spec at CSHT, keeping the same star-expansion fallback for implementation tractability.

### 4.2 Other current work on the same problem

| Paper | Relevance |
|---|---|
| **MaGNet: Mamba Dual-Hypergraph Network for Stock Prediction** ([arXiv:2511.00085](https://arxiv.org/pdf/2511.00085)) | Temporal-causal + global relational hypergraph learning; Mamba backbone is far cheaper to train than a Transformer on a laptop/MPS — relevant given the spec targets MPS/CPU |
| **Relational Probing: LM-to-Graph Adaptation for Financial Prediction** ([arXiv:2604.10212](https://arxiv.org/pdf/2604.10212)) | 2026. Extracts relational structure from an LM into a graph — a cheaper alternative to the blueprint's §1.3 KG-embedding route, and a direct fit for the existing LLM relationship-discovery agent |
| **Physics-Informed GNNs for Supply Chain Disruption** ([ResearchGate](https://www.researchgate.net/publication/399504875_Physics-Informed_Graph_Neural_Networks_for_Supply_Chain_Disruption_Prediction_and_Mitigation)) | Reports 23% disruption-prediction error reduction vs. purely data-driven GNNs — relevant to blueprint §1.2, the P0 item that is currently a stub |
| **GNNs in Supply Chain Analytics: Concepts, Dataset and Benchmarks** ([arXiv:2411.08550](https://arxiv.org/html/2411.08550v1)) | Supplies the benchmark/dataset baseline the blueprint's §1.2 lacks |

### 4.3 Evaluation integrity — the gap the blueprint under-weights

This is the most important addition, because it determines whether *any* result from the work above is believable.

**"Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents"** ([arXiv:2510.07920](https://arxiv.org/abs/2510.07920))

Finding: LLM-based financial agents show "dazzling back-tested returns [that] evaporate once the model's knowledge window ends." The cause is **pre-training contamination** — the LLM memorized the price moves and their post-hoc explanations from its training corpus, so it is recalling, not reasoning. The paper releases **FinLake-Bench** (leakage-robust evaluation) and **FactFin**, which uses counterfactual perturbation to force causal learning.

**Why this is critical for MarketPulse specifically:** the entire pipeline is LLM-driven (OpenRouter/Groq/Gemini), and the GHAN-Lite spec proposes evaluating on **2022 test data** — comfortably inside every current model's pre-training window. Any backtest over that period is contaminated by construction. Related: [HindsightBench](https://arxiv.org/html/2607.18867v1) (black-box audit for parametric hindsight) and [Interpretable Temporal Contamination Detection](https://arxiv.org/pdf/2602.17234).

**Concrete implication:** either move the test window past the model knowledge cutoff, or evaluate the GHAN model in isolation from LLM features. The current spec does neither.

### 4.4 Dataset note — FNSPID

**FNSPID** ([arXiv:2402.06698](https://arxiv.org/abs/2402.06698), [GitHub](https://github.com/Zdong104/FNSPID_Financial_News_Dataset)) — 29.7M prices + 15.7M time-aligned news records, 4,775 S&P 500 companies, 1999–2023. The spec's choice is sound and remains the best open option.

Caveats to design around: the headline R²=0.988 sentiment-augmented benchmark is **not** a realistic target — it reflects favourable framing, and reported performance concentrates in persistent trend regimes with weak predictive power in the ranging conditions that dominate real markets. The spec's 3-class abnormal-return-vs-SPY target is a **more honest** formulation than the FNSPID paper's own benchmark, and should be kept.

### 4.5 RL track — if Phase 3 is ever attempted

| Paper | Note |
|---|---|
| [HARLF](https://arxiv.org/pdf/2507.18560) (arXiv:2507.18560) | Hierarchical RL + lightweight LLM sentiment; already cited in blueprint §4.4, still the closest fit |
| [FinRL Contests benchmark](https://arxiv.org/pdf/2504.02281) (arXiv:2504.02281) | Standardized baselines — use rather than self-reported Sharpe |
| [3S-Trader](https://arxiv.org/pdf/2510.17393) (arXiv:2510.17393) | Multi-LLM scoring/strategy/selection — architecturally close to the existing LangGraph agents |
| [LLM-Based Financial Multi-Agent Systems: Taxonomy & Cost Awareness](https://arxiv.org/html/2603.27539v1) (arXiv:2603.27539) | March 2026 survey of 2023–2026 work; the cost-awareness dimension is directly applicable to the current multi-provider LLM router |

---

## 5. Recommended order of work *(items 1, 2 and 4 are now done — see §0)*

1. **Add the "not investment advice" disclaimer.** Hours of work, explicitly required by the blueprint, currently absent while the app emits trade recommendations.
2. **Build the walk-forward backtest harness with slippage and costs.** The blueprint insists this precedes all model work; today's `backtester.py` cannot validate anything. Nothing below is trustworthy without it.
3. **Execute the GHAN-Lite spec** — retargeted at CSHT (§4.1) if scope allows, with a test window chosen against the leakage constraint (§4.3). This converts the headline weakness into the project's actual contribution.
4. **Fix or retire `retrain()`.** Either wire real outcome feedback into it or delete it; shipping a no-op that presents as continuous learning is worse than shipping neither.
5. **Then** Phase 1 leftovers — Isolation Forest (§2.4, ~0.5 wk) and Black-Litterman via PyPortfolioOpt (§5.1, ~1 wk) are the cheapest genuine wins.

**Environment note:** several of these are blocked before a line is written. `torch`, `transformers`, `scikit-learn`, `lightgbm`, `hmmlearn`, `arch`, `statsmodels`, `neuralforecast`, `PyPortfolioOpt`, `cvxpy`, and `networkx` are declared in `requirements.txt` but **not installed** — so even the HMM regime detector (the one genuinely-built P0 item) is running its rule-based fallback in production today.

---

## Sources

- [arXiv:2409.00438 — Breaking Down Financial News Impact: Geometric Hypergraphs (GHAN)](https://arxiv.org/abs/2409.00438)
- [arXiv:2510.04357 — From News to Returns: Granger-Causal Hypergraph Transformer on the Sphere (CSHT)](https://arxiv.org/abs/2510.04357) · [ACM ICAIF '25](https://dl.acm.org/doi/10.1145/3768292.3770414)
- [arXiv:2511.00085 — MaGNet: Mamba Dual-Hypergraph Network](https://arxiv.org/pdf/2511.00085)
- [arXiv:2604.10212 — Relational Probing: LM-to-Graph Adaptation](https://arxiv.org/pdf/2604.10212)
- [arXiv:2510.07920 — Profit Mirage: Information Leakage in LLM-based Financial Agents](https://arxiv.org/abs/2510.07920)
- [arXiv:2607.18867 — HindsightBench](https://arxiv.org/html/2607.18867v1)
- [arXiv:2602.17234 — Interpretable Temporal Contamination Detection](https://arxiv.org/pdf/2602.17234)
- [arXiv:2402.06698 — FNSPID dataset](https://arxiv.org/abs/2402.06698) · [GitHub](https://github.com/Zdong104/FNSPID_Financial_News_Dataset)
- [arXiv:2411.08550 — GNNs in Supply Chain Analytics: Benchmarks](https://arxiv.org/html/2411.08550v1)
- [Physics-Informed GNNs for Supply Chain Disruption](https://www.researchgate.net/publication/399504875_Physics-Informed_Graph_Neural_Networks_for_Supply_Chain_Disruption_Prediction_and_Mitigation)
- [arXiv:2507.18560 — HARLF](https://arxiv.org/pdf/2507.18560)
- [arXiv:2504.02281 — FinRL Contests](https://arxiv.org/pdf/2504.02281)
- [arXiv:2510.17393 — 3S-Trader](https://arxiv.org/pdf/2510.17393)
- [arXiv:2603.27539 — LLM Financial Multi-Agent Systems: Taxonomy & Cost Awareness](https://arxiv.org/html/2603.27539v1)
