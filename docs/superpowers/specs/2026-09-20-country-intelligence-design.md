# Country Intelligence Panel — Design

**Date:** 2026-09-20
**Status:** Approved, implementing
**Builds on:** `2026-09-20-trader-second-brain-design.md` (sub-project A, the evidence spine)

## Goal

Click a country on the world map and get what a trader needs about it: the
companies domiciled there, their insider filings, the news flow, the market
picture, and — when the feeds are alive — military/conflict tensions. Plus
search for a company within that country.

## Why this is safe to build now

Sub-project A landed the evidence spine, so a section with no live source
renders as *"unavailable — ACLED_API_KEY not configured"* rather than as an
empty box implying calm. Without that, this panel would have been four working
sections and two silent lies.

## Data reality, verified 2026-09-20

Each pillar was tested against the live system, not assumed.

| Pillar | Backing | Verified how |
|---|---|---|
| **Companies in country** | yfinance `.info` returns `country` **and** `city` | `TSM→Taiwan/Hsinchu City`, `ASML→Netherlands/Veldhoven`, `ARM→United Kingdom/Cambridge`, `AAPL→United States/Cupertino` |
| **News** | `signal_aggregator.ingest_news_signals` already tags `country_code`, with `_infer_country` keyword fallback; 104 live sources | Existing code path |
| **Insiders** | Existing `/api/intelligence/insider-trades/{ticker}`, fanned out over the country's tickers | Existing endpoint |
| **Markets** | Partial — market signals hardcode `country_code="US"` ("Most indices are US"). Needs a static index-per-country table | `signal_aggregator.py:231` |
| **Military tensions** | **No live source.** ACLED unkeyed; UCDP `24.1` returns 401; GDELT returns 429 on repeated attempts | Live curl + two GDELT fetch attempts |
| **Shipping lanes** | **No data.** Zero references in the codebase; live AIS is a paid feed | Repo-wide grep |

### Known limitation, stated plainly

Insider data is **SEC Form 4 — US-listed filings only**. Clicking Taiwan surfaces
TSM's *ADR* filings, not Taiwanese insider activity. This is a regulatory
boundary, not an implementation gap, and the panel must label it as such rather
than implying it covers local insider activity.

## The geography problem

The map loads `world.geojson` from `raw.githubusercontent.com` **at runtime**,
and its features carry only `{"name": ...}` — no ISO codes. Two problems in one:
a third-party CDN sits in the data path, and there is no key to join map clicks
to `signal_aggregator`, which is keyed by ISO-3166 alpha-2.

**Fix:** vendor the file. A build script enriches each feature with `iso2`/`iso3`
and writes `frontend/public/world-countries.geojson` (248 KB), which the map
loads locally. No runtime external fetch, and clicks yield an ISO2 directly.

`pycountry` resolves 160 of 177 names. The remaining 17 need an explicit alias
table — and three of them matter:

- `Russia → RU`, `Turkey → TR`, and **`England → GB`** (the geojson labels the
  United Kingdom "England", which is where ARM lives)
- Plus: Ivory Coast→CI, The Bahamas→BS, Brunei→BN, Democratic Republic of the
  Congo→CD, Guinea Bissau→GW, Macedonia→MK, Swaziland→SZ, East Timor→TL,
  Falkland Islands→FK, French Southern and Antarctic Lands→TF, West Bank→PS
- Deliberately unmapped (no ISO assignment): Northern Cyprus, Somaliland, Kosovo.
  These render as clickable but return no data, which the panel states.

## Architecture

### Backend

**`app/services/data/company_geo.py`** — resolves a ticker to its domicile via
yfinance `.info`, returning a `SourceResult`. Builds the reverse index
(country → tickers) over the known universe: `SUPPLY_CHAIN_COMPANIES` plus the
user's watchlist. Country lookups are effectively static, so they cache with a
long TTL; a failed lookup returns `available: False` rather than guessing.

**`app/routers/country.py`** — `GET /api/country/{iso2}` returns one object whose
every section is an evidence-wrapped block:

```
{ "country": {"iso2","name"},
  "sections": {
     "companies": {available, data:[{ticker,name,city}], error},
     "insiders":  {available, data:[...], error, note:"SEC Form 4 — US-listed only"},
     "news":      {available, data:[...], error},
     "markets":   {available, data:{...}, error},
     "tensions":  {available:false, error:"ACLED_API_KEY not configured"},
     "shipping":  {available:false, error:"no data source configured"} },
  "coverage": {live_count, total_count, missing:{...}} }
```

`coverage` comes from `evidence.aggregate()` with equal weights, so the panel can
show "4 of 6 sections live" the same way the alpha score shows source coverage.

### Frontend

**`WorldMap.jsx`** — `<Geography onClick>` emits the feature's `iso2`; selected
country gets a highlight fill. Loads the vendored geojson.

**`CountryPanel.jsx`** — slide-over panel. One card per section; an unavailable
section renders its `error` in muted/amber instead of an empty list. Includes a
filter box over the country's companies (this is the "search by company in that
country"), and each company row links into the existing Research view.

## Non-goals

- Live vessel/AIS tracking. Not buying a feed.
- Per-country insider data beyond SEC filings.
- Rendering tensions or shipping as anything other than explicitly unavailable
  until a real source is wired.

## Testing

- `company_geo` returns `available: False` with a reason when yfinance has no
  country, never a guessed one.
- The alias table resolves England→GB, Russia→RU, Turkey→TR.
- A country with no companies returns `available: True` with an empty list
  (genuinely none) — distinct from a lookup failure.
- `/api/country/{iso2}` reports 6 sections with `coverage.live_count < 6` while
  tensions and shipping are dead.
