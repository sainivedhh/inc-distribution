# Third-Party Dependencies, Models, and Licences

All dependencies, models, and libraries utilized in IncuBrix Distribution have been verified for commercial compatibility (permissive licences: MIT, Apache 2.0, BSD). No AGPL or non-commercial (CC BY-NC) components are included in the shipped service.

## 1. Shipped Python Dependencies

| Package | Version | Licence | Purpose |
|---|---|---|---|
| fastapi | 0.110.0 | MIT | Asynchronous REST API framework |
| uvicorn | 0.28.0 | BSD-3-Clause | ASGI web server |
| pydantic | 2.6.4 | MIT | Data parsing, validation, and contracts |
| pydantic-settings | 2.2.1 | MIT | Environment variable and configuration management |
| sqlalchemy | 2.0.28 | MIT | ORM and asynchronous database engine |
| psycopg / asyncpg | 3.1.18 / 0.29.0 | LGPL / Apache 2.0 | PostgreSQL asynchronous drivers |
| aiosqlite | 0.20.0 | MIT | Asynchronous SQLite engine for lightweight local testing |
| redis | 5.3.1 | MIT | Redis cache and queue client |
| arq | 0.28.0 | MIT | Asynchronous Redis job queue |
| httpx | 0.27.0 | BSD-3-Clause | Asynchronous HTTP client for platform connectors |
| tenacity | 8.2.3 | Apache 2.0 | Exponential backoff and retry handling |
| structlog | 26.1.0 | Apache 2.0 / MIT | Structured JSON logging with contextvars |
| cryptography | 42.0.5 | Apache 2.0 / BSD | Fernet symmetric encryption for credentials at rest |
| python-multipart | 0.0.22 | Apache 2.0 | Multipart form-data parser |
| pyyaml | 6.0.1 | MIT | YAML manifest parser |
| boto3 / botocore | 1.34.69 | Apache 2.0 | S3 / MinIO storage client |
| openpyxl | 3.1.2 | MIT | Excel workbook automation and reporting |
| pytz | 2024.1 | MIT | Timezone handling |

## 2. Infrastructure & Local Test Containers

| Container / Image | Source | Licence | Purpose |
|---|---|---|---|
| postgres:16-alpine | Docker Hub Official | PostgreSQL Licence | Relational storage for destinations, jobs, idempotency |
| redis:7-alpine | Docker Hub Official | BSD-3-Clause | In-memory queue and caching |
| minio/minio | Quay / Docker Hub | AGPLv3 (runtime container only, client library boto3 is Apache 2.0) | S3-compatible object storage |

## 3. Data Sourcing

- `catalogue/real_catalogue.csv`: Curated from publicly available open source communities, developer networks, and public forum guidelines (Discourse meta, Dev.to, Ghost, Hashnode, Lemmy, Indie Hackers).
- No proprietary or copyrighted personal data was scraped.
