"""Relevance Scoring and AI Rules Capture Adapter."""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from core.contract import DestinationConfig


# IncuBrix target audiences
INCUBRIX_AUDIENCES = {"ai", "video", "marketing", "saas", "creators", "founders", "developer", "engineering"}


class RuleProposal(BaseModel):
    frequency_cap: str
    self_promo_allowed: bool
    link_policy: str
    disclosure_required: bool
    automation_allowed: bool
    quoted_sources: List[str]
    status: str = "proposed"  # proposed | confirmed


class RelevanceScorer:
    @staticmethod
    def score_destination(
        name: str,
        category: Optional[str],
        audience_tags: List[str],
        est_audience: int = 0,
    ) -> (int, str):
        """Scores 1-5 against IncuBrix's audience: AI, video, marketing, SaaS, creators, founders."""
        text = f"{name} {category or ''} {' '.join(audience_tags)}".lower()
        matched = [a for a in INCUBRIX_AUDIENCES if a in text]

        score = 1
        if len(matched) >= 3 or ("ai" in matched and "saas" in matched):
            score = 5
        elif len(matched) == 2:
            score = 4
        elif len(matched) == 1:
            score = 3
        else:
            if est_audience > 50000:
                score = 2
            else:
                score = 1

        reason = f"Audience matches {len(matched)} IncuBrix target sectors ({', '.join(matched) if matched else 'general'})."
        return score, reason


class RulesCaptureAIAdapter:
    @staticmethod
    def capture_rules_from_text(rules_page_text: str) -> RuleProposal:
        """Heuristic/mock AI adapter parsing community rules page text into structured rules with quotes."""
        text = rules_page_text.lower()
        quoted = []

        # 1. Self-promotion
        promo_allowed = True
        if "no self promotion" in text or "no ads" in text or "no promotional links" in text:
            promo_allowed = False
            quoted.append("Rule: No self promotion or promotional spam allowed.")

        # 2. Link policy
        link_policy = "allowed"
        if "no external links" in text:
            link_policy = "no_links"
            quoted.append("Rule: No external links allowed in posts.")
        elif "max 1 link" in text or "one link per post" in text:
            link_policy = "max_1_link"
            quoted.append("Rule: Only one link per post is permitted.")

        # 3. AI disclosure
        disclosure_required = False
        if "ai" in text and ("disclose" in text or "label" in text or "disclosure required" in text):
            disclosure_required = True
            quoted.append("Rule: AI-generated content must be clearly disclosed.")

        # 4. Automation
        automation_allowed = True
        if "no bots" in text or "no automated posting" in text or "manual only" in text:
            automation_allowed = False
            quoted.append("Rule: Automated bot posting is prohibited; humans only.")

        # 5. Frequency cap
        frequency_cap = "1 per 7 days"
        cap_match = re.search(r"(\d+\s+per\s+\d+\s+days?)", text)
        if cap_match:
            frequency_cap = cap_match.group(1)
            quoted.append(f"Frequency limit: {frequency_cap}")

        return RuleProposal(
            frequency_cap=frequency_cap,
            self_promo_allowed=promo_allowed,
            link_policy=link_policy,
            disclosure_required=disclosure_required,
            automation_allowed=automation_allowed,
            quoted_sources=quoted or ["Standard community guidelines analyzed."],
            status="proposed",
        )
