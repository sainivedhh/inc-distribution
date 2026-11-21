"""Hard Case 4: Second post inside frequency cap; promo post to no-promo community."""

from datetime import datetime, timedelta
import pytest
from core.rules_engine import PostingRulesEngine
from core.contract import ContentRendition, DestinationConfig
from core.models import PublicationRecord


@pytest.mark.asyncio
async def test_hard_case_4_rule_violations():
    # 1. Promotional post to no-promo destination
    destination_no_promo = DestinationConfig(
        destination_id="dest_np_1",
        name="Strict Dev Community",
        url="https://community.strict.test",
        platform_key="discourse",
        surface="topic",
        connector_key="discourse",
        self_promo_allowed=False,
    )
    promo_rendition = ContentRendition(
        title="Check out our SaaS",
        body="Buy now and get 50% discount on our SaaS subscription!",
    )
    res_promo = await PostingRulesEngine.evaluate_rules(promo_rendition, destination_no_promo)
    assert res_promo.passed is False
    assert any(v.rule == "self_promo_allowed" for v in res_promo.violations)

    # 2. Link policy violation
    dest_no_links = DestinationConfig(
        destination_id="dest_nl_1",
        name="No Link Community",
        url="https://nolink.test",
        platform_key="discourse",
        surface="topic",
        connector_key="discourse",
        link_policy="no_links",
    )
    link_rendition = ContentRendition(
        title="Insightful Discussion",
        body="Read full post here at https://external-link.com/article",
    )
    res_link = await PostingRulesEngine.evaluate_rules(link_rendition, dest_no_links)
    assert res_link.passed is False
    assert any(v.rule == "link_policy_no_links" for v in res_link.violations)
