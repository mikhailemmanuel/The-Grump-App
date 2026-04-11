#!/usr/bin/env bash
# FoodGrump — Manually trigger all scrapers in sequence
# Usage: ./scripts/run_scrapers.sh [--skip-reddit] [--skip-rankings]
#
# Requires: Celery worker running, or run directly via Python
# This script sends tasks to the Celery queue. Make sure a worker is up.
set -euo pipefail

cd "$(dirname "$0")/.."

SKIP_REDDIT=false
SKIP_RANKINGS=false

for arg in "$@"; do
    case $arg in
        --skip-reddit) SKIP_REDDIT=true ;;
        --skip-rankings) SKIP_RANKINGS=true ;;
        --help) echo "Usage: $0 [--skip-reddit] [--skip-rankings]"; exit 0 ;;
    esac
done

echo "🍽️  FoodGrump Scraper Pipeline"
echo "==============================="
echo ""

run_task() {
    local name="$1"
    local task="$2"
    echo "⏳ [$name] Sending task..."
    python -c "
from app.celery_app import celery
result = celery.send_task('$task')
print(f'   Task ID: {result.id}')
"
    echo "✅ [$name] Task queued"
    echo ""
}

# ── Restaurant scrapers ──────────────────────────────────────────────
echo "🍴 RESTAURANT SCRAPERS"
echo "──────────────────────"
run_task "Michelin Restaurants" "app.scrapers.michelin.scrape_michelin_restaurants"
run_task "Beli" "app.scrapers.beli.scrape_beli"
run_task "Infatuation" "app.scrapers.infatuation.scrape_infatuation"
run_task "Eater" "app.scrapers.eater.scrape_eater"

if [ "$SKIP_REDDIT" = false ]; then
    run_task "Reddit Restaurants" "app.scrapers.reddit.scrape_reddit_restaurants"
fi

# ── Hotel scrapers ───────────────────────────────────────────────────
echo "🏨 HOTEL SCRAPERS"
echo "──────────────────"
run_task "Michelin Hotels" "app.scrapers.michelin_hotels.scrape_michelin_hotels"
run_task "Condé Nast" "app.scrapers.conde_nast.scrape_conde_nast"

if [ "$SKIP_REDDIT" = false ]; then
    run_task "Reddit Hotels" "app.scrapers.reddit.scrape_reddit_hotels"
fi

# ── Cross-cutting ────────────────────────────────────────────────────
echo "🔗 ENRICHMENT"
echo "──────────────"
run_task "Google Reviews (Restaurants)" "app.scrapers.google_reviews.sync_google_reviews_restaurants"
run_task "Google Reviews (Hotels)" "app.scrapers.google_reviews.sync_google_reviews_hotels"
run_task "Reservation Matching" "app.scrapers.reservations.match_reservations"

# ── Rankings & Summaries ─────────────────────────────────────────────
if [ "$SKIP_RANKINGS" = false ]; then
    echo "📊 RANKINGS & SUMMARIES"
    echo "───────────────────────"
    run_task "Compute Rankings" "app.scrapers.scoring.compute_all_rankings"
    run_task "AI Summaries" "app.scrapers.ai_summary.generate_all_summaries"
fi

echo "==============================="
echo "✅ All tasks queued! Monitor progress in Celery worker logs."
echo ""
echo "Tip: Watch worker output with:"
echo "  docker compose -f docker-compose.prod.yml logs -f celery-worker"
