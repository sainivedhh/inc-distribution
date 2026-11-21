# Requirements Traceability Matrix

This document maps every requirement from IncuBrix Engineering Assessment 4 to repository code, configuration, tests, and evidence artifacts.

## 1. Must-Haves (Sheet 2_Must_haves)

| # | Must-have | Status | Implementation Path | Verification Test / Evidence | Notes / Limits |
|---|-----------|--------|---------------------|-------------------------------|----------------|
| 1 | Exact connector contract (Appendix A) | Planned | `connectors/`, `api/v1/connector_routes.py`, `core/contract.py` | `tests/contract/test_contract_suite.py` | Validates all methods, request/response models, manifests, and error codes |
| 2 | Six Core connectors certified (Discourse, Lemmy, Dev.to, Ghost, Webhook HMAC, Assisted) | Planned | `connectors/{discourse,lemmy,devto,ghost,webhook_hmac,assisted}/` | `tests/integration/test_core_connectors.py`, `certification_pack/` | Full run: publish, confirm live URL, status, delete / assist pack |
| 3 | Configuration, not code (add instance via single catalogue row) | Planned | `core/catalogue.py`, `api/v1/destinations.py` | `tests/integration/test_add_destination_runtime.py` | New destination row added at runtime and published with zero code changes |
| 4 | Rules checked before every post (frequency cap, self-promo, link policy, AI disclosure) | Planned | `core/rules_engine.py` | `tests/unit/test_rules_engine.py`, `test_pack/rule_evaluation_report.json` | Tested on >=40 labelled cases; blocks/reschedules with machine-readable reasons |
| 5 | Never spam, never cheat (test posts to sandboxes/mocks, deleted within 10 min, 429 respected) | Planned | `core/certification.py`, `connectors/` | `tests/integration/test_rate_limits_and_cleanup.py`, `certification_pack/` | Auto-deletion verified; Retry-After / X-RateLimit-Reset parsed and respected |
| 6 | Safe retries (same idempotency key never creates second post) | Planned | `core/idempotency.py`, `core/jobs.py` | `tests/integration/test_idempotency_timeout_retry.py` | Atomic DB key reservation before platform call + deterministic reconciliation |
| 7 | Secrets protected & simulation mode | Planned | `core/logging.py`, `core/config.py`, `mocks/` | `tests/unit/test_secrets_redaction.py`, `tests/e2e/test_simulation_mode.py` | Structlog redaction filter; SIMULATION_MODE=true runs with zero external keys |
| 8 | Local test instances via docker-compose | Planned | `docker-compose.yml`, `Dockerfile` | `tests/e2e/test_compose_health.py` | Compose boots app, worker, postgres, redis, minio, lemmy, ghost, and mock server |
| 9 | Integration Standard followed & live demo works | Planned | Full repository & `docs/DEPLOY.md` | Verification against 10 Integration points, openapi.yaml diff test | Live demo deployment instructions and token-based protection |

## 2. Assessment Levels (Sheet 3_Levels)

| Level | Item | Status | Implementation Path | Verification Test / Evidence |
|-------|------|--------|---------------------|-------------------------------|
| Core | All must-haves pass | Planned | Full repository | Full test suite green |
| Core | Each Core connector passes full certification run with stored evidence | Planned | `core/certification.py` | `certification_pack/`, `tests/integration/test_certification.py` |
| Core | Platform errors mapped to shared error codes (tokens, rate limits, rejection) | Planned | `connectors/*/errors.py`, `core/errors.py` | `tests/unit/test_error_mapping.py` |
| Advanced | Catalogue import: CSV validated, deduped, reachability checked, enriched (1,000 rows < 5 min) | Planned | `core/catalogue_import.py`, `api/v1/catalogue_routes.py` | `tests/integration/test_catalogue_import_1000.py`, `catalogue/import_report.json` |
| Advanced | Rules capture: AI step reads community rules, proposes structured rules, human confirms | Planned | `core/rules_capture.py` | `tests/unit/test_rules_capture.py` |
| Advanced | Relevance score (1-5) vs IncuBrix audience + short explanation | Planned | `core/relevance.py` | `tests/unit/test_relevance_scoring.py` |
| Advanced | Tailoring: per-destination title/body, discussion-first, canonical URL, safe truncation, hashtags | Planned | `core/tailoring.py` | `tests/unit/test_tailoring.py` |
| Advanced | Three more connectors (Hashnode, Slack app, MRSS video feed) | Planned | `connectors/{hashnode,slack,mrss}/` | `tests/contract/test_advanced_connectors.py`, `certification_pack/` |
| Outstanding | Recommender: rank destinations by fit, measure precision@10 on labelled set | Planned | `core/recommender.py` | `tests/unit/test_recommender.py`, `catalogue/labelled_set.csv` |
| Outstanding | Metrics: fetch_metrics on >=3 connectors normalized to 7 metrics | Planned | `connectors/{discourse,ghost,hashnode}/connector.py` | `tests/integration/test_fetch_metrics.py` |
| Outstanding | Recertification: scheduler re-tests destinations before 30 days, demotes on failure | Planned | `core/recertification.py` | `tests/unit/test_recertification_scheduler.py` |
| Outstanding | Real catalogue: >=150 real, relevant destinations researched with public rules URLs | Planned | `catalogue/real_catalogue.csv` | Sourced and documented in `SOURCES.md` |

