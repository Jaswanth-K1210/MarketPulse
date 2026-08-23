"""
FDA / Clinical Trials Service — ClinicalTrials.gov API v2.
Tracks trial phases, status changes, drug pipeline progress.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# v1 (/api/query/full_studies) was retired and now returns 404.
CT_GOV_BASE = "https://clinicaltrials.gov/api/v2/studies"

_FIELDS = ",".join([
    "NCTId", "BriefTitle", "OverallStatus", "Phase",
    "StartDate", "PrimaryCompletionDate", "LeadSponsorName",
])

# v2 returns SCREAMING_SNAKE enums; the scorer and UI expect title case.
_STATUS_MAP = {
    "ACTIVE_NOT_RECRUITING": "Active, not recruiting",
    "COMPLETED": "Completed",
    "RECRUITING": "Recruiting",
    "NOT_YET_RECRUITING": "Not yet recruiting",
    "ENROLLING_BY_INVITATION": "Enrolling by invitation",
    "SUSPENDED": "Suspended",
    "TERMINATED": "Terminated",
    "WITHDRAWN": "Withdrawn",
    "UNKNOWN": "Unknown status",
}


def _norm_status(raw: str) -> str:
    if not raw:
        return ""
    return _STATUS_MAP.get(raw, raw.replace("_", " ").title())


def _norm_phases(raw: list) -> str:
    """['PHASE2','PHASE3'] -> 'Phase 2/Phase 3'; ['NA'] -> 'N/A'."""
    if not raw:
        return ""
    out = []
    for ph in raw:
        if ph in ("NA", "NOT_APPLICABLE"):
            out.append("N/A")
        elif ph.startswith("PHASE"):
            out.append("Phase " + ph.replace("PHASE", "").strip())
        elif ph == "EARLY_PHASE1":
            out.append("Early Phase 1")
        else:
            out.append(ph.replace("_", " ").title())
    return "/".join(out)


class FDATrialsService:
    async def get_trials(self, company: str, limit: int = 20) -> dict:
        result = {
            "company": company,
            "trials": [],
            "total_trials": 0,
            "phase_distribution": {},
            "status_distribution": {},
            "recent_milestones": [],
            "available": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            params = {
                "query.lead": company,
                "pageSize": min(limit, 100),
                "fields": _FIELDS,
            }

            async with httpx.AsyncClient() as client:
                resp = await client.get(CT_GOV_BASE, params=params, timeout=20)
                if resp.status_code != 200:
                    logger.warning("ClinicalTrials.gov API error: %s", resp.status_code)
                    result["error"] = f"ClinicalTrials.gov returned HTTP {resp.status_code}"
                    return result

                studies = resp.json().get("studies", [])
                result["available"] = True

                for study in studies:
                    protocol = study.get("protocolSection", {})
                    id_module = protocol.get("identificationModule", {})
                    status_module = protocol.get("statusModule", {})
                    design_module = protocol.get("designModule", {})
                    sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

                    result["trials"].append({
                        "nct_id": id_module.get("nctId", ""),
                        "title": id_module.get("briefTitle", ""),
                        "phase": _norm_phases(design_module.get("phases", [])),
                        "status": _norm_status(status_module.get("overallStatus", "")),
                        "start_date": status_module.get("startDateStruct", {}).get("date", ""),
                        "completion_date": status_module.get("primaryCompletionDateStruct", {}).get("date", ""),
                        "sponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
                        "url": f"https://clinicaltrials.gov/study/{id_module.get('nctId', '')}",
                        "source": "clinicaltrials.gov",
                    })

                result["total_trials"] = len(result["trials"])

                phases = {}
                statuses = {}
                for t in result["trials"]:
                    p = t.get("phase") or "Unknown"
                    phases[p] = phases.get(p, 0) + 1
                    s = t.get("status") or "Unknown"
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
            logger.warning("ClinicalTrials.gov fetch failed: %s", e)
            result["error"] = str(e)

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
