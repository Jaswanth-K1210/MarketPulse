import requests
import logging
import json
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from app.services.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class SECParser:
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()
        self.ticker_to_cik = {}
        self._load_ticker_map()

    def _load_ticker_map(self):
        """SEC provides a JSON mapping of all tickers to CIKs."""
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {"User-Agent": "MarketPulse Support (support@marketpulse.ai)"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for key, val in data.items():
                    self.ticker_to_cik[val['ticker'].upper()] = str(val['cik_str']).zfill(10)
            logger.info(f"Loaded {len(self.ticker_to_cik)} ticker-to-CIK mappings.")
        except Exception as e:
            logger.error(f"Failed to load SEC ticker map: {e}")

    def get_cik(self, ticker: str) -> Optional[str]:
        return self.ticker_to_cik.get(ticker.upper())

    def fetch_latest_10k_text(self, ticker: str) -> Optional[str]:
        """Fetch the business and risk sections of the latest 10-K for a ticker."""
        cik = self.get_cik(ticker)
        if not cik:
            logger.warning(f"CIK not found for ticker: {ticker}")
            return None

        try:
            # 1. Get List of Submissions
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            headers = {"User-Agent": "MarketPulse Support (support@marketpulse.ai)"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            recent = data.get('filings', {}).get('recent', {})
            
            # Find the latest 10-K
            forms = recent.get('form', [])
            idx = -1
            for i, form in enumerate(forms):
                if form == '10-K':
                    idx = i
                    break
            
            if idx == -1:
                return None
            
            acc_num = recent.get('accessionNumber', [])[idx].replace('-', '')
            primary_doc = recent.get('primaryDocument', [])[idx]
            
            # 2. Fetch the actual document (HTML)
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num}/{primary_doc}"
            doc_resp = requests.get(doc_url, headers=headers, timeout=15)
            if doc_resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(doc_resp.content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            
            # Extract relevant sections (Business, Risk Factors)
            # Use regex to find "Item 1. Business" and "Item 1A. Risk Factors"
            # This is a heuristic; real 10-K parsing is complex
            business_start = re.search(r"Item 1\.\s+Business", text, re.IGNORECASE)
            risk_start = re.search(r"Item 1A\.\s+Risk Factors", text, re.IGNORECASE)
            legal_start = re.search(r"Item 3\.\s+Legal Proceedings", text, re.IGNORECASE)
            
            content = ""
            if business_start and risk_start:
                content += text[business_start.start():risk_start.start()]
            if risk_start and legal_start:
                content += text[risk_start.start():legal_start.start()]
                
            return content if len(content) > 500 else text[:10000] # Fallback to first 10k chars
            
        except Exception as e:
            logger.error(f"Error fetching 10-K for {ticker}: {e}")
            return None

    def extract_relationships(self, ticker: str) -> List[Dict]:
        """Use Gemini to extract structured relationships from 10-K text."""
        text = self.fetch_latest_10k_text(ticker)
        if not text:
            return []

        prompt = f"""
        Analyze the following excerpt from a 10-K filing for {ticker}.
        Extract all significant supply chain relationships (Suppliers, Customers, Strategic Partners).
        For each relationship, provide:
        1. Related Company Name
        2. Relationship Type (Supplier, Customer, Partner)
        3. Criticality (Critical, High, Medium, Low)
        4. Evidence (brief quote or reasoning)
        
        Text: {text[:8000]}
        
        Return ONLY valid JSON format:
        [
            {{"related_company": "NAME", "type": "supplier|customer|partner", "criticality": "LEVEL", "evidence": "REASON"}}
        ]
        """
        
        try:
            # We assume gemini_client has a method to get structured JSON
            # For Phase 3 implementation, we parse the response
            response_text = self.gemini_client.generate_content(prompt).text
            # Clean JSON if LLM adds backticks
            response_text = re.sub(r'^```json\s*|\s*```$', '', response_text.strip(), flags=re.MULTILINE)
            rels = json.loads(response_text)
            for r in rels:
                r["source"] = "sec_edgar"
                r["confidence"] = 0.92
            return rels
        except Exception as e:
            logger.error(f"LLM extraction failed for {ticker}: {e}")
            return []

sec_parser = SECParser()
