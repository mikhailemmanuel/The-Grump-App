# FoodGrump — Restaurant & Hotel Recommendation Aggregator

> Discover the best restaurants and hotels, ranked by an intelligent combination of Michelin Guide, The Infatuation, Eater, Beli, Condé Nast Traveler, Google Reviews, and Reddit sentiment.

## Two ways to run

FoodGrump can run in **two modes**, controlled by `USE_LOCAL_DATA` in `mobile/lib/config.ts`:

1. **Offline / shareable (default).** The app ships with a curated dataset of ~180 top
   restaurants & hotels across 11 travel cities (`mobile/lib/seed.json`), with composite
   scores computed by the real weighting model. No backend, database, or API keys needed —
   just build the web app and share a URL. This is the mode used for the GitHub Pages
   deploy. Want-to-go / saved / your verdicts persist on the device.
2. **Live backend.** Set `USE_LOCAL_DATA = false` to point the app at a running FoodGrump
   API (accounts, community reviews, photo uploads, and live scraped data).

### Share it as a web link (offline mode)

```bash
cd mobile
npm install --legacy-peer-deps
npx expo export -p web        # outputs static site to mobile/dist/
```

Pushing to the deploy branch auto-publishes to **GitHub Pages** via
`.github/workflows/deploy-web.yml`. One-time setup: repo **Settings → Pages → Source →
GitHub Actions**. The app is then live at `https://<user>.github.io/The-Grump-App/`.

> The Pages base path is set in `mobile/app.json` (`experiments.baseUrl: "/The-Grump-App"`).
> If you rename the repo or use a custom domain, update that value to match.

### Regenerating the curated dataset

The bundled dataset is produced from editorial source files by a script that ports the
backend's exact scoring model:

```bash
cd mobile
node scripts/generate-seed.mjs <group1.json> [group2.json ...]   # → lib/seed.json
```

## Architecture

```
backend/          Python FastAPI + SQLAlchemy + Celery
mobile/           React Native (Expo) mobile app
mobile/lib/seed.json          curated offline dataset (scored)
mobile/scripts/generate-seed.mjs   dataset generator (mirrors backend scoring)
```

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
cp .env.example .env        # fill in your keys
alembic upgrade head
uvicorn app.main:app --reload
```

## Mobile Setup

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with **Expo Go** on your phone.

## Data Sources

| Entity | Sources |
|--------|---------|
| Restaurants | Michelin Guide, The Infatuation, Eater, Beli, Google Reviews, Reddit |
| Hotels | Michelin Hotels Guide, Condé Nast Traveler, Google Reviews, Reddit |

## Security

- JWT authentication with short-lived access tokens (15 min) + refresh tokens (30 days)
- Token revocation via Redis blacklist
- API rate limiting (100/min unauthenticated, 300/min authenticated, 5/min on auth)
- Pre-signed S3 uploads (AWS credentials never exposed to client)
- EXIF metadata stripping + image moderation pipeline
- Security headers (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
- Configurable CORS origins
- Password strength enforcement
- Role-based authorization (owner, admin)
- Pluggable secrets provider (env vars / AWS Secrets Manager)

Run security audit: `./scripts/security-check.sh`

## Deployment

### Option A: Docker Compose (self-hosted / VPS)

```bash
# 1. Clone and configure
git clone https://github.com/mikhailemmanuel/TravelGrump-FoodGrump-HotelGrump.git
cd TravelGrump-FoodGrump-HotelGrump
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# 2. Start all services (API + PostgreSQL + Redis + Celery worker + Celery beat)
docker compose -f docker-compose.prod.yml up -d

# 3. Verify
curl http://localhost:8000/    # → {"status": "ok", "service": "foodgrump"}

# 4. Run scrapers to populate data
docker compose -f docker-compose.prod.yml exec api bash scripts/run_scrapers.sh

# 5. Monitor
docker compose -f docker-compose.prod.yml logs -f
```

### Option B: Fly.io (recommended for quick start)

```bash
# 1. Install Fly CLI: https://fly.io/docs/getting-started/installing-flyctl/
# 2. Sign up / log in
fly auth login

# 3. Create app + managed Postgres + Redis
cd backend
fly launch --copy-config    # uses existing fly.toml
fly postgres create --name foodgrump-db
fly postgres attach foodgrump-db
fly redis create --name foodgrump-redis

# 4. Set secrets
fly secrets set \
  SECRET_KEY="$(openssl rand -hex 32)" \
  GOOGLE_PLACES_API_KEY="your-key" \
  OPENAI_API_KEY="your-key" \
  REDDIT_CLIENT_ID="your-id" \
  REDDIT_CLIENT_SECRET="your-secret" \
  BELI_EMAIL="your-email" \
  BELI_PASSWORD="your-password" \
  AWS_ACCESS_KEY_ID="your-key" \
  AWS_SECRET_ACCESS_KEY="your-secret" \
  AWS_S3_BUCKET="foodgrump-photos" \
  ALLOWED_ORIGINS='["https://foodgrump.com"]' \
  ENVIRONMENT="production"

# 5. Deploy
fly deploy

# 6. Scale worker + beat processes
fly scale count worker=1 beat=1

# 7. Run scrapers
fly ssh console -C "cd /app && bash scripts/run_scrapers.sh"
```

### Option C: Railway

```bash
# 1. Install Railway CLI: https://docs.railway.app/guides/cli
railway login

# 2. Create project
railway init

# 3. Add PostgreSQL + Redis plugins via Railway dashboard

# 4. Set environment variables via Railway dashboard (same as Fly.io secrets above)

# 5. Deploy
railway up

# 6. Run scrapers via Railway shell
railway run bash backend/scripts/run_scrapers.sh
```

### After Deployment

Update the mobile app to point to your deployed API:

```bash
# In mobile/lib/config.ts, update PROD_URL:
const PROD_URL = 'https://your-app.fly.dev';  # or your Railway URL
```

## Scraper Management

```bash
# Run all scrapers manually
cd backend && bash scripts/run_scrapers.sh

# Run without Reddit (if you don't have Reddit API keys yet)
bash scripts/run_scrapers.sh --skip-reddit

# Run without ranking computation
bash scripts/run_scrapers.sh --skip-rankings
```

Scrapers also run automatically via Celery Beat on this schedule:
| Scraper | Frequency | Time (UTC) |
|---------|-----------|------------|
| Michelin Restaurants | Weekly (Sun) | 2:00 AM |
| Michelin Hotels | Weekly (Sun) | 3:00 AM |
| Condé Nast | Weekly (Sun) | 4:00 AM |
| Google Reviews | Weekly (Sun/Mon) | 5:00 AM |
| Beli | Daily | 6:00 AM |
| Reddit (Restaurants) | Daily | 7:00 AM |
| Reddit (Hotels) | Daily | 8:00 AM |
| Infatuation | Weekly (Mon) | 2:00 AM |
| Eater | Weekly (Mon) | 3:00 AM |
| Reservation Matching | Daily | 9:00 AM |
| Compute Rankings | Daily | 10:00 AM |
| AI Summaries | Daily | 11:00 AM |

## License

Private — All rights reserved.
