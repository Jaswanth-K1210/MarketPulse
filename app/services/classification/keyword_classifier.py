"""
Keyword Pre-Classifier — Zero-cost, zero-latency classification for ~80% of headlines.
Ported from WorldMonitor's 4-tier keyword matching system.

This runs BEFORE any LLM call. If it returns a result, no LLM is needed.
If it returns None, the article is ambiguous and needs LLM classification.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# EXCLUSION LIST — Irrelevant content that should never trigger alerts
# ============================================================
EXCLUSION_KEYWORDS = [
    "fantasy football", "box office", "grammy", "oscars", "super bowl",
    "world cup final score", "nba draft", "nfl draft", "premier league table",
    "bachelor", "bachelorette", "kardashian", "tiktok dance", "recipe",
    "horoscope", "zodiac", "celebrity wedding", "celebrity divorce",
    "red carpet", "fashion week", "dating show", "reality tv",
    "cooking show", "wellness tip", "yoga pose", "meditation guide",
    "video game release", "movie review", "album review", "book review",
    "pet adoption", "gardening tip", "home decor", "diy craft",
    "strikes deal",  # "strikes a deal" is business, not military
]

# ============================================================
# CRITICAL TIER — Immediate global significance
# ============================================================
CRITICAL_KEYWORDS = [
    "nuclear strike", "nuclear attack", "nuclear war", "nuclear detonation",
    "declaration of war", "declares war", "declared war",
    "martial law declared", "martial law imposed",
    "coup d'etat", "military coup", "government overthrown",
    "ethnic cleansing", "genocide", "mass execution",
    "chemical attack", "chemical weapon", "biological weapon",
    "dirty bomb", "radiological weapon",
    "nato article 5", "article 5 invoked",
    "major combat operations", "full-scale invasion",
    "nuclear missile launch", "icbm launch",
    "city destroyed", "capital seized", "government collapsed",
]

# ============================================================
# HIGH TIER — Significant geopolitical/economic impact
# ============================================================
HIGH_KEYWORDS = [
    "airstrike", "airstrikes", "drone strike", "missile strike",
    "missile launch", "ballistic missile", "cruise missile",
    "bombing", "bombed", "car bomb", "suicide bomb",
    "mass casualties", "hundreds killed", "thousands killed",
    "cyber attack", "cyberattack", "critical infrastructure hack",
    "sanctions imposed", "economic sanctions", "trade embargo",
    "invasion", "invaded", "troops deployed", "military incursion",
    "ceasefire violated", "ceasefire collapsed",
    "earthquake magnitude", "tsunami warning", "category 5 hurricane",
    "pandemic declared", "new pandemic", "global health emergency",
    "nuclear plant", "meltdown", "radiation leak",
    "bank collapse", "financial crisis", "market crash",
    "default on debt", "sovereign default",
    "assassination", "leader assassinated", "president killed",
    "hostage crisis", "terrorist attack", "mass shooting",
    "famine declared", "humanitarian catastrophe",
]

# ============================================================
# MEDIUM TIER — Regional/sector significance
# ============================================================
MEDIUM_KEYWORDS = [
    "protest", "protests", "mass protest", "anti-government protest",
    "riot", "riots", "civil unrest", "looting",
    "military exercise", "military drill", "naval exercise",
    "diplomatic crisis", "ambassador recalled", "embassy closed",
    "trade war", "tariff imposed", "retaliatory tariff",
    "inflation spike", "hyperinflation", "stagflation",
    "flood", "floods", "flooding", "hurricane", "typhoon", "cyclone",
    "wildfire", "wildfires", "forest fire",
    "oil spill", "pipeline explosion", "refinery fire",
    "strike action", "general strike", "workers strike",
    "supply chain disruption", "port shutdown", "shipping blockade",
    "interest rate hike", "rate cut", "emergency rate",
    "government shutdown", "political crisis",
    "data breach", "ransomware attack", "zero-day exploit",
    "factory shutdown", "production halt", "chip shortage",
]

# ============================================================
# LOW TIER — Noteworthy but not urgent
# ============================================================
LOW_KEYWORDS = [
    "election", "elections", "polling shows", "voter turnout",
    "treaty signed", "trade agreement", "peace talks",
    "climate change", "carbon emissions", "net zero",
    "vaccine", "vaccination", "clinical trial",
    "interest rate", "fed meeting", "central bank",
    "ipo", "initial public offering", "spac merger",
    "merger", "acquisition", "buyout",
    "earnings report", "quarterly results", "revenue growth",
    "layoffs", "job cuts", "restructuring",
    "regulatory approval", "fda approval", "antitrust",
    "new legislation", "bill passed", "executive order",
]

# Short keywords that need word-boundary matching to avoid false positives
BOUNDARY_KEYWORDS = {"war", "coup", "riot", "bomb", "fire", "flood", "hack", "crash"}

# ============================================================
# CATEGORY INFERENCE
# ============================================================
CATEGORY_PATTERNS = {
    "conflict": re.compile(
        r'(war|strike|bomb|attack|missile|troops|military|invasion|'
        r'casualties|killed|assassination|hostage|terror)', re.IGNORECASE
    ),
    "geopolitical": re.compile(
        r'(sanctions|embargo|diplomat|ambassador|treaty|nato|'
        r'coup|martial law|government)', re.IGNORECASE
    ),
    "economic": re.compile(
        r'(inflation|rate|fed|bank|market|crash|default|debt|'
        r'earnings|revenue|trade war|tariff|gdp)', re.IGNORECASE
    ),
    "natural_disaster": re.compile(
        r'(earthquake|tsunami|hurricane|typhoon|cyclone|flood|'
        r'wildfire|volcano|tornado)', re.IGNORECASE
    ),
    "cyber": re.compile(
        r'(cyber|hack|breach|ransomware|zero-day|infrastructure hack)', re.IGNORECASE
    ),
    "health": re.compile(
        r'(pandemic|epidemic|outbreak|virus|vaccine|WHO|health emergency)', re.IGNORECASE
    ),
    "supply_chain": re.compile(
        r'(supply chain|shipping|port|factory|production halt|shortage|chip)', re.IGNORECASE
    ),
    "technology": re.compile(
        r'(ai |artificial intelligence|quantum|semiconductor|tech|startup)', re.IGNORECASE
    ),
    "energy": re.compile(
        r'(oil|gas|opec|pipeline|refinery|nuclear plant|renewable|solar|wind)', re.IGNORECASE
    ),
}

# Compound escalation patterns (HIGH → CRITICAL if combined with specific targets)
ESCALATION_PATTERNS = [
    (
        re.compile(r'\b(attack|strike|bomb|missile)\b', re.IGNORECASE),
        re.compile(r'\b(iran|russia|china|nato|us base|israel|nuclear)\b', re.IGNORECASE),
    ),
    (
        re.compile(r'\b(invad|invasion|troops)\b', re.IGNORECASE),
        re.compile(r'\b(taiwan|ukraine|nato|south korea|japan)\b', re.IGNORECASE),
    ),
]


def infer_category(text: str) -> str:
    """Infer the category from text using pattern matching."""
    for category, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(text):
            return category
    return "general"


def _check_keywords(text: str, keywords: list[str]) -> bool:
    """Check if any keyword matches in text, with boundary awareness for short words."""
    lower = text.lower()
    for kw in keywords:
        if kw in BOUNDARY_KEYWORDS:
            if re.search(rf'\b{re.escape(kw)}\b', lower):
                return True
        elif kw in lower:
            return True
    return False


def _check_escalation(text: str) -> bool:
    """Check compound escalation patterns (HIGH → CRITICAL)."""
    for pattern_a, pattern_b in ESCALATION_PATTERNS:
        if pattern_a.search(text) and pattern_b.search(text):
            return True
    return False


def classify_by_keywords(headline: str) -> Optional[dict]:
    """
    Classify a headline using keyword matching.

    Returns:
        dict with {level, category, confidence, source} or None if ambiguous.
        None means "needs LLM classification".
    """
    if not headline or len(headline.strip()) < 5:
        return None

    lower = headline.lower().strip()

    # 1. Exclusion check — reject irrelevant content
    for kw in EXCLUSION_KEYWORDS:
        if kw in lower:
            return {
                "level": "info",
                "category": "entertainment",
                "confidence": 0.9,
                "source": "keyword_exclusion",
            }

    # 2. Critical tier
    if _check_keywords(headline, CRITICAL_KEYWORDS):
        return {
            "level": "critical",
            "category": infer_category(headline),
            "confidence": 0.85,
            "source": "keyword_critical",
        }

    # 3. Compound escalation check (HIGH keywords + sensitive targets → CRITICAL)
    if _check_escalation(headline):
        return {
            "level": "critical",
            "category": infer_category(headline),
            "confidence": 0.80,
            "source": "keyword_escalation",
        }

    # 4. High tier
    if _check_keywords(headline, HIGH_KEYWORDS):
        return {
            "level": "high",
            "category": infer_category(headline),
            "confidence": 0.75,
            "source": "keyword_high",
        }

    # 5. Medium tier
    if _check_keywords(headline, MEDIUM_KEYWORDS):
        return {
            "level": "medium",
            "category": infer_category(headline),
            "confidence": 0.70,
            "source": "keyword_medium",
        }

    # 6. Low tier
    if _check_keywords(headline, LOW_KEYWORDS):
        return {
            "level": "low",
            "category": infer_category(headline),
            "confidence": 0.65,
            "source": "keyword_low",
        }

    # 7. No match — needs LLM
    return None


def classify_batch(headlines: list[str]) -> tuple[list[dict], list[str]]:
    """
    Classify a batch of headlines. Returns (classified, needs_llm).

    Args:
        headlines: List of headline strings

    Returns:
        Tuple of (list of classified results, list of headlines that need LLM)
    """
    classified = []
    needs_llm = []

    for headline in headlines:
        result = classify_by_keywords(headline)
        if result is not None:
            result["headline"] = headline
            classified.append(result)
        else:
            needs_llm.append(headline)

    logger.info(
        f"Keyword classifier: {len(classified)} classified, "
        f"{len(needs_llm)} need LLM ({len(classified)/(len(headlines) or 1)*100:.0f}% hit rate)"
    )

    return classified, needs_llm
