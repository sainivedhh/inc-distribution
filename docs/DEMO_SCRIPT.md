# 8-Minute Unedited Live Demonstration Script

This script provides an exact 8-minute walkthrough for the candidate's video recording:

## Part 1: Architecture & Request Tracing (00:00 - 02:00)
- **Action**: Open `README.md` and review the architecture diagram.
- **Trace**:
  1. Show a content submission hitting `POST /connector/v1/discourse/publish`.
  2. Explain `CorrelationIdMiddleware` injecting `X-Correlation-Id` and secret redaction filter.
  3. Show how `PostingRulesEngine.evaluate_rules()` verifies frequency caps, self-promo flags, and AI-disclosure tags.
  4. Trace execution into `SafeExecutionManager`: explain the atomic database reservation of `Idempotency-Key` preventing duplicate posts.
  5. Show the connector dispatch to Discourse API / mock server.

## Part 2: One Clean Run & One Failure Handled (02:00 - 04:30)
- **Clean Run**:
  - Run `python -m cli.batch --input test_pack/inputs/input_01_discourse_valid.json --api http://localhost:8000 --out test_pack/outputs`
  - Show the returned 200 OK with `platform_post_id` and live URL.
- **Handled Failure**:
  - Run `python -m cli.batch --input test_pack/inputs/input_02_discourse_violation.json --api http://localhost:8000 --out test_pack/outputs`
  - Show that it cleanly returns violations with `field: title` and `rule: title_max_chars` without crashing or throwing 500 errors.

## Part 3: Test Suite Execution (04:30 - 06:30)
- **Action**: Execute `pytest tests/` in terminal.
- **Highlight**:
  - Point out that all 16 tests pass green.
  - Highlight the 7 hard cases: timeout retry zero duplication, 429 reset time backoff, schema drift detection with automated demotion, SSRF private IP blocking, and UTF-8 safe word boundary truncation.

## Part 4: Design Decision in Code (06:30 - 08:00)
- **Action**: Open `core/idempotency.py` and `core/rules_engine.py`.
- **Explain**:
  - Why stateless connectors combined with atomic DB reservation are essential in distributed publishing.
  - How deterministic reconciliation prevents duplicates even when an external platform experiences network timeouts after creating the post.
