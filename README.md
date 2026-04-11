# FoodGrump — Restaurant & Hotel Recommendation Aggregator

> Discover the best restaurants and hotels, ranked by an intelligent combination of Michelin Guide, The Infatuation, Eater, Beli, Condé Nast Traveler, Google Reviews, and Reddit sentiment.

## Architecture

```
backend/          Python FastAPI + SQLAlchemy + Celery
mobile/           React Native (Expo) mobile app
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

## License

Private — All rights reserved.
