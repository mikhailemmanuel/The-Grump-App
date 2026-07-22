/**
 * FoodGrump mobile app configuration.
 *
 * Set FOODGRUMP_API_URL in your environment or Expo config to override.
 * Default: localhost:8000 in dev, https://api.foodgrump.com in production.
 */

// @ts-ignore — Expo injects extra/expoConfig at runtime
const expoConfig = (globalThis as any).expo?.modules?.ExpoConstants?.expoConfig;

const DEV_URL = 'http://localhost:8000';
const PROD_URL = 'https://api.foodgrump.com';

export const API_BASE_URL: string =
  expoConfig?.extra?.apiBaseUrl ??
  (typeof __DEV__ !== 'undefined' && __DEV__ ? DEV_URL : PROD_URL);

/**
 * When true, the app runs fully offline against the bundled curated dataset
 * (lib/seed.json) — no backend, database, or API keys required. This is the
 * mode used for the shareable web build.
 *
 * Set to false to talk to a live FoodGrump backend at API_BASE_URL instead
 * (real accounts, community reviews, photo uploads, live scraped data).
 */
export const USE_LOCAL_DATA: boolean =
  expoConfig?.extra?.useLocalData ?? true;

// build: web deploy
