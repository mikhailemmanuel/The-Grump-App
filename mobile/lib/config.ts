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
