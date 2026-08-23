"""
Insider Trading Service — SEC Form 4 filings via EDGAR + OpenInsider.
Parses filing XML for actual buy/sell transactions with insider names, prices, shares.
"""
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions"
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data"
SEC_USER_AGENT = "MarketPulseOSINT/1.0 (contact@marketpulse.ai)"

TRANSACTION_MAP = {
    "P": "BUY",
    "S": "SELL",
    "A": "AWARD",
    "D": "DISPOSITION",
    "F": "TAX_WITHHOLDING",
    "I": "DERIVATIVE_ACQUISITION",
    "M": "OPTION_EXERCISE",
    "X": "OPTION_EXERCISE",
    "C": "CONVERSION",
    "E": "EXPIRATION",
    "G": "GIFT",
    "J": "OTHER",
    "L": "SMALL_ACQUISITION",
    "W": "WILL",
    "Z": "TRUST",
}


class InsiderTrade:
    def __init__(self, ticker: str, insider_name: str, relationship: str,
                 transaction_type: str, shares: float, price: float,
                 value: float, filing_date: str, trade_date: str):
        self.ticker = ticker
        self.insider_name = insider_name
        self.relationship = relationship
        self.transaction_type = transaction_type
        self.shares = shares
        self.price = price
        self.value = value
        self.filing_date = filing_date
        self.trade_date = trade_date

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "insider_name": self.insider_name,
            "relationship": self.relationship,
            "transaction_type": self.transaction_type,
            "shares": self.shares,
            "price": self.price,
            "value": self.value,
            "filing_date": self.filing_date,
            "trade_date": self.trade_date,
        }


