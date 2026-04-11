#!/usr/bin/env bash
# FoodGrump API — Production deployment entrypoint
# Usage: ./scripts/deploy.sh
set -euo pipefail

echo "🚀 FoodGrump API — Starting deployment..."

# ── Check required environment variables ─────────────────────────────
REQUIRED_VARS=(
    "DATABASE_URL"
    "REDIS_URL"
    "SECRET_KEY"
    "GOOGLE_PLACES_API_KEY"
    "OPENAI_API_KEY"
)

missing=0
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "❌ Missing required env var: $var"
        missing=1
    fi
done

if [ "$missing" -eq 1 ]; then
    echo ""
    echo "Set missing variables in your .env file or environment."
    echo "See .env.example for reference."
    exit 1
fi

echo "✅ All required environment variables present"

# ── Run database migrations ──────────────────────────────────────────
echo "📦 Running Alembic migrations..."
cd "$(dirname "$0")/.."
alembic upgrade head
echo "✅ Migrations complete"

# ── Calculate workers ────────────────────────────────────────────────
CPU_COUNT=$(python -c "import os; print(os.cpu_count() or 1)")
WORKERS=$((CPU_COUNT * 2 + 1))
# Cap at 8 workers to avoid memory issues on small instances
if [ "$WORKERS" -gt 8 ]; then
    WORKERS=8
fi

echo "🔧 Starting uvicorn with $WORKERS workers (CPUs: $CPU_COUNT)"

# ── Start the API server ─────────────────────────────────────────────
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "$WORKERS" \
    --log-level info \
    --access-log
