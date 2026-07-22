/**
 * Local personal-state store for offline mode: want-to-go, saved venues, and
 * your own verdicts/reviews. Persists to web-safe storage (localStorage on web,
 * MMKV on native) so a friend's picks survive a page refresh.
 *
 * No account needed — everything is device-local.
 */
import { createStore } from './storage';
import type { Verdict } from './types';

const store = createStore('foodgrump-local');

const KEYS = {
  WANT_TO_GO: 'want_to_go',
  SAVED: 'saved',
  REVIEWS: 'reviews',
} as const;

export interface LocalReview {
  id: string;
  venue_id: string;
  verdict: Verdict;
  comment?: string;
  created_at: string;
}

function readIds(key: string): string[] {
  const raw = store.getString(key);
  if (!raw) return [];
  try { return JSON.parse(raw) as string[]; } catch { return []; }
}
function writeIds(key: string, ids: string[]): void {
  store.set(key, JSON.stringify(ids));
}

// ── Want to go ───────────────────────────────────────────────────────
export function getWantToGoIds(): string[] { return readIds(KEYS.WANT_TO_GO); }
export function isWantToGo(id: string): boolean { return getWantToGoIds().includes(id); }
export function setWantToGo(id: string, on: boolean): void {
  const ids = new Set(getWantToGoIds());
  if (on) ids.add(id); else ids.delete(id);
  writeIds(KEYS.WANT_TO_GO, [...ids]);
}

// ── Saved ────────────────────────────────────────────────────────────
export function getSavedIds(): string[] { return readIds(KEYS.SAVED); }
export function isSaved(id: string): boolean { return getSavedIds().includes(id); }
export function setSaved(id: string, on: boolean): void {
  const ids = new Set(getSavedIds());
  if (on) ids.add(id); else ids.delete(id);
  writeIds(KEYS.SAVED, [...ids]);
}

// ── Reviews (your verdicts) ──────────────────────────────────────────
export function getLocalReviews(): LocalReview[] {
  const raw = store.getString(KEYS.REVIEWS);
  if (!raw) return [];
  try { return JSON.parse(raw) as LocalReview[]; } catch { return []; }
}
export function getLocalReview(venueId: string): LocalReview | undefined {
  return getLocalReviews().find((r) => r.venue_id === venueId);
}
export function upsertLocalReview(
  venueId: string,
  verdict: Verdict,
  comment?: string,
): LocalReview {
  const all = getLocalReviews().filter((r) => r.venue_id !== venueId);
  const review: LocalReview = {
    id: `local-${venueId}`,
    venue_id: venueId,
    verdict,
    comment,
    // Deterministic-free timestamp; ISO string is fine at runtime (not in workflows).
    created_at: new Date().toISOString(),
  };
  all.push(review);
  store.set(KEYS.REVIEWS, JSON.stringify(all));
  return review;
}
export function getVisitedIds(): string[] {
  return getLocalReviews().map((r) => r.venue_id);
}
