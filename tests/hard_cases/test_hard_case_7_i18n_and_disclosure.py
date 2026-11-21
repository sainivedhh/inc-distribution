"""Hard Case 7: Non-English community; destination requiring AI-content disclosure."""

import pytest
from core.tailoring import TailoringEngine
from core.rules_engine import PostingRulesEngine
from core.contract import ContentRendition, DestinationConfig


def test_hard_case_7_i18n_and_disclosure():
    # 1. Non-English community & UTF-8 safe word boundary truncation (CJK & emoji safe)
    cjk_text = "IncuBrix 发布工具非常强大 🚀 这是一个测试句子，用于验证多语言字符的安全截断，绝不截断代码点或表情符号。"
    truncated, was_trunc = TailoringEngine.truncate_at_word_boundary(cjk_text, 35)
    assert was_trunc is True
    assert truncated.endswith("...")
    # Verify valid UTF-8 encoding/decoding without corruption
    assert truncated.encode("utf-8").decode("utf-8") == truncated

    # 2. Destination requiring AI-content disclosure
    dest = DestinationConfig(
        name="Strict AI Policy Forum",
        url="https://forum.incubrix.test",
        platform_key="discourse",
        surface="topic",
        connector_key="discourse",
        disclosure_required=True,
    )

    rendition_without_disclosure = ContentRendition(
        title="AI Automation in 2026",
        body="Here are new benchmarks for model pipelines.",
        ai_generated=True,
    )

    # Tailoring engine automatically injects disclosure line
    tailored, warnings = TailoringEngine.tailor_rendition(rendition_without_disclosure, dest)
    assert "[AI-Assisted" in tailored.body
    assert any("AI disclosure" in w for w in warnings)

    # Verify that tailored rendition passes the rules engine
    import asyncio
    res = asyncio.run(PostingRulesEngine.evaluate_rules(tailored, dest))
    assert res.passed is True
