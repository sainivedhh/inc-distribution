# Live Demo Deployment Instructions

This guide provides steps to deploy the IncuBrix Distribution Connector Service as a containerised web service with API token authentication and rate limiting.

## Option A: Deploy to Render / Railway / Fly.io

1. **Create Web Service**:
   - Link the private GitHub repository.
   - Choose Docker deployment (builds from the root `Dockerfile`).
2. **Environment Variables**:
   ```env
   ENVIRONMENT=production
   SIMULATION_MODE=true
   API_TOKEN=incubrix-live-demo-token-987654321
   PORT=8000
   HOST=0.0.0.0
   DATABASE_URL=sqlite+aiosqlite:///./data/distribution.db
   SECRET_ENCRYPTION_KEY=k7R7E-N6yV6s1N3xK1P2l7-v5d_t0A1B2C3D4E5F6G8=
   WEBHOOK_SIGNING_SECRET=incubrix-webhook-hmac-signing-secret-key-32chars
   ```
3. **Verify Deployment**:
   ```bash
   curl -H "X-API-Token: incubrix-live-demo-token-987654321" https://<your-app>.onrender.com/health
   ```
   Cold-start wait time for free-tier containers: ~30-45 seconds.

## Option B: Deploy to VPS / Docker Compose

```bash
git clone <repo_url>
cd Distribution
cp .env.example .env
docker compose up -d --build
```
