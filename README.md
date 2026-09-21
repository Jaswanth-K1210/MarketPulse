# MarketPulse-X

OSINT intelligence platform for traders.

## Run it locally

```bash
./dev.sh
```

Backend on http://localhost:8000 (API docs at `/docs`), frontend on
http://localhost:5173. Ctrl-C stops both.

**If the UI shows no data, check this first:** the frontend proxies `/api` to
port 8000 and renders empty when nothing is listening there. `curl
localhost:8000/api/health` — if that fails, the backend simply is not running.

## Source liveness

`GET /api/evidence/health` reports which data sources are actually alive. The
dashboard header shows the same as `N/M sources live`. A section that says
"source unavailable" is telling the truth: the feed is down, not the market
quiet.

Two feeds need action to go live:

- **ACLED** (conflict/military tensions) — free key at
  https://developer.acleddata.com, then set `ACLED_API_KEY` and `ACLED_EMAIL`
  in `.env`.
- **UCDP** — returns HTTP 401 on the `24.1` endpoint; it is no longer keyless.

## Notes

- Use `venv/`, not `.venv/`. Always invoke through the interpreter
  (`venv/bin/python -m pip`, `venv/bin/python -m pytest`) — console scripts in
  both venvs carry a dead shebang from the project's former path.
- Tests: `venv/bin/python -m pytest tests/ -q`
