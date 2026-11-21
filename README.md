# IncuBrix Distribution: Long-Tail Destination Network

A production-grade, containerised connector service and posting-rules intelligence engine designed for IncuBrix Engineering Assessment 4.

Publishes creators' content to long-tail destinations (Discourse forums, Lemmy federated communities, Dev.to/Ghost/Hashnode developer blogs, generic HMAC-signed partner webhooks, Slack channels, MRSS syndication feeds, and assisted-tier destinations).

## Architecture Overview

```mermaid
flowchart TD
    Client["IncuBrix Content Core / Batch Runner"] -->|POST /connector/v1/\{connector\}/\{method\}| API["FastAPI Connector Gateway"]
    Client -->|POST /api/v1/destinations| API
    
    API --> Middleware["Correlation ID & Redaction Middleware"]
    Middleware --> RulesEngine["Posting-Rules Engine\n(Cap, Promo, Links, Disclosure)"]
    
    RulesEngine --> SafeRetries["Idempotency & Safe Retries\n(Atomic DB Key Reservation)"]
    SafeRetries --> Connectors["Connectors Layer\n(Discourse, Lemmy, Devto, Ghost, HMAC, Assisted, Hashnode, Slack, MRSS)"]
    
    Connectors --> Platforms["Third-Party Platforms / Local Test Mocks"]
    API --> Jobs["Background Jobs & Webhook Signer"]
    Jobs --> DB[("PostgreSQL / SQLite")]
    Connectors --> Storage["MinIO / S3 Storage Service"]
```

## Setup & Quickstart (Under 5 Commands)

```bash
# 1. Clone repository and copy environment configuration
cp .env.example .env

# 2. Start services via Docker Compose
docker compose up -d --build

# 3. Run full automated test suite (Unit, Contract, Integration, Hard cases)
make test

# 4. Execute Batch Runner CLI on sample inputs
python -m cli.batch --input test_pack/inputs --api http://localhost:8000 --out test_pack/outputs
```

## Shared Error Codes (Appendix A)

| Error Code | Retryable? | Expected Behavior |
|---|---|---|
| `DEST_SPEC_VIOLATION` | No | Content breaks destination format limits; returns field-level violations |
| `DEST_RULE_FREQUENCY_CAP` | Yes (Later) | Destination posting cap reached; rescheduled with retry window |
| `CONNECTION_AUTH_EXPIRED` | No (After reconnect) | Token/API key expired or revoked; pauses destination connection |
| `PLATFORM_RATE_LIMIT` | Yes | Backs off using platform `Retry-After` / `X-RateLimit-Reset` |
| `PLATFORM_QUOTA_EXHAUSTED` | Yes (Next window) | Daily quota used up; reschedules |
| `PLATFORM_CONTENT_REJECTED` | No | Platform rejected post content; returns reason for editorial review |
| `PLATFORM_UNAVAILABLE` | Yes | Transient platform 5xx; circuit breaker after 5 consecutive failures |
| `CONNECTOR_DISABLED` | No | Disabled by operator kill switch (`DISABLED_CONNECTORS`) |
| `IDEMPOTENCY_KEY_REUSED` | No | Idempotency key reused with mismatched body (HTTP 409) |

## Verification & Documentation

- [REQUIREMENTS_TRACE.md](file:///d:/projects/Distribution/docs/REQUIREMENTS_TRACE.md): Mapping of all 9 Must-haves, 12 Levels, 10 Integration points, and 7 Hard cases to code and tests.
- [REPORT.md](file:///d:/projects/Distribution/REPORT.md): Measured benchmarks, architecture trade-offs, and verification results.
- [SOURCES.md](file:///d:/projects/Distribution/SOURCES.md): Verified commercial-friendly licences and third-party dependencies.
- [AI_USE.md](file:///d:/projects/Distribution/AI_USE.md): Complete disclosure of AI tools and adapters used.
- [DEMO_SCRIPT.md](file:///d:/projects/Distribution/docs/DEMO_SCRIPT.md): 8-minute demonstration script.
