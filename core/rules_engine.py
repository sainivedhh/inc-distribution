"""Posting Rules Engine verifying compliance before publication."""

import re
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.contract import ContentRendition, DestinationConfig, ViolationItem
from core.models import DestinationModel, PublicationRecord
from core.errors import IncuBrixError, ErrorCode


class RuleEngineResult:
    def __init__(self, passed: bool, violations: List[ViolationItem], retry_after_seconds: Optional[int] = None):
        self.passed = passed
        self.violations = violations
        self.retry_after_seconds = retry_after_seconds


class PostingRulesEngine:
    @staticmethod
    def parse_frequency_cap_seconds(cap_str: str) -> int:
        """Parses frequency cap string (e.g. '1 per 7 days', '2 per 24 hours') into window seconds."""
        if not cap_str:
            return 7 * 86400
        match = re.search(r"(\d+)\s+per\s+(\d+)\s+(day|hour|week|minute)s?", cap_str, re.IGNORECASE)
        if match:
            count = int(match.group(1))
            num = int(match.group(2))
            unit = match.group(3).lower()
            if unit == "minute":
                return (num * 60) // count
            elif unit == "hour":
                return (num * 3600) // count
            elif unit == "day":
                return (num * 86400) // count
            elif unit == "week":
                return (num * 7 * 86400) // count
        return 7 * 86400

    @classmethod
    async def evaluate_rules(
        cls,
        rendition: ContentRendition,
        destination: DestinationConfig,
        db: Optional[AsyncSession] = None,
        now: Optional[datetime] = None,
    ) -> RuleEngineResult:
        violations: List[ViolationItem] = []
        current_time = now or datetime.utcnow()
        retry_after = None

        # 1. Frequency Cap Check
        if db and destination.destination_id:
            cap_seconds = cls.parse_frequency_cap_seconds(destination.frequency_cap or "1 per 7 days")
            window_start = current_time - timedelta(seconds=cap_seconds)
            stmt = select(PublicationRecord).where(
                PublicationRecord.destination_id == destination.destination_id,
                PublicationRecord.created_at >= window_start,
                PublicationRecord.status.in_(["published", "pending"]),
            ).order_by(PublicationRecord.created_at.desc())
            res = await db.execute(stmt)
            recent_post = res.scalars().first()
            if recent_post:
                elapsed = (current_time - recent_post.created_at).total_seconds()
                wait_seconds = max(1, int(cap_seconds - elapsed))
                retry_after = wait_seconds
                violations.append(
                    ViolationItem(
                        field="frequency_cap",
                        message=f"Destination frequency cap of '{destination.frequency_cap}' reached. Next post allowed in {wait_seconds} seconds.",
                        rule="frequency_cap",
                        severity="error",
                    )
                )

        # 2. Self-Promotion Policy
        if not destination.self_promo_allowed:
            promo_keywords = ["buy now", "discount", "offer", "sale", "pricing", "sign up today", "coupon", "special promo"]
            content_lower = f"{rendition.title or ''} {rendition.body}".lower()
            matched = [k for k in promo_keywords if k in content_lower]
            if matched:
                violations.append(
                    ViolationItem(
                        field="body",
                        message=f"Self-promotion is strictly banned in destination '{destination.name}'. Detected promotional keywords: {matched}",
                        rule="self_promo_allowed",
                        severity="error",
                    )
                )

        # 3. Link Policy
        link_policy = (destination.link_policy or "allowed").lower()
        has_links = bool(re.search(r"https?://\S+", rendition.body))
        if link_policy == "no_links" and has_links:
            violations.append(
                ViolationItem(
                    field="body",
                    message="External links are strictly prohibited by this destination's link policy.",
                    rule="link_policy_no_links",
                    severity="error",
                )
            )
        elif link_policy == "max_1_link":
            links = re.findall(r"https?://\S+", rendition.body)
            if len(links) > 1:
                violations.append(
                    ViolationItem(
                        field="body",
                        message=f"Link policy allows at most 1 link, but found {len(links)} links.",
                        rule="link_policy_max_links",
                        severity="error",
                    )
                )

        # 4. AI Content Disclosure Requirement
        if destination.disclosure_required:
            disclosure_patterns = ["[ai-generated]", "[ai-assisted", "ai disclosure", "generated by ai", "assisted by ai"]
            content_lower = f"{rendition.body} {rendition.ai_disclosure_text or ''}".lower()
            has_disclosure = any(p in content_lower for p in disclosure_patterns)
            if not has_disclosure:
                violations.append(
                    ViolationItem(
                        field="ai_disclosure",
                        message="Destination requires explicit AI-content disclosure label (e.g. '[AI-Assisted]').",
                        rule="disclosure_required",
                        severity="error",
                    )
                )

        # 5. Automation Allowed Check
        if not destination.automation_allowed and destination.connector_key != "assisted":
            violations.append(
                ViolationItem(
                    field="automation_allowed",
                    message="Automated posting is not allowed on this destination. Must be handled via the 'assisted' connector.",
                    rule="automation_allowed",
                    severity="error",
                )
            )

        passed = len(violations) == 0
        return RuleEngineResult(passed=passed, violations=violations, retry_after_seconds=retry_after)
