"""
NewsIngestionLayer v2 — 110 curated sources
  - ETag/If-Modified-Since caching on every feedparser call (304 = serve stale)
  - Per-feed circuit breaker: 3 failures → 15-min cooldown
  - source_tier (1–4) and state_affiliated flag on every source
  - Negative caching: empty / 404 responses cached 5 min
  - Portfolio-based feed filtering: only fetch feeds tagged to user's sectors
"""
import feedparser
import requests
import requests.exceptions
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.config import (
    FINNHUB_API_KEY,
    GNEWS_API_KEY,
    MEDIASTACK_API_KEY,
    NEWSAPI_KEY,
    NEWSDATA_IO_KEY,
    TRACKED_COMPANIES,
)
from app.models.article import Article

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN = 900   # 15 min
NEGATIVE_CACHE_TTL = 300         # 5 min

# ─── SOURCE CATALOG ────────────────────────────────────────────────────────────
# tier 1 = Official/Regulatory  tier 2 = Major Financial/Business
# tier 3 = Industry/Specialized tier 4 = Community/Alternative
# state_affiliated: True → apply discount weight in LightGBM features
SOURCE_CATALOG: List[Dict] = [
    # ── Tier 1 — Official & Regulatory ────────────────────────────────────────
    {"name": "Reuters Business",        "url": "https://feeds.reuters.com/reuters/businessNews",                            "tier": 1, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "Reuters Top News",        "url": "https://feeds.reuters.com/reuters/topNews",                                 "tier": 1, "state_affiliated": False, "category": "general",      "tags": ["macro", "geopolitical"]},
    {"name": "Reuters Energy",          "url": "https://feeds.reuters.com/reuters/energy",                                  "tier": 1, "state_affiliated": False, "category": "energy",       "tags": ["energy", "oil"]},
    {"name": "Bloomberg Markets",       "url": "https://feeds.bloomberg.com/markets/news.rss",                              "tier": 1, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "Bloomberg Technology",    "url": "https://feeds.bloomberg.com/technology/news.rss",                           "tier": 1, "state_affiliated": False, "category": "tech",         "tags": ["tech", "semiconductor"]},
    {"name": "Financial Times",         "url": "https://www.ft.com/rss/home/us",                                            "tier": 1, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "WSJ Markets",             "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",                             "tier": 1, "state_affiliated": False, "category": "financial",    "tags": ["market"]},
    {"name": "WSJ World News",          "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",                               "tier": 1, "state_affiliated": False, "category": "general",      "tags": ["geopolitical", "macro"]},
    {"name": "AP Business",             "url": "https://rsshub.app/apnews/topics/business",                                 "tier": 1, "state_affiliated": False, "category": "general",      "tags": ["macro"]},
    {"name": "Federal Reserve",         "url": "https://www.federalreserve.gov/feeds/press_all.xml",                        "tier": 1, "state_affiliated": True,  "category": "macro",        "tags": ["macro", "rates"]},
    {"name": "SEC Press Releases",      "url": "https://www.sec.gov/news/pressreleases.rss",                                "tier": 1, "state_affiliated": True,  "category": "regulatory",   "tags": ["regulatory"]},
    {"name": "BLS News",                "url": "https://www.bls.gov/feed/bls_latest.rss",                                   "tier": 1, "state_affiliated": True,  "category": "macro",        "tags": ["macro", "labor"]},
    {"name": "WHO News",                "url": "https://www.who.int/rss-feeds/news-english.xml",                             "tier": 1, "state_affiliated": True,  "category": "health",       "tags": ["health", "pandemic"]},
    {"name": "USGS Earthquakes",        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.atom", "tier": 1, "state_affiliated": True, "category": "disaster", "tags": ["disaster", "logistics"]},
    {"name": "NOAA Weather Alerts",     "url": "https://www.weather.gov/rss_page.php?site_name=us",                         "tier": 1, "state_affiliated": True,  "category": "disaster",     "tags": ["disaster", "logistics"]},
    {"name": "WTO News",                "url": "https://www.wto.org/rss/english/news_e.rss",                                "tier": 1, "state_affiliated": True,  "category": "trade",        "tags": ["trade", "tariff"]},
    {"name": "World Bank",              "url": "https://feeds.worldbank.org/worldbank/all",                                  "tier": 1, "state_affiliated": True,  "category": "macro",        "tags": ["macro", "emerging"]},
    {"name": "IMF News",                "url": "https://www.imf.org/en/News/rss?language=eng",                              "tier": 1, "state_affiliated": True,  "category": "macro",        "tags": ["macro"]},
    {"name": "OFAC Sanctions",          "url": "https://home.treasury.gov/system/files/126/ofac.xml",                       "tier": 1, "state_affiliated": True,  "category": "regulatory",   "tags": ["sanctions", "regulatory"]},
    {"name": "DOJ Antitrust",           "url": "https://www.justice.gov/feeds/opa/justice-news.xml",                        "tier": 1, "state_affiliated": True,  "category": "regulatory",   "tags": ["regulatory"]},
    {"name": "FTC News",                "url": "https://www.ftc.gov/feeds/press-release-rss.xml",                           "tier": 1, "state_affiliated": True,  "category": "regulatory",   "tags": ["regulatory"]},
    # ── Tier 2 — Major Financial & Business ───────────────────────────────────
    {"name": "CNBC",                    "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",                     "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "CNBC Tech",               "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html",                      "tier": 2, "state_affiliated": False, "category": "tech",         "tags": ["tech", "semiconductor"]},
    {"name": "Forbes Business",         "url": "https://www.forbes.com/business/feed/",                                     "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market"]},
    {"name": "Business Insider",        "url": "https://feeds.businessinsider.com/custom/all",                              "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market"]},
    {"name": "The Guardian Business",   "url": "https://www.theguardian.com/business/rss",                                  "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "BBC Business",            "url": "https://feeds.bbci.co.uk/news/business/rss.xml",                            "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "BBC Technology",          "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",                          "tier": 2, "state_affiliated": False, "category": "tech",         "tags": ["tech"]},
    {"name": "The Economist",           "url": "https://www.economist.com/finance-and-economics/rss.xml",                   "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["macro", "market"]},
    {"name": "MarketWatch",             "url": "https://feeds.marketwatch.com/marketwatch/topstories/",                     "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "stocks"]},
    {"name": "Seeking Alpha",           "url": "https://seekingalpha.com/market_currents.xml",                              "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "stocks"]},
    {"name": "Barron's",                "url": "https://www.barrons.com/feed/rss/current-all.rss",                          "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "stocks"]},
    {"name": "NYT Business",            "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",                 "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "NYT Technology",          "url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",               "tier": 2, "state_affiliated": False, "category": "tech",         "tags": ["tech"]},
    {"name": "Axios Markets",           "url": "https://api.axios.com/feed/stream/9c30a6e9-37a2-4e79-b02b-cf2e4ce9a7a1",  "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market"]},
    {"name": "FT Alphaville",           "url": "https://ftalphaville.ft.com/feed/",                                         "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "quant"]},
    {"name": "S&P Global Commodity",    "url": "https://www.spglobal.com/commodityinsights/en/rss-feed-list",               "tier": 2, "state_affiliated": False, "category": "commodity",    "tags": ["commodity", "macro"]},
    {"name": "Nasdaq News",             "url": "https://www.nasdaq.com/feed/rssoutbound",                                   "tier": 2, "state_affiliated": False, "category": "financial",    "tags": ["market", "stocks"]},
    {"name": "ProPublica",              "url": "https://feeds.propublica.org/propublica/main",                              "tier": 2, "state_affiliated": False, "category": "investigative","tags": ["regulatory", "corporate"]},
    {"name": "Investopedia",            "url": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=rss_headline","tier": 2,"state_affiliated": False, "category": "financial",    "tags": ["market"]},
    {"name": "South China Morning Post","url": "https://www.scmp.com/rss/91/feed",                                          "tier": 2, "state_affiliated": False, "category": "china",        "tags": ["china", "macro"]},
    {"name": "Nikkei Asia",             "url": "https://asia.nikkei.com/rss/feed/nar",                                      "tier": 2, "state_affiliated": False, "category": "asia",         "tags": ["asia", "macro", "semiconductor"]},
    # ── Tier 3 — Industry & Specialized ───────────────────────────────────────
    {"name": "TechCrunch",              "url": "https://techcrunch.com/feed/",                                              "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "startup"]},
    {"name": "Wired",                   "url": "https://www.wired.com/feed/rss",                                            "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech"]},
    {"name": "Ars Technica",            "url": "https://feeds.arstechnica.com/arstechnica/index",                           "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "semiconductor"]},
    {"name": "MIT Tech Review",         "url": "https://www.technologyreview.com/feed/",                                    "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "ai"]},
    {"name": "IEEE Spectrum",           "url": "https://spectrum.ieee.org/feeds/feed.rss",                                  "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "semiconductor"]},
    {"name": "EE Times",                "url": "https://www.eetimes.com/feed/",                                             "tier": 3, "state_affiliated": False, "category": "semiconductor","tags": ["semiconductor"]},
    {"name": "Supply Chain Dive",       "url": "https://www.supplychaindive.com/feeds/news/",                               "tier": 3, "state_affiliated": False, "category": "supply_chain","tags": ["supply_chain", "logistics"]},
    {"name": "Logistics Management",    "url": "https://www.logisticsmgmt.com/rss_feed/blogs",                              "tier": 3, "state_affiliated": False, "category": "supply_chain","tags": ["supply_chain", "logistics"]},
    {"name": "FreightWaves",            "url": "https://www.freightwaves.com/news/feed",                                    "tier": 3, "state_affiliated": False, "category": "supply_chain","tags": ["logistics", "shipping"]},
    {"name": "DC Velocity",             "url": "https://www.dcvelocity.com/rss/news",                                       "tier": 3, "state_affiliated": False, "category": "supply_chain","tags": ["supply_chain", "logistics"]},
    {"name": "Industry Week",           "url": "https://www.industryweek.com/rss.xml",                                      "tier": 3, "state_affiliated": False, "category": "manufacturing","tags": ["manufacturing", "supply_chain"]},
    {"name": "Chemical & Eng News",     "url": "https://cen.acs.org/rss/latest.xml",                                        "tier": 3, "state_affiliated": False, "category": "chemical",     "tags": ["chemical", "commodity"]},
    {"name": "Oil & Gas Journal",       "url": "https://www.ogj.com/rss.xml",                                               "tier": 3, "state_affiliated": False, "category": "energy",       "tags": ["energy", "oil"]},
    {"name": "Rigzone",                 "url": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",                       "tier": 3, "state_affiliated": False, "category": "energy",       "tags": ["energy", "oil"]},
    {"name": "Mining.com",              "url": "https://www.mining.com/feed/",                                              "tier": 3, "state_affiliated": False, "category": "mining",       "tags": ["mining", "commodity"]},
    {"name": "Steel Guru",              "url": "https://steelguru.com/rss/steel-news",                                      "tier": 3, "state_affiliated": False, "category": "metals",       "tags": ["metals", "commodity"]},
    {"name": "Fastmarkets",             "url": "https://www.fastmarkets.com/insights/rss.xml",                              "tier": 3, "state_affiliated": False, "category": "metals",       "tags": ["metals", "commodity"]},
    {"name": "Agrimoney",               "url": "https://www.agrimoney.com/rss.asp",                                         "tier": 3, "state_affiliated": False, "category": "agriculture",  "tags": ["agriculture", "commodity"]},
    {"name": "AgWeb",                   "url": "https://www.agweb.com/rss/news",                                            "tier": 3, "state_affiliated": False, "category": "agriculture",  "tags": ["agriculture", "commodity"]},
    {"name": "BioPharma Dive",          "url": "https://www.biopharmadive.com/feeds/news/",                                 "tier": 3, "state_affiliated": False, "category": "pharma",       "tags": ["pharma", "healthcare"]},
    {"name": "Pharma Technology",       "url": "https://www.pharmaceutical-technology.com/feed/",                           "tier": 3, "state_affiliated": False, "category": "pharma",       "tags": ["pharma", "healthcare"]},
    {"name": "Automotive News",         "url": "https://www.autonews.com/rss.xml",                                          "tier": 3, "state_affiliated": False, "category": "automotive",   "tags": ["automotive", "ev"]},
    {"name": "Electrek",                "url": "https://electrek.co/feed/",                                                 "tier": 3, "state_affiliated": False, "category": "automotive",   "tags": ["ev", "automotive"]},
    {"name": "The Verge",               "url": "https://www.theverge.com/rss/index.xml",                                    "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "consumer"]},
    {"name": "VentureBeat",             "url": "https://venturebeat.com/feed/",                                             "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "ai", "startup"]},
    {"name": "Cybersecurity Dive",      "url": "https://www.cybersecuritydive.com/feeds/news/",                             "tier": 3, "state_affiliated": False, "category": "cybersecurity","tags": ["cybersecurity", "tech"]},
    {"name": "Krebs on Security",       "url": "https://krebsonsecurity.com/feed/",                                         "tier": 3, "state_affiliated": False, "category": "cybersecurity","tags": ["cybersecurity"]},
    {"name": "Retail Dive",             "url": "https://www.retaildive.com/feeds/news/",                                    "tier": 3, "state_affiliated": False, "category": "retail",       "tags": ["retail", "consumer"]},
    {"name": "Food Dive",               "url": "https://www.fooddive.com/feeds/news/",                                      "tier": 3, "state_affiliated": False, "category": "food",         "tags": ["food", "supply_chain"]},
    {"name": "Shipping Watch",          "url": "https://en.shippingwatch.com/rss.xml",                                      "tier": 3, "state_affiliated": False, "category": "shipping",     "tags": ["shipping", "logistics"]},
    {"name": "Air Cargo News",          "url": "https://www.aircargonews.net/feed/",                                        "tier": 3, "state_affiliated": False, "category": "aviation",     "tags": ["aviation", "logistics"]},
    {"name": "Energy Monitor",          "url": "https://www.energymonitor.ai/feed/",                                        "tier": 3, "state_affiliated": False, "category": "energy",       "tags": ["energy", "climate"]},
    {"name": "ZDNet",                   "url": "https://www.zdnet.com/news/rss.xml",                                        "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "enterprise"]},
    {"name": "HR Dive",                 "url": "https://www.hrdive.com/feeds/news/",                                        "tier": 3, "state_affiliated": False, "category": "labor",        "tags": ["labor", "macro"]},
    {"name": "CFO Dive",                "url": "https://www.cfodive.com/feeds/news/",                                       "tier": 3, "state_affiliated": False, "category": "financial",    "tags": ["corporate", "finance"]},
    {"name": "Global Finance",          "url": "https://www.gfmag.com/feed/",                                               "tier": 3, "state_affiliated": False, "category": "financial",    "tags": ["macro", "emerging"]},
    {"name": "Semiconductor Eng",       "url": "https://semiengineering.com/feed/",                                         "tier": 3, "state_affiliated": False, "category": "semiconductor","tags": ["semiconductor"]},
    {"name": "Tom's Hardware",          "url": "https://www.tomshardware.com/feeds/all",                                    "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "semiconductor"]},
    {"name": "AnandTech",               "url": "https://www.anandtech.com/rss/",                                            "tier": 3, "state_affiliated": False, "category": "semiconductor","tags": ["semiconductor", "tech"]},
    {"name": "CNET News",               "url": "https://www.cnet.com/rss/news/",                                            "tier": 3, "state_affiliated": False, "category": "tech",         "tags": ["tech", "consumer"]},
    {"name": "Grocery Dive",            "url": "https://www.grocerydive.com/feeds/news/",                                   "tier": 3, "state_affiliated": False, "category": "retail",       "tags": ["retail", "food"]},
    {"name": "Construction Dive",       "url": "https://www.constructiondive.com/feeds/news/",                              "tier": 3, "state_affiliated": False, "category": "construction", "tags": ["construction", "commodity"]},
    {"name": "Defense News",            "url": "https://www.defensenews.com/rss/",                                          "tier": 3, "state_affiliated": False, "category": "defense",      "tags": ["defense", "geopolitical"]},
    {"name": "Breaking Defense",        "url": "https://breakingdefense.com/feed/",                                         "tier": 3, "state_affiliated": False, "category": "defense",      "tags": ["defense", "geopolitical"]},
    # ── Tier 4 — Community & Alternative ──────────────────────────────────────
    {"name": "Hacker News",             "url": "https://hnrss.org/frontpage",                                               "tier": 4, "state_affiliated": False, "category": "tech",         "tags": ["tech", "startup", "ai"]},
    {"name": "Product Hunt",            "url": "https://www.producthunt.com/feed?category=tech",                            "tier": 4, "state_affiliated": False, "category": "tech",         "tags": ["tech", "startup"]},
    {"name": "Reddit r/stocks",         "url": "https://www.reddit.com/r/stocks/.rss",                                     "tier": 4, "state_affiliated": False, "category": "financial",    "tags": ["market", "stocks"]},
    {"name": "Reddit r/investing",      "url": "https://www.reddit.com/r/investing/.rss",                                   "tier": 4, "state_affiliated": False, "category": "financial",    "tags": ["market", "stocks"]},
    {"name": "Reddit r/supplychain",    "url": "https://www.reddit.com/r/supplychain/.rss",                                 "tier": 4, "state_affiliated": False, "category": "supply_chain","tags": ["supply_chain"]},
    {"name": "Reddit r/Economics",      "url": "https://www.reddit.com/r/Economics/.rss",                                   "tier": 4, "state_affiliated": False, "category": "macro",        "tags": ["macro"]},
    {"name": "Reddit r/geopolitics",    "url": "https://www.reddit.com/r/geopolitics/.rss",                                 "tier": 4, "state_affiliated": False, "category": "geopolitical", "tags": ["geopolitical"]},
    {"name": "Wolf Street",             "url": "https://wolfstreet.com/feed/",                                              "tier": 4, "state_affiliated": False, "category": "financial",    "tags": ["market", "macro"]},
    {"name": "Calculated Risk",         "url": "https://feeds.feedburner.com/calculatedrisk",                               "tier": 4, "state_affiliated": False, "category": "macro",        "tags": ["macro", "housing"]},
    {"name": "Towards Data Science",    "url": "https://towardsdatascience.com/feed",                                       "tier": 4, "state_affiliated": False, "category": "tech",         "tags": ["ai", "quant"]},
    {"name": "AI News",                 "url": "https://www.artificialintelligence-news.com/feed/",                         "tier": 4, "state_affiliated": False, "category": "tech",         "tags": ["ai"]},
    {"name": "CoinDesk",                "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",                           "tier": 4, "state_affiliated": False, "category": "crypto",       "tags": ["crypto"]},
    {"name": "Naked Capitalism",        "url": "https://www.nakedcapitalism.com/feed",                                      "tier": 4, "state_affiliated": False, "category": "financial",    "tags": ["macro", "finance"]},
    {"name": "OpenSecrets",             "url": "https://www.opensecrets.org/news/feed/",                                    "tier": 4, "state_affiliated": False, "category": "regulatory",   "tags": ["regulatory", "political"]},
    # State-affiliated international
    {"name": "Xinhua Business",         "url": "https://www.xinhuanet.com/english/business/news_business.xml",              "tier": 4, "state_affiliated": True,  "category": "china",        "tags": ["china", "macro"]},
    {"name": "Global Times",            "url": "https://www.globaltimes.cn/rss.xml",                                        "tier": 4, "state_affiliated": True,  "category": "china",        "tags": ["china", "geopolitical"]},
    {"name": "TASS",                    "url": "https://tass.com/rss/v2.xml",                                               "tier": 4, "state_affiliated": True,  "category": "russia",       "tags": ["russia", "geopolitical"]},
    {"name": "Al Jazeera",              "url": "https://www.aljazeera.com/xml/rss/all.xml",                                  "tier": 4, "state_affiliated": True,  "category": "mideast",      "tags": ["geopolitical", "energy"]},
]

# ─── SECTOR → TAGS MAP (for portfolio-based filtering) ─────────────────────────
SECTOR_TAG_MAP: Dict[str, List[str]] = {
    "tech":         ["tech", "semiconductor", "ai", "startup"],
    "energy":       ["energy", "oil", "climate"],
    "commodity":    ["commodity", "metals", "mining", "agriculture", "chemical"],
    "financial":    ["market", "stocks", "macro", "finance", "quant", "credit"],
    "supply_chain": ["supply_chain", "logistics", "shipping", "aviation"],
    "geopolitical": ["geopolitical", "sanctions", "trade", "tariff", "defense"],
    "healthcare":   ["health", "pharma", "pandemic"],
    "macro":        ["macro", "rates", "labor", "housing", "emerging"],
    "regulatory":   ["regulatory", "corporate", "political"],
    "china":        ["china", "asia"],
    "automotive":   ["automotive", "ev"],
    "disaster":     ["disaster", "logistics"],
}


class NewsIngestionLayer:
    """
    110-source news ingestion with ETag caching, circuit breakers, and portfolio filtering.
    """

    def __init__(self):
        self._headers = {
            "User-Agent": "MarketPulse-X/2.0 (supply-chain-intelligence; support@marketpulse.ai)"
        }
        # url → {"etag": str, "last_modified": str, "entries": list}
        self._etag_cache: Dict[str, Dict] = {}
        # url → {"failures": int, "open_until": float}
        self._circuit_breaker: Dict[str, Dict] = {}
        # url → expiry timestamp (negative cache)
        self._negative_cache: Dict[str, float] = {}

    # ── Circuit Breaker ────────────────────────────────────────────────────────

    def _is_open(self, url: str) -> bool:
        """True if the circuit breaker for this url is tripped."""
        cb = self._circuit_breaker.get(url)
        if cb and cb["failures"] >= CIRCUIT_BREAKER_THRESHOLD:
            if time.time() < cb["open_until"]:
                return True
            # Cooldown expired — reset
            self._circuit_breaker[url] = {"failures": 0, "open_until": 0.0}
        return False

    def _record_success(self, url: str) -> None:
        self._circuit_breaker[url] = {"failures": 0, "open_until": 0.0}

    def _record_failure(self, url: str) -> None:
        cb = self._circuit_breaker.setdefault(url, {"failures": 0, "open_until": 0.0})
        cb["failures"] += 1
        if cb["failures"] >= CIRCUIT_BREAKER_THRESHOLD:
            cb["open_until"] = time.time() + CIRCUIT_BREAKER_COOLDOWN
            logger.warning("Circuit breaker OPEN for %s (will retry in 15 min)", url)

    # ── Negative Cache ─────────────────────────────────────────────────────────

    def _is_negative_cached(self, url: str) -> bool:
        expiry = self._negative_cache.get(url, 0.0)
        return time.time() < expiry

    def _set_negative_cache(self, url: str) -> None:
        self._negative_cache[url] = time.time() + NEGATIVE_CACHE_TTL

    # ── ETag-aware feedparser call ─────────────────────────────────────────────

    def _fetch_feed(self, source: Dict) -> List[Dict]:
        """
        Fetch one RSS/Atom feed with circuit breaker + ETag + negative cache.
        Returns list of raw article dicts.
        """
        url = source["url"]
        name = source["name"]
        tier = source["tier"]

        if self._is_open(url):
            cached = self._etag_cache.get(url, {})
            return cached.get("entries", [])

        if self._is_negative_cached(url):
            return []

        kwargs: Dict = {}
        cached = self._etag_cache.get(url, {})
        if cached.get("etag"):
            kwargs["etag"] = cached["etag"]
        if cached.get("last_modified"):
            kwargs["modified"] = cached["last_modified"]

        try:
            feed = feedparser.parse(url, request_headers=self._headers, **kwargs)

            # 304 Not Modified — serve stale
            if getattr(feed, "status", 200) == 304:
                return cached.get("entries", [])

            status = getattr(feed, "status", 200)
            if status in (404, 410, 451):
                self._set_negative_cache(url)
                self._record_failure(url)
                return []

            if not feed.entries:
                self._set_negative_cache(url)
                return []

            # Update ETag cache
            new_etag = getattr(feed, "etag", None) or getattr(feed.feed, "etag", None)
            new_modified = getattr(feed, "modified", None) or getattr(feed.feed, "updated", None)
            entries = self._parse_entries(feed.entries, source)
            self._etag_cache[url] = {
                "etag": new_etag,
                "last_modified": new_modified,
                "entries": entries,
            }
            self._record_success(url)
            return entries

        except Exception as e:
            self._record_failure(url)
            logger.warning("Feed fetch failed [%s] %s: %s", name, url, e)
            return cached.get("entries", [])

    def _parse_entries(self, entries, source: Dict) -> List[Dict]:
        name = source["name"]
        tier = source["tier"]
        state_affiliated = source["state_affiliated"]
        results = []
        for e in entries[:15]:
            title = getattr(e, "title", "") or ""
            link = getattr(e, "link", "") or ""
            summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""
            published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
            if not title or not link:
                continue
            results.append({
                "title": title,
                "url": link,
                "content": self._strip_html(summary),
                "source": name,
                "source_tier": tier,
                "state_affiliated": state_affiliated,
                "published_at": published or datetime.now(timezone.utc).isoformat(),
                "type": "rss",
            })
        return results

    # ── Portfolio-based source filtering ──────────────────────────────────────

    def _relevant_sources(self, tickers: List[str]) -> List[Dict]:
        """
        Return sources whose tags intersect with sectors inferred from tickers.
        Falls back to full catalog if no sector match found.
        """
        # Build required tags from ticker names (heuristic mapping)
        required_tags: set = set()
        ticker_upper = {t.upper() for t in tickers}

        sector_hints = {
            frozenset(["TSM", "NVDA", "AMD", "INTC", "ASML", "ARM", "QCOM", "AVGO", "MU", "MTCR", "SSNLF"]): ["tech", "semiconductor"],
            frozenset(["XOM", "CVX", "BP", "SHEL", "COP", "SLB"]): ["energy", "oil"],
            frozenset(["AAPL", "MSFT", "GOOGL", "GOOG", "META", "AMZN"]): ["tech", "market"],
            frozenset(["JPM", "BAC", "GS", "MS", "C", "WFC"]): ["financial", "market"],
            frozenset(["TSLA", "GM", "F", "RIVN", "NIO"]): ["automotive", "ev"],
            frozenset(["JNJ", "PFE", "MRNA", "ABBV", "LLY"]): ["healthcare", "pharma"],
            frozenset(["CAT", "DE", "MMM", "HON", "GE"]): ["manufacturing", "supply_chain"],
        }

        for sector_tickers, tags in sector_hints.items():
            if ticker_upper & sector_tickers:
                required_tags.update(tags)

        # Always include macro + geopolitical + supply_chain + regulatory
        required_tags.update(["macro", "geopolitical", "supply_chain", "regulatory", "sanctions", "disaster"])

        if not required_tags:
            return SOURCE_CATALOG

        return [
            s for s in SOURCE_CATALOG
            if required_tags & set(s.get("tags", []))
        ]

    # ── Utility ────────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", "", text)
        clean = clean.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')
        return " ".join(clean.split())[:500]

    # ── Official API fetchers ──────────────────────────────────────────────────

    def _fetch_newsapi(self, query: str) -> List[Dict]:
        if not NEWSAPI_KEY or self._is_open("newsapi"):
            return []
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": query, "language": "en", "sortBy": "publishedAt", "apiKey": NEWSAPI_KEY, "pageSize": 10},
                timeout=10,
            )
            data = resp.json()
            self._record_success("newsapi")
            return [{
                "title": a["title"],
                "url": a["url"],
                "content": self._strip_html(a.get("description", "")),
                "source": a["source"]["name"],
                "source_tier": 2,
                "state_affiliated": False,
                "published_at": a["publishedAt"],
                "type": "api",
            } for a in data.get("articles", []) if a.get("title")]
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            self._record_failure("newsapi")
            logger.warning("NewsAPI failed: %s", e)
            return []

    def _fetch_newsdata(self, query: str) -> List[Dict]:
        if not NEWSDATA_IO_KEY or self._is_open("newsdata"):
            return []
        try:
            resp = requests.get(
                "https://newsdata.io/api/1/news",
                params={"apikey": NEWSDATA_IO_KEY, "q": query, "language": "en"},
                timeout=10,
            )
            data = resp.json()
            self._record_success("newsdata")
            return [{
                "title": a["title"],
                "url": a["link"],
                "content": self._strip_html(a.get("description", "")),
                "source": a.get("source_id", "NewsData"),
                "source_tier": 2,
                "state_affiliated": False,
                "published_at": a.get("pubDate", ""),
                "type": "api",
            } for a in data.get("results", []) if isinstance(a, dict) and a.get("title")]
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            self._record_failure("newsdata")
            logger.warning("NewsData failed: %s", e)
            return []

    def _fetch_finnhub(self, symbol: str) -> List[Dict]:
        if not FINNHUB_API_KEY or self._is_open("finnhub"):
            return []
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            resp = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={"symbol": symbol, "from": start, "to": today, "token": FINNHUB_API_KEY},
                timeout=10,
            )
            data = resp.json()
            self._record_success("finnhub")
            return [{
                "title": a["headline"],
                "url": a["url"],
                "content": a.get("summary", ""),
                "source": a.get("source", "Finnhub"),
                "source_tier": 1,
                "state_affiliated": False,
                "published_at": datetime.fromtimestamp(a["datetime"], tz=timezone.utc).isoformat(),
                "type": "api",
            } for a in data[:10] if a.get("headline") and a.get("url")]
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            self._record_failure("finnhub")
            logger.warning("Finnhub failed for %s: %s", symbol, e)
            return []

    def _fetch_gnews(self, query: str) -> List[Dict]:
        if not GNEWS_API_KEY or self._is_open("gnews"):
            return []
        try:
            resp = requests.get(
                "https://gnews.io/api/v4/search",
                params={"q": query, "lang": "en", "token": GNEWS_API_KEY, "max": 10},
                timeout=10,
            )
            data = resp.json()
            self._record_success("gnews")
            return [{
                "title": a["title"],
                "url": a["url"],
                "content": a.get("description", ""),
                "source": a["source"]["name"],
                "source_tier": 2,
                "state_affiliated": False,
                "published_at": a["publishedAt"],
                "type": "api",
            } for a in data.get("articles", []) if a.get("title")]
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            self._record_failure("gnews")
            logger.warning("GNews failed: %s", e)
            return []

    def _fetch_mediastack(self, query: str) -> List[Dict]:
        if not MEDIASTACK_API_KEY or self._is_open("mediastack"):
            return []
        try:
            resp = requests.get(
                "http://api.mediastack.com/v1/news",
                params={"access_key": MEDIASTACK_API_KEY, "keywords": query, "languages": "en", "limit": 10},
                timeout=10,
            )
            data = resp.json()
            self._record_success("mediastack")
            return [{
                "title": a["title"],
                "url": a["url"],
                "content": self._strip_html(a.get("description", "")),
                "source": a.get("source", "MediaStack"),
                "source_tier": 2,
                "state_affiliated": False,
                "published_at": a.get("published_at", ""),
                "type": "api",
            } for a in data.get("data", []) if a.get("title")]
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            self._record_failure("mediastack")
            logger.warning("MediaStack failed: %s", e)
            return []

    # ── Dynamic per-ticker feeds ───────────────────────────────────────────────

    def _fetch_yahoo_rss(self, ticker: str) -> List[Dict]:
        source = {
            "name": f"Yahoo Finance ({ticker})",
            "url": f"https://finance.yahoo.com/rss/headline?s={ticker}",
            "tier": 2,
            "state_affiliated": False,
            "tags": ["market", "stocks"],
        }
        return self._fetch_feed(source)

    def _fetch_sec_edgar(self, ticker: str) -> List[Dict]:
        source = {
            "name": f"SEC EDGAR ({ticker})",
            "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=8-K&dateb=&owner=include&count=10&output=atom",
            "tier": 1,
            "state_affiliated": True,
            "tags": ["regulatory"],
        }
        return self._fetch_feed(source)

    def _fetch_google_news_rss(self, query: str) -> List[Dict]:
        source = {
            "name": "Google News",
            "url": f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
            "tier": 3,
            "state_affiliated": False,
            "tags": ["macro", "market"],
        }
        return self._fetch_feed(source)

    # ── Deduplication ──────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(articles: List[Dict]) -> List[Dict]:
        seen_urls: set = set()
        unique: List[Dict] = []
        for art in articles:
            url = art.get("url", "")
            if not url or url in seen_urls:
                continue
            title_words = set(re.findall(r"\w+", art.get("title", "").lower()))
            is_dup = any(
                len(title_words & set(re.findall(r"\w+", u.get("title", "").lower()))) / max(len(title_words), 1) > 0.6
                for u in unique[-50:]  # only check last 50 for speed
            )
            if not is_dup:
                seen_urls.add(url)
                unique.append(art)
        return unique

    # ── Prioritization ─────────────────────────────────────────────────────────

    @staticmethod
    def _prioritize(articles: List[Dict]) -> List[Dict]:
        # Lower tier = higher priority; break ties by recency (first seen wins)
        return sorted(articles, key=lambda a: a.get("source_tier", 4))

    # ── MAIN INGESTION WORKFLOW ────────────────────────────────────────────────

    def ingest_all(self, tickers: List[str]) -> List[Article]:
        """
        Ingest from all 110 sources relevant to the given tickers.
        Returns top 30 deduplicated, prioritized Article objects.
        """
        all_raw: List[Dict] = []
        query = " OR ".join(tickers[:3])
        primary_ticker = tickers[0] if tickers else "AAPL"

        # 1. Catalog RSS feeds (filtered to portfolio sectors)
        sources = self._relevant_sources(tickers)
        logger.info("Fetching %d/%d catalog sources for tickers %s", len(sources), len(SOURCE_CATALOG), tickers)
        for src in sources:
            all_raw.extend(self._fetch_feed(src))

        # 2. Dynamic per-ticker feeds
        for ticker in tickers[:5]:
            all_raw.extend(self._fetch_yahoo_rss(ticker))
            all_raw.extend(self._fetch_sec_edgar(ticker))

        # 3. Google News query
        all_raw.extend(self._fetch_google_news_rss(query))

        # 4. Official APIs
        all_raw.extend(self._fetch_newsapi(query))
        all_raw.extend(self._fetch_newsdata(query))
        all_raw.extend(self._fetch_finnhub(primary_ticker))
        all_raw.extend(self._fetch_gnews(query))
        all_raw.extend(self._fetch_mediastack(query))

        logger.info("Raw articles collected: %d", len(all_raw))

        # 5. Deduplicate and prioritize
        deduped = self._deduplicate(all_raw)
        ranked = self._prioritize(deduped)

        logger.info("After dedup+rank: %d articles", len(ranked))

        # 6. Build Article objects (top 30)
        final: List[Article] = []
        for a in ranked[:30]:
            final.append(Article(
                title=a["title"],
                url=a["url"],
                source=a["source"],
                published_at=datetime.now(timezone.utc),
                content=a["content"],
                companies_mentioned=tickers,
                priority=a.get("source_tier", 4),
                relevance="direct" if a.get("source_tier", 4) <= 2 else "indirect",
            ))

        return final

    def source_stats(self) -> Dict:
        """Return circuit breaker and cache stats — used by /api/health."""
        open_feeds = [
            url for url, cb in self._circuit_breaker.items()
            if cb["failures"] >= CIRCUIT_BREAKER_THRESHOLD and time.time() < cb["open_until"]
        ]
        return {
            "total_catalog": len(SOURCE_CATALOG),
            "etag_cached": len(self._etag_cache),
            "negative_cached": sum(1 for exp in self._negative_cache.values() if time.time() < exp),
            "circuit_open": len(open_feeds),
            "open_feeds": open_feeds[:10],
        }


# Singleton
news_aggregator_layer = NewsIngestionLayer()