## 3. Integration Standard (Sheet 4_Integration)

| Point | Requirement | Status | Implementation Path | Verification Test / Evidence |
|-------|-------------|--------|---------------------|-------------------------------|
| 1 | One-command start and test (`docker compose up`, `make test`, `.env.example`) | Planned | `docker-compose.yml`, `Makefile`, `.env.example` | Clean run verification |
| 2 | Documented HTTP API (`openapi.yaml` matches `/api/v1/` and `/connector/v1/`) | Planned | `openapi.yaml`, `api/app.py` | `tests/contract/test_openapi_spec_diff.py` |
| 3 | Background jobs (202 + job_id for >2s, status endpoint, signed callback) | Planned | `core/jobs.py`, `api/v1/job_routes.py` | `tests/integration/test_background_jobs_and_webhook.py` |
| 4 | Safe retries (`Idempotency-Key` header on every POST) | Planned | `core/idempotency.py`, `api/middleware.py` | `tests/integration/test_idempotency_middleware.py` |
| 5 | Clear errors (`{"error": {"code", "message", "retryable", "details"}}`) | Planned | `core/errors.py`, `api/middleware.py` | `tests/unit/test_error_envelope.py` |
| 6 | Configuration (all settings from env/pydantic-settings, zero hardcoded keys) | Planned | `core/config.py`, `.env.example` | `tests/unit/test_configuration_settings.py` |
| 7 | Files in, files out (upload or URL in, MinIO presigned download links out) | Planned | `core/storage.py`, `api/v1/upload_routes.py` | `tests/integration/test_storage_presigned_urls.py` |
| 8 | Logs and health (JSON logs with timestamp, level, job_id, correlation-id; `/health` & `/ready`) | Planned | `core/logging.py`, `api/v1/health_routes.py` | `tests/unit/test_logging_and_health.py` |
| 9 | Output manifest (JSON manifest with models, versions, timings, costs, warnings, ai_generated) | Planned | `core/manifest_builder.py` | `tests/unit/test_output_manifest.py` |
| 10 | Batch runner (`python -m cli.batch`) | Planned | `cli/batch.py` | `tests/e2e/test_batch_runner.py` |

## 4. Hard Cases (Sheet 6_Hard_cases)

| # | Situation | Status | Handled Behavior | Verification Test |
|---|-----------|--------|------------------|-------------------|
| 1 | Publish timeout & retry with same idempotency key | Planned | Reconciles with platform using deterministic key/slug; returns same post ID, zero duplicate posts | `tests/hard_cases/test_hard_case_1_timeout_retry.py` |
| 2 | 429 response with reset time; expired token; content rejected | Planned | Parses `Retry-After`/`X-RateLimit-Reset` and backs off; returns `CONNECTION_AUTH_EXPIRED` (pause); returns `PLATFORM_CONTENT_REJECTED` with message | `tests/hard_cases/test_hard_case_2_errors.py` |
| 3 | Title/body longer than allowed; unsupported media | Planned | Returns `DEST_SPEC_VIOLATION` with field-level details or applies safe tailoring with warning | `tests/hard_cases/test_hard_case_3_spec_violations.py` |
| 4 | Second post inside frequency cap; promo to no-promo | Planned | Blocks with `DEST_RULE_FREQUENCY_CAP` + retry window; blocks promo with policy details | `tests/hard_cases/test_hard_case_4_rule_violations.py` |
| 5 | Platform renames field in API | Planned | Certification detects schema drift, fails loudly, demotes destination level, logs alert | `tests/hard_cases/test_hard_case_5_schema_drift.py` |
| 6 | CSV with duplicates/bad URLs/mixed languages; partner revokes | Planned | Cleans, deduplicates, reports errors row-by-row; marks webhook connection disabled on 401/410 | `tests/hard_cases/test_hard_case_6_csv_and_revocation.py` |
| 7 | Non-English community; destination requires AI-disclosure | Planned | Language-aware UTF-8 safe word-boundary truncation; auto-appends or validates disclosure tag | `tests/hard_cases/test_hard_case_7_i18n_and_disclosure.py` |
