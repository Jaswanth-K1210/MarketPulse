# MarketPulse as a Trader's Second Brain — Design

**Date:** 2026-09-20
**Status:** Approved, implementation starting with Sub-project A

## Problem

MarketPulse already produces ~30 distinct signals (options flow, short interest,
insider, retail sentiment, technical patterns, factor rotation, correlations,
macro, regime, anomaly, FinBERT sentiment, backtests, Monte Carlo, KG, memory).
It is not short of data. It is short of *trust*: a trader cannot tell which of
those 30 numbers is backed by live evidence and which is a dead feed returning a
confident zero.

The goal is not a better OSINT aggregator. It is a system a trader can use to
make and later defend a decision.

## Research basis

Four findings drive this design. Sources are cited so future readers can check
the reasoning rather than inherit it.

1. **Retrieval speed is the wrong optimisation target.**
   [The Research Process Is Broken](https://contours.ai/2026/04/14/the-research-process-is-broken-and-ai-didnt-fix-it/)
   argues most AI research tools "optimise for retrieval speed rather than
   decision quality. Making retrieval faster does not fix the underlying
   problem. It scales it." The missing layer is *structured evidence
   governance*: an auditable link between the question asked, the sources
   authorised to answer it, and the conclusion defensibly drawn.

2. **Insufficient evidence must be a first-class answer.** The same source:
   "explicit acknowledgment of insufficient evidence is not a limitation to be
   engineered away." Named failure modes are fabricated facts, fabricated
   sources, wrong attribution, and **stale confidence** — stating something true
   two years ago as current.

3. **LLM trading agents are regime-blind and decay fast.**
   [FINSABER](https://arxiv.org/html/2505.07078v5) backtested LLM strategies
   over two decades and 100+ symbols: reported advantages "deteriorate
   significantly" under a broader cross-section, with agents over-conservative
   in bull markets and over-aggressive in bear markets.
   [AlphaAgent](https://arxiv.org/pdf/2502.16789v2.pdf) shows LLM-driven alpha
   mining accelerates decay through factor homogenisation and crowding.
   ["Can Agentic Trading Systems Pay for Their Own Intelligence?"](https://arxiv.org/html/2607.10286v1)
   proposes attributing both profit *and* LLM cost back to interpretable
   evidence.

4. **What traders actually monitor**, from practitioner accounts: pre-market
   futures / overseas / VIX, economic calendar *with expected volatility*,
   sector relative strength, key levels marked before the open (VPOC, prior
   high/low, overnight range, unfilled gaps), unusual options activity, dealer
   gamma (call wall, put wall, gamma flip), and order-flow absorption *only at
   pre-marked levels*. Two meta-habits matter more than any single signal: they
   **set alerts instead of watching**, and they **log every instance and audit
   for strategy drift**.

Reference architectures reviewed:
[TradingAgents](https://github.com/TauricResearch/TradingAgents) and
[FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) — both model a
trading desk's org chart as an agent graph; MarketPulse's existing
`app/agents/` already follows this shape, so it is not a gap.

## Non-goals

Explicitly out of scope, to stop this growing without a decision:

- Adding new OSINT feeds for their own sake. Finding 3 and 1 both argue against it.
- Order execution or broker integration. This is a research tool.
- Autonomous trading. Every output is a recommendation with its evidence attached.
- Voice control, cockpit camera, satellite tracking (considered and dropped from
  the `gods-eye-view` reference).

## Decomposition

| # | Sub-project | Purpose | Existing assets |
|---|---|---|---|
| **A** | Evidence & liveness spine | Every signal carries provenance, freshness, and availability. Aggregates renormalise over live sources. "Insufficient evidence" is a valid answer. | `alpha_aggregator` (reference impl), `cache_manager`, `audit_agent` |
| **B** | Decision journal | Thesis → evidence snapshot → outcome → drift audit. The actual "second brain". | `memory_agent`, `audit_agent`, `AuditTrail.jsx` |
| **C** | Trader workflow surface | Pre-market brief, alert-at-level, watchlist triage. Globe panel lands here. | `Dashboard.jsx`, `alert_generator`, `telegram_bot` |
| **D** | Signal gaps | Dealer gamma/GEX, econ calendar with expected vol, pre-marked key levels, crowding-as-contrarian. | `options_flow` endpoint |
| **E** | Honest eval harness | Regime-split backtests (per FINSABER), cost-per-decision (per finding 3). | `backtester`, `walk_forward`, `usage_tracker` |

**Build order: A → B → D → C → E.**

A is first because it is the foundation, it is already half-built, and it fixes
a live defect. B is second because it is the genuine differentiator. D precedes
C so the new workflow surface has signals worth displaying.

---

# Sub-project A — Evidence & Liveness Spine

## The defect this fixes

Live, reproducible today:

```
$ curl -s localhost:8000/api/intelligence/signals
{"status":"bootstrap","signals":[],"timestamp":"..."}
```

The endpoint is healthy, the payload is well-formed, and the content is nothing.
`.env` has no `ACLED_API_KEY`/`ACLED_EMAIL`, so `conflict_data.get_acled_events`
returns `[]` immediately. Nothing in the response says so. A trader reads "no
signals" as "calm markets" rather than "the feed is dead."

`alpha_aggregator` already solves this correctly for one aggregate — it has
`_has_data`, `coverage`, `MIN_COVERAGE = 0.5`, and an `INSUFFICIENT_DATA`
verdict. The problem is that `_has_data` infers liveness *downstream*, with
bespoke per-component rules:

```python
if component == "short_interest":
    return bool(raw.get("sources")) and raw.get("short_pct_float") is not None
if component == "sentiment":
    return bool(raw.get("sources")) and (raw.get("total_mentions") or 0) > 0
```

Every new source needs another branch, and every other consumer re-invents the
guess. Liveness belongs to the source, not the reader.

## Design

### The contract

New module `app/services/evidence.py`. One dataclass, one helper. Not a framework.

```python
@dataclass
class SourceResult:
    source_id: str              # "acled", "finnhub_short_interest"
    available: bool             # did this source actually answer?
    data: Any = None
    error: str | None = None    # why not, in words a trader can read
    fetched_at: float = 0.0     # when we retrieved it
    as_of: float | None = None  # when the underlying fact was true
    origin: str | None = None   # URL / endpoint the data came from
```

The `as_of` vs `fetched_at` split is the point, and it is what kills **stale
confidence** (finding 2). A 2023 filing pulled from cache one second ago is
fresh-fetched and stale-fact. Only `as_of` can tell a trader whether the
evidence is current; `fetched_at` only says the plumbing ran.

`origin` carries provenance, the auditable link finding 1 requires.

### The aggregation rule

```python
def aggregate(results: dict[str, SourceResult], weights: dict[str, float],
              min_coverage: float = 0.5) -> dict
```

Contract, generalised from `alpha_aggregator`:

- Renormalise weights over `available=True` sources only. A dead source must
  never spend its weight.
- Report `coverage`: live weight fraction, live/total counts, and the names of
  missing sources with their `error` strings.
- Below `min_coverage`, return `INSUFFICIENT_EVIDENCE` with the reason, never a
  directional call.
- Report `staleness`: the oldest `as_of` among contributing sources, so a
  composite built from three-day-old inputs says so.

### Migration strategy

Thirty services will not be rewritten at once. Two seams make this incremental:

1. **`CacheManager.get_or_fetch` already returns `CacheResult(data, source,
   age_seconds)`** where `source` is one of `memory|redis|stale|bootstrap|fresh|
   miss|negative`. `bootstrap` and `negative` already mean "not live" — that
   information is computed and then discarded at the router. Threading it into
   `SourceResult` is a small change that upgrades every cached endpoint at once.

2. **`alpha_aggregator` becomes the first consumer**, with its bespoke
   `_has_data` branches deleted as each underlying source starts returning a
   `SourceResult`. Behaviour must not regress: it already reports coverage
   correctly, so its existing output is the regression baseline.

Order of conversion, highest value first: `signals` (currently broken),
`conflict`, `short_interest`, `retail_sentiment`, `insider`, `technical`,
`fundamentals`.

### Endpoint

`GET /api/evidence/health` — one call returning every registered source with
`available`, `as_of`, `error`, and per-aggregate coverage. This is what the
frontend liveness dots bind to, and what makes a dead feed visible in one look
instead of by noticing a suspicious zero.

### Frontend

Minimal in this sub-project — the surface work is C. Two changes:

- `BackendStatus.jsx` gains a source-coverage readout fed by
  `/api/evidence/health`.
- Any component rendering an aggregate shows coverage, and renders
  `INSUFFICIENT_EVIDENCE` as an explicit state rather than a zero or a blank.

## Relationship to `osint-research.md`

The July 2026 research plan (`osint-research.md`) drove most of the current data
layer and was largely implemented. This design amends one part of it and adopts
two others.

**Amended — §5.5 Graceful Degradation.** That section prescribes:

```
Primary source → Cache → Stale cache fallback → Keyword/rule fallback → Graceful null
```

Followed literally, this is the direct cause of the defect above: the chain
terminates in a *silent* null, so a dead source is indistinguishable from a
source that genuinely returned nothing. The chain itself is right — a dashboard
must not crash — but the terminal state must carry a flag. Amended:

```
Primary → Cache → Stale cache → Rule fallback → Null WITH available=False + error + as_of
```

**Adopted — §5.2 Staleness Detection.** Its per-source thresholds become the
concrete `as_of` limits: market data stale beyond 15 min (real-time) or 24 h
(EOD); insider filings flagged beyond a 5-day delay; news rejected beyond 7 days
or with no date. These belong in the source modules, checked against `as_of`.

**Adopted — §5.4 Reliability Rankings.** The Gold/Silver/Bronze/Watch tiers are
a natural input to `aggregate()` weights: a SEC EDGAR or FRED reading should not
carry the same weight as a scraped Bronze-tier source. Not wired in sub-project
A — noted so the tiering is not reinvented later.

## Error handling

A source that throws returns `SourceResult(available=False, error=str(e))` —
never a zero-valued payload. The existing `circuit_breaker` and `retry_handler`
stay where they are; they decide *whether to call*, `SourceResult` records
*what came back*.

## Testing

Per repo convention (`tests/test_osint_coverage.py` already guards
`alpha_aggregator`):

- A dead source reports `available: False` and never contributes weight.
- Coverage below `min_coverage` yields `INSUFFICIENT_EVIDENCE`, not a direction.
- A stale-cached source reports its true `as_of`, not its `fetched_at`.
- `/api/evidence/health` lists every registered source, including dead ones.

Regression guard: `alpha_aggregator` output for a fixed input is unchanged by
the refactor.

## Risks

- **Conversion drift.** Half-converted sources mean some liveness is real and
  some inferred. Mitigation: a registry of converted sources; `_has_data` stays
  as the fallback until its last branch is deleted.
- **Honest output looks worse.** Surfacing coverage will show that several
  signals are running on partial evidence. That is the intended outcome, and it
  will be uncomfortable before it is useful.
- **ACLED key is external.** Registration is free but requires a human. Conflict
  layer stays `available: False` with a clear error until then — which is
  exactly the behaviour being built.
