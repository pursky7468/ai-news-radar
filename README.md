# X AI News Researcher

Automated X (Twitter) research pipeline that continuously fetches, scores, and surfaces AI-related posts.

## Architecture

- **Backend**: FastAPI + APScheduler (Python 3.11)
- **Scoring**: TF-IDF + keyword weight model (no external API)
- **Storage**: PostgreSQL via SQLAlchemy + Alembic
- **Dashboard**: Next.js 14 (TypeScript + Tailwind CSS)
- **Delivery**: Email (SMTP) + webhook digest

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set X_BEARER_TOKEN and API_KEY at minimum
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

- API: http://localhost:8000
- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs

### 3. First run verification

```bash
# Check health
curl http://localhost:8000/api/health

# List news (after first fetch cycle completes in ~15 min)
curl -H "X-API-Key: <your_api_key>" http://localhost:8000/api/news

# Trigger digest manually
curl -X POST -H "X-API-Key: <your_api_key>" http://localhost:8000/api/digest/trigger
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `X_BEARER_TOKEN` | Yes | X API v2 Bearer Token |
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `API_KEY` | Yes | Key for `X-API-Key` header auth |
| `SMTP_HOST` | No | SMTP host for email digest |
| `SMTP_PORT` | No | SMTP port (default: 587) |
| `SMTP_USER` | No | SMTP username |
| `SMTP_PASSWORD` | No | SMTP password |
| `DIGEST_EMAIL_FROM` | No | From address for digest email |
| `DIGEST_EMAIL_TO` | No | Recipient for digest email |
| `DIGEST_WEBHOOK_URL` | No | Slack/Discord webhook URL |
| `FETCH_INTERVAL_MINUTES` | No | Fetch cadence (default: 15) |
| `DIGEST_CRON` | No | Digest schedule cron (default: `0 8 * * *`) |
| `RELEVANCE_THRESHOLD` | No | Min score for `is_relevant` (default: 5) |
| `MONITORED_ACCOUNTS` | No | Comma-separated X handles to monitor |

## Running Tests

### Backend

```bash
cd backend
pip install -e ".[test]"
pytest
```

### Frontend

```bash
cd dashboard
npm install
npm test
```

## API Key Generation

Generate a secure random key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set this as `API_KEY` in your `.env` file.

## Keyword Tuning

Edit `backend/keywords.yaml` to adjust term weights and add/remove keywords without code changes. Restart the service to apply changes.

## Development

```bash
# Backend dev server
cd backend && uvicorn app.main:app --reload

# Frontend dev server
cd dashboard && npm run dev
```
