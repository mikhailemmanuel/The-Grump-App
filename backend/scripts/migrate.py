#!/usr/bin/env python3
"""Standalone migration script for production deployment.

Runs Alembic migrations without importing the full app.
This avoids import-time side effects (engine creation, geoalchemy2, etc.).
"""
import os
import sys
import traceback

def main():
    print("=== FoodGrump Migration Script ===", flush=True)

    # Ensure we can import app modules
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, app_dir)
    os.chdir(app_dir)

    print(f"Working dir: {os.getcwd()}", flush=True)
    print(f"Python path: {sys.path[:3]}", flush=True)

    # Read DATABASE_URL directly from env (don't import app.config to avoid side effects)
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set", flush=True)
        sys.exit(1)

    # Convert to sync psycopg2 driver
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Ensure SSL for Supabase / external Postgres
    if "sslmode" not in sync_url:
        separator = "&" if "?" in sync_url else "?"
        sync_url += f"{separator}sslmode=require"

    print(f"DB host: {sync_url.split('@')[1].split('/')[0] if '@' in sync_url else 'unknown'}", flush=True)

    # Test connection first
    print("Testing database connection...", flush=True)
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Connection OK: {result.scalar()}", flush=True)
        engine.dispose()
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

    # Clean up partial migration state (from previous failed attempts)
    print("Checking for partial migration state...", flush=True)
    try:
        from sqlalchemy import create_engine, text, inspect
        engine = create_engine(sync_url, pool_pre_ping=True)
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        with engine.connect() as conn:
            # Check if alembic_version table exists and has our migration
            has_alembic = "alembic_version" in existing_tables
            migration_done = False
            if has_alembic:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                versions = [row[0] for row in result]
                migration_done = "001_initial" in versions
                print(f"  Alembic versions: {versions}", flush=True)

            # If enum types exist but migration isn't recorded as done, we have partial state
            has_our_tables = "venues" in existing_tables
            if has_our_tables and migration_done:
                print("  Migration 001_initial already applied — nothing to do.", flush=True)
                engine.dispose()
                print("=== Migrations complete! ===", flush=True)
                sys.exit(0)

            if has_our_tables and not migration_done:
                print("  PARTIAL STATE DETECTED — cleaning up...", flush=True)
                # Drop all our tables and types so migration can run clean
                tables_to_drop = [
                    "scrape_jobs", "custom_list_items", "custom_lists",
                    "saved_venues", "want_to_go", "venue_summaries",
                    "review_photos", "user_reviews", "users",
                    "city_rankings", "reservation_links", "recommendations", "venues",
                ]
                for t in tables_to_drop:
                    if t in existing_tables:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{t}" CASCADE'))
                        print(f"    Dropped table: {t}", flush=True)

                # Drop enum types
                for enum_name in ["scrape_status", "list_entity_type", "verdict_type",
                                  "platform_type", "source_type", "entity_type"]:
                    conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
                    print(f"    Dropped type: {enum_name}", flush=True)

                # Drop alembic version tracking
                if has_alembic:
                    conn.execute(text("DELETE FROM alembic_version"))
                    print("    Cleared alembic_version", flush=True)

                conn.commit()
                print("  Cleanup done.", flush=True)
            else:
                # Check if just enum types exist without tables (very partial)
                result = conn.execute(text(
                    "SELECT typname FROM pg_type WHERE typname IN "
                    "('entity_type','source_type','platform_type','verdict_type','list_entity_type','scrape_status')"
                ))
                existing_types = [row[0] for row in result]
                if existing_types and not has_our_tables:
                    print(f"  Orphan enum types found: {existing_types} — cleaning...", flush=True)
                    for enum_name in existing_types:
                        conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
                    if has_alembic:
                        conn.execute(text("DELETE FROM alembic_version"))
                    conn.commit()
                    print("  Orphan types cleaned.", flush=True)
                else:
                    print("  No partial state — clean database.", flush=True)

        engine.dispose()
    except Exception as e:
        print(f"WARNING: Partial state check failed (non-fatal): {e}", flush=True)

    # Run Alembic migrations
    print("Running Alembic migrations...", flush=True)
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(os.path.join(app_dir, "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        alembic_cfg.set_main_option("script_location", os.path.join(app_dir, "alembic"))

        command.upgrade(alembic_cfg, "head")
        print("=== Migrations complete! ===", flush=True)
    except Exception as e:
        print(f"ERROR: Migration failed: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
