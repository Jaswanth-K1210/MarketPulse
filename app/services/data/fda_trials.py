"""
FDA / Clinical Trials Service — ClinicalTrials.gov API.
Tracks trial phases, status changes, drug pipeline progress.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CT_GOV_BASE = "https://clinicaltrials.gov/api/query/full_studies"


class FDATrialsService:
    async def get_trials(self, company: str, limit: int = 20) -> dict:
        result = {
            "company": company,
            "trials": [],
            "total_trials": 0,
            "phase_distribution": {},
            "status_distribution": {},
            "recent_milestones": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            params = {
                "expr": f"sponsor:{company} OR lead_sponsor:{company}",
                "min_rnk": 1,
                "max_rnk": limit,
                "fmt": "json",
            }

            async with httpx.AsyncClient() as client:
                resp = await client.get(CT_GOV_BASE, params=params, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"ClinicalTrials.gov API error: {resp.status_code}")
                    return result

                data = resp.json()
                studies = data.get("FullStudiesResponse", {}).get("FullStudy", [])

                for study in studies:
                    info = study.get("Study", {})
                    protocol = info.get("ProtocolSection", {})
                    id_module = protocol.get("IdentificationModule", {})
                    status_module = protocol.get("StatusModule", {})
                    design_module = protocol.get("DesignModule", {})

                    nct_id = id_module.get("NCTId", "")
                    title = id_module.get("BriefTitle", "")
                    phase = design_module.get("Phase", "")
                    status = status_module.get("OverallStatus", "")
                    start_date = status_module.get("StartDateStruct", {}).get("StartDate", "")
                    completion_date = status_module.get("PrimaryCompletionDateStruct", {}).get("PrimaryCompletionDate", "")

                    trial = {
                        "nct_id": nct_id,
                        "title": title,
                        "phase": phase,
                        "status": status,
                        "start_date": start_date,
                        "completion_date": completion_date,
                        "source": "clinicaltrials.gov",
                    }
                    result["trials"].append(trial)

                result["total_trials"] = len(result["trials"])

                phases = {}
                statuses = {}
                for t in result["trials"]:
                    p = t.get("phase", "Unknown")
                    phases[p] = phases.get(p, 0) + 1
                    s = t.get("status", "Unknown")
                    statuses[s] = statuses.get(s, 0) + 1

                result["phase_distribution"] = phases
                result["status_distribution"] = statuses

                milestones = []
                for t in result["trials"]:
                    if t.get("status") in ("Active, not recruiting", "Completed"):
                        milestones.append({
                            "nct_id": t["nct_id"],
                            "title": t["title"][:100],
                            "milestone": t["status"],
                            "phase": t["phase"],
                        })
                result["recent_milestones"] = milestones[:5]

        except Exception as e:
            logger.warning(f"ClinicalTrials.gov fetch failed: {e}")

        return result

    def score_fda_pipeline(self, data: dict) -> float:
        score = 0.0
        trials = data.get("trials", [])

        if not trials:
            return 0.0

        late_phase = sum(1 for t in trials if "Phase 3" in t.get("phase", "") or "Phase 4" in t.get("phase", ""))
        completed = sum(1 for t in trials if t.get("status") == "Completed")
        active = sum(1 for t in trials if "recruiting" in t.get("status", "").lower() or "active" in t.get("status", "").lower())

        if late_phase >= 2:
            score += 2.0
        elif late_phase >= 1:
            score += 1.0

        if completed >= 3:
            score += 1.5
        elif completed >= 1:
            score += 0.5

        if active >= 3:
            score += 1.0
        elif active >= 1:
            score += 0.5

        total = data.get("total_trials", 0)
        if total > 10:
            score += 0.5

        return max(-5.0, min(5.0, score))


fda_trials_service = FDATrialsService()
