from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RelationshipFusion:
    def __init__(self):
        # Base confidence levels per source (Spec v3.0)
        self.SOURCE_CONFIDENCES = {
            "sec_edgar": 0.92,
            "news_report": 0.70,
            "company_website": 0.65,
            "llm_inference": 0.45
        }

    def fuse(self, relationships: List[Dict]) -> List[Dict]:
        """
        Merge relationships from multiple sources.
        Logic:
        - If multiple sources confirm the same relationship, boost confidence by 15%.
        - Standardize names to prevent duplicates.
        """
        if not relationships:
            return []

        fused = {}
        for rel in relationships:
            key = f"{rel['related_company'].upper()}:{rel['type'].upper()}"
            if key not in fused:
                fused[key] = {
                    "related_company": rel['related_company'],
                    "type": rel['type'],
                    "criticality": rel['criticality'],
                    "evidence": [rel.get('evidence', '')],
                    "sources": [rel.get('source', 'unknown')],
                    "confidence": rel.get('confidence', 0.5)
                }
            else:
                # Relationship already exists, boost confidence
                fused[key]["confidence"] = min(0.99, fused[key]["confidence"] + 0.15)
                fused[key]["sources"].append(rel.get('source', 'unknown'))
                if rel.get('evidence'):
                    fused[key]["evidence"].append(rel['evidence'])
                    
                # Take the highest criticality if they differ
                # (Critical > High > Medium > Low)
                crit_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
                current_crit = fused[key]["criticality"].lower()
                new_crit = rel['criticality'].lower()
                if crit_rank.get(new_crit, 0) > crit_rank.get(current_crit, 0):
                    fused[key]["criticality"] = rel['criticality']

        return list(fused.values())

relationship_fusion = RelationshipFusion()