class InsiderTradesService:
    def __init__(self):
        self._ticker_to_cik: dict = {}
        self._last_cik_fetch = None

    async def _ensure_cik_map(self):
        if self._ticker_to_cik and self._last_cik_fetch and \
           (datetime.now() - self._last_cik_fetch).days < 1:
            return
        try:
            url = SEC_TICKERS
            headers = {"User-Agent": SEC_USER_AGENT, "Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.values():
                        ticker = item.get("ticker", "").upper()
                        cik = str(item.get("cik_str", "")).zfill(10)
                        if ticker and cik:
                            self._ticker_to_cik[ticker] = cik
                    self._last_cik_fetch = datetime.now()
                    logger.info(f"Loaded {len(self._ticker_to_cik)} ticker→CIK mappings")
        except Exception as e:
            logger.warning(f"Failed to load CIK map: {e}")

    async def get_insider_trades(self, ticker: str, days_back: int = 90) -> list:
        ticker = ticker.upper()
        await self._ensure_cik_map()
        cik = self._ticker_to_cik.get(ticker)
        if not cik:
            logger.warning(f"No CIK found for ticker {ticker}")
            return await self._get_openinsider_fallback(ticker, days_back)

        trades = await self._get_sec_edgar_trades(ticker, cik, days_back)
        if not trades:
            trades = await self._get_openinsider_fallback(ticker, days_back)
        return trades

    async def _get_sec_edgar_trades(self, ticker: str, cik: str, days_back: int) -> list:
        trades = []
        try:
            url = f"{SEC_SUBMISSIONS}/CIK{cik}.json"
            headers = {"User-Agent": SEC_USER_AGENT, "Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                filings = data.get("filings", {}).get("recent", {})
                form_types = filings.get("form", [])
                filing_dates = filings.get("filingDate", [])
                primary_docs = filings.get("primaryDocument", [])
                accession_numbers = filings.get("accessionNumber", [])

                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

                for i, form in enumerate(form_types):
                    if form != "4":
                        continue
                    if i >= len(filing_dates) or i >= len(primary_docs) or i >= len(accession_numbers):
                        continue

                    fdate = filing_dates[i]
                    try:
                        fd = datetime.strptime(fdate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        if fd < cutoff:
                            continue
                    except ValueError:
                        continue

                    doc = primary_docs[i].split("/")[-1]
                    acc = accession_numbers[i]
                    cik_raw = str(int(cik))
                    acc_no_dashes = acc.replace("-", "")

                    doc_url = f"{SEC_ARCHIVE}/{cik_raw}/{acc_no_dashes}/{doc}"
                    parsed = await self._parse_form4_xml(ticker, doc_url)
                    trades.extend(parsed)

                    if len(trades) >= 50:
                        break

        except Exception as e:
            logger.warning(f"SEC EDGAR fetch failed for {ticker}: {e}")

        return trades

    async def _parse_form4_xml(self, ticker: str, doc_url: str) -> list:
        trades = []
        try:
            headers = {"User-Agent": SEC_USER_AGENT, "Accept": "application/xml"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(doc_url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    return []

                root = ET.fromstring(resp.content)

                def _val(el, path):
                    found = el.find(path)
                    if found is not None and found.text:
                        return found.text.strip()
                    return ""

                insider_name = "Unknown"
                relationship = ""

                owner = root.find("reportingOwner")
                if owner is not None:
                    oid = owner.find("reportingOwnerId")
                    if oid is not None:
                        name = _val(oid, "rptOwnerName")
                        if name:
                            insider_name = name
                    rel = owner.find("reportingOwnerRelationship")
                    if rel is not None:
                        if _val(rel, "isDirector") == "true":
                            relationship = "Director"
                        elif _val(rel, "isOfficer") == "true":
                            relationship = _val(rel, "officerTitle") or "Officer"
                        elif _val(rel, "isTenPercentOwner") == "true":
                            relationship = "10% Owner"
                        elif _val(rel, "isOther") == "true":
                            relationship = _val(rel, "officerTitle") or "Other"

                for table_tag in ("nonDerivativeTable", "derivativeTable"):
                    table = root.find(table_tag)
                    if table is None:
                        continue

                    for tr in table.findall("nonDerivativeTransaction" if "non" in table_tag else "derivativeTransaction"):
                        try:
                            coding = tr.find("transactionCoding")
                            ttype_code = _val(coding, "transactionCode").upper() if coding is not None else ""

                            acquired_code = ""
                            amounts = tr.find("transactionAmounts")
                            shares = 0
                            price = 0
                            if amounts is not None:
                                ts = amounts.find("transactionShares")
                                if ts is not None:
                                    sv = _val(ts, "value") or (ts.text or "0")
                                    shares = float(sv.replace(",", ""))
                                tp = amounts.find("transactionPricePerShare")
                                if tp is not None:
                                    pv = _val(tp, "value") or (tp.text or "0")
                                    try:
                                        price = float(pv.replace(",", ""))
                                    except ValueError:
                                        price = 0
                                adc = amounts.find("transactionAcquiredDisposedCode")
                                if adc is not None:
                                    acquired_code = _val(adc, "value") or ""

                            trade_date = ""
                            td = tr.find("transactionDate")
                            if td is not None:
                                trade_date = _val(td, "value") or (td.text or "")

                            human_type = TRANSACTION_MAP.get(ttype_code, ttype_code)

                            if human_type in ("BUY", "SELL") and shares > 0:
                                trades.append(InsiderTrade(
                                    ticker=ticker,
                                    insider_name=insider_name,
                                    relationship=relationship,
                                    transaction_type=human_type,
                                    shares=shares,
                                    price=price,
                                    value=shares * price,
                                    filing_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                    trade_date=trade_date,
                                ).to_dict())
                        except (ValueError, AttributeError):
                            continue

        except ET.ParseError:
            pass
        except Exception as e:
            logger.debug(f"Form 4 XML parse error for {ticker}: {e}")

        return trades

    async def _get_openinsider_fallback(self, ticker: str, days_back: int) -> list:
        try:
            url = f"http://openinsider.com/screener?s={ticker}"
            headers = {"User-Agent": "Mozilla/5.0"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=15, follow_redirects=True)
                if resp.status_code != 200:
                    return []

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                table = soup.find("table", class_="tinytable")
                if not table:
                    return []

                rows = table.find_all("tr")[1:]
                trades = []
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

                for row in rows[:30]:
                    cols = row.find_all("td")
                    if len(cols) < 12:
                        continue

                    try:
                        tds = [c.get_text(strip=True) for c in cols]
                        trade_date_str = tds[1] if len(tds) > 1 else ""
                        filing_date_str = tds[2] if len(tds) > 2 else ""
                        insider = tds[4] if len(tds) > 4 else "Unknown"
                        rel = tds[5] if len(tds) > 5 else ""
                        ttype = tds[7] if len(tds) > 7 else ""
                        shares_str = tds[8] if len(tds) > 8 else "0"
                        price_str = tds[9] if len(tds) > 9 else "0"

                        try:
                            fd = datetime.strptime(filing_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                            if fd < cutoff:
                                continue
                        except ValueError:
                            continue

                        shares = float(shares_str.replace(",", "")) if re.match(r'^[\d.,-]+$', shares_str) else 0
                        price = float(price_str.replace("$", "").replace(",", "")) if re.match(r'^[\d.,$-]+$', price_str) else 0

                        trades.append(InsiderTrade(
                            ticker=ticker,
                            insider_name=insider,
                            relationship=rel,
                            transaction_type=ttype.upper(),
                            shares=abs(shares),
                            price=price,
                            value=abs(shares) * price,
                            filing_date=filing_date_str,
                            trade_date=trade_date_str,
                        ).to_dict())
                    except (ValueError, IndexError):
                        continue

                return trades
        except Exception as e:
            logger.warning(f"OpenInsider fallback failed for {ticker}: {e}")
            return []

    def score_insider_activity(self, trades: list) -> float:
        if not trades:
            return 0.0

        score = 0.0
        buy_count = 0
        sell_count = 0
        buy_value = 0.0
        sell_value = 0.0

        for t in trades:
            ttype = t.get("transaction_type", "")
            value = t.get("value", 0)
            shares = t.get("shares", 0)
            relationship = t.get("relationship", "")

            officer_weight = 1.5 if "officer" in relationship.lower() or "CEO" in relationship.upper() else 1.0
            director_weight = 1.2 if "director" in relationship.lower() else 1.0
            weight = officer_weight * director_weight

            if "BUY" in ttype or "PURCHASE" in ttype or "ACQUIRE" in ttype:
                buy_count += 1
                buy_value += value * weight
            elif "SELL" in ttype or "DISPOSITION" in ttype:
                sell_count += 1
                sell_value += value * weight

        total = buy_count + sell_count
        if total == 0:
            return 0.0

        net_ratio = (buy_count - sell_count) / total
        score += net_ratio * 3.0

        if buy_value > 5000000:
            score += 2.0
        elif buy_value > 1000000:
            score += 1.5
        elif buy_value > 500000:
            score += 1.0
        elif buy_value > 100000:
            score += 0.5

        if sell_value > 10000000:
            score -= 1.5
        elif sell_value > 5000000:
            score -= 1.0
        elif sell_value > 1000000:
            score -= 0.5

        cluster_bonus = 0
        if buy_count >= 3:
            cluster_bonus += 0.5
        if sell_count >= 3:
            cluster_bonus -= 0.5

        score += cluster_bonus

        return max(-5.0, min(5.0, score))


insider_trades_service = InsiderTradesService()
