"""
Conflict Data Integration — ACLED, UCDP, GDELT.
Provides real conflict/instability data for risk scoring.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ACLED_API_KEY = os.getenv("ACLED_API_KEY", "")
ACLED_EMAIL = os.getenv("ACLED_EMAIL", "")
ACLED_BASE_URL = "https://api.acleddata.com/acled/read"

UCDP_BASE_URL = "https://ucdpapi.pcr.uu.se/api/gedevents/24.1"

GDELT_BASE_URL = "https://api.gdeltproject.org/api/v2"


class ConflictDataService:
    """Fetches real conflict/instability data from academic sources."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ============================================================
    # ACLED (Armed Conflict Location & Event Data)
    # ============================================================

    async def get_acled_events(
        self,
        country_codes: Optional[list[str]] = None,
        days: int = 7,
        limit: int = 500,
    ) -> list[dict]:
        """
        Fetch recent ACLED events.

        Returns events: protests, riots, battles, explosions, violence against civilians.
        Free academic access requires API key + email registration.
        """
        if not ACLED_API_KEY or not ACLED_EMAIL:
            logger.debug("ACLED credentials not configured")
            return []

        session = await self._get_session()
        date_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        params = {
            "key": ACLED_API_KEY,
            "email": ACLED_EMAIL,
            "event_date": f"{date_from}|{datetime.utcnow().strftime('%Y-%m-%d')}",
            "event_date_where": "BETWEEN",
            "limit": limit,
            "fields": "event_id_cnty|event_date|event_type|sub_event_type|country|iso3|"
                      "admin1|admin2|location|latitude|longitude|fatalities|notes|source",
        }

        if country_codes:
            params["iso3"] = "|".join(country_codes)

        try:
            async with session.get(ACLED_BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"ACLED API error: {resp.status}")
                    return []
                data = await resp.json()
                events = data.get("data", [])

                return [
                    {
                        "id": ev.get("event_id_cnty", ""),
                        "date": ev.get("event_date", ""),
                        "event_type": self._normalize_acled_type(ev.get("event_type", "")),
                        "sub_event_type": ev.get("sub_event_type", ""),
                        "country": ev.get("country", ""),
                        "country_code": ev.get("iso3", ""),
                        "admin1": ev.get("admin1", ""),
                        "location": ev.get("location", ""),
                        "latitude": float(ev.get("latitude", 0) or 0),
                        "longitude": float(ev.get("longitude", 0) or 0),
                        "fatalities": int(ev.get("fatalities", 0) or 0),
                        "notes": ev.get("notes", "")[:500],
                        "source": "acled",
                    }
                    for ev in events
                ]
        except Exception as e:
            logger.warning(f"ACLED fetch error: {e}")
            return []

    @staticmethod
    def _normalize_acled_type(event_type: str) -> str:
        """Normalize ACLED event type to standard categories."""
        mapping = {
            "battles": "battles",
            "explosions/remote violence": "explosions_remote_violence",
            "violence against civilians": "violence_against_civilians",
            "protests": "protests",
            "riots": "riots",
            "strategic developments": "strategic_developments",
        }
        return mapping.get(event_type.lower(), event_type.lower())

    # ============================================================
    # UCDP (Uppsala Conflict Data Program)
    # ============================================================

    async def get_ucdp_conflicts(self, limit: int = 100) -> list[dict]:
        """
        Fetch UCDP armed conflict data.
        Intensity: 1 = minor conflict, 2 = war (1000+ battle deaths/year)
        Free, no API key required.
        """
        session = await self._get_session()

        try:
            params = {"pagesize": limit}
            async with session.get(UCDP_BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"UCDP API error: {resp.status}")
                    return []
                data = await resp.json()
                results = data.get("Result", [])

                return [
                    {
                        "id": ev.get("id", ""),
                        "year": ev.get("year", 0),
                        "conflict_name": ev.get("conflict_name", ""),
                        "side_a": ev.get("side_a", ""),
                        "side_b": ev.get("side_b", ""),
                        "country": ev.get("country", ""),
                        "country_code": ev.get("country_id", ""),
                        "region": ev.get("region", ""),
                        "intensity_level": int(ev.get("intensity_level", 0) or 0),
                        "type_of_violence": int(ev.get("type_of_violence", 0) or 0),
                        "latitude": float(ev.get("latitude", 0) or 0),
                        "longitude": float(ev.get("longitude", 0) or 0),
                        "best_estimate": int(ev.get("best", 0) or 0),
                        "date_start": ev.get("date_start", ""),
                        "date_end": ev.get("date_end", ""),
                        "source": "ucdp",
                    }
                    for ev in results
                ]
        except Exception as e:
            logger.warning(f"UCDP fetch error: {e}")
            return []

    # ============================================================
    # GDELT (Global Database of Events, Language, and Tone)
    # ============================================================

    async def get_gdelt_events(self, query: str, max_records: int = 50) -> list[dict]:
        """
        Search GDELT event database.
        Free, no API key required. Real-time global event monitoring.
        """
        session = await self._get_session()

        try:
            url = f"{GDELT_BASE_URL}/doc/doc"
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": max_records,
                "format": "json",
                "timespan": "7d",
            }

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"GDELT API error: {resp.status}")
                    return []
                data = await resp.json()
                articles = data.get("articles", [])

                return [
                    {
                        "title": art.get("title", ""),
                        "url": art.get("url", ""),
                        "source": art.get("domain", ""),
                        "language": art.get("language", ""),
                        "seendate": art.get("seendate", ""),
                        "tone": float(art.get("tone", 0) or 0),
                        "source_db": "gdelt",
                    }
                    for art in articles
                ]
        except Exception as e:
            logger.warning(f"GDELT fetch error: {e}")
            return []

    # ============================================================
    # Unified Conflict Snapshot
    # ============================================================

    async def get_conflict_snapshot(
        self, country_codes: Optional[list[str]] = None
    ) -> dict:
        """Get unified conflict data from all sources."""
        acled_task = self.get_acled_events(country_codes=country_codes)
        ucdp_task = self.get_ucdp_conflicts()

        results = await asyncio.gather(acled_task, ucdp_task, return_exceptions=True)

        acled_events = results[0] if not isinstance(results[0], Exception) else []
        ucdp_conflicts = results[1] if not isinstance(results[1], Exception) else []

        # Aggregate ACLED events by country
        country_events = {}
        for event in acled_events:
            cc = event.get("country_code", "")
            if cc not in country_events:
                country_events[cc] = {
                    "country": event.get("country", ""),
                    "battles": 0, "protests": 0, "riots": 0,
                    "explosions_remote_violence": 0,
                    "violence_against_civilians": 0,
                    "strategic_developments": 0,
                    "total_fatalities": 0, "total_events": 0,
                }
            entry = country_events[cc]
            etype = event.get("event_type", "")
            if etype in entry:
                entry[etype] += 1
            entry["total_events"] += 1
            entry["total_fatalities"] += event.get("fatalities", 0)

        # Identify active wars from UCDP
        active_wars = []
        active_conflicts = []
        for conflict in ucdp_conflicts:
            if conflict.get("intensity_level", 0) >= 2:
                active_wars.append(conflict)
            elif conflict.get("intensity_level", 0) >= 1:
                active_conflicts.append(conflict)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "acled_events": acled_events,
            "acled_by_country": country_events,
            "ucdp_conflicts": ucdp_conflicts,
            "active_wars": active_wars,
            "active_minor_conflicts": active_conflicts,
            "total_acled_events": len(acled_events),
            "total_fatalities": sum(e.get("fatalities", 0) for e in acled_events),
        }
