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

## License

Private — All rights reserved.
