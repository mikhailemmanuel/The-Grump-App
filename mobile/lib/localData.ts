/**
 * Offline data source backed by the bundled curated dataset (seed.json).
 *
 * Every function here mirrors the signature/return shape of the matching
 * function in api.ts, so hooks can swap between live-backend and offline modes
 * transparently (see dataSource.ts and config.USE_LOCAL_DATA).
 */
import type {
  VenueOut, VenueList, RecommendationOut, ReservationLinkOut,
  VenueSummaryOut, CityRankingOut, ReviewOut,
} from './types';
import seedJson from './seed.json';
import { getLocalReviews } from './localStore';

// ── Seed shape ───────────────────────────────────────────────────────
interface SeedRec {
  id: string;
  source: string;
  source_label: string;
  source_url?: string;
  title: string;
  snippet?: string;
  rating_display: string;
  rating?: number;
  awards?: string[];
  score: number;
  weight: number;
}
interface SeedReservation { id: string; platform: string; booking_url: string }
export interface SeedVenue {
  id: string;
  entity_type: 'restaurant' | 'hotel';
  name: string;
  city: string;
  country: string | null;
  neighborhood: string | null;
  address: string | null;
  lat: number | null;
  lng: number | null;
  tags: string[];
  cuisine_tags: string[] | null;
  hotel_brand: string | null;
  star_rating: number | null;
  price_level: number | null;
  blurb: string | null;
  composite_score: number;
  source_scores: Record<string, number>;
  recommendations: SeedRec[];
  reservations: SeedReservation[];
  rank: number;
}
interface Seed { cities: string[]; venues: SeedVenue[] }

const seed = seedJson as unknown as Seed;
const byId = new Map(seed.venues.map((v) => [v.id, v]));

// ── Mapping helpers ──────────────────────────────────────────────────
export function toVenueOut(v: SeedVenue): VenueOut {
  return {
    id: v.id,
    entity_type: v.entity_type,
    name: v.name,
    address: v.address ?? undefined,
    city: v.city,
    country: v.country ?? undefined,
    lat: v.lat ?? undefined,
    lng: v.lng ?? undefined,
    tags: v.tags,
    price_level: v.price_level ?? undefined,
    cuisine_tags: v.cuisine_tags ?? undefined,
    star_rating: v.star_rating ?? undefined,
    hotel_brand: v.hotel_brand ?? undefined,
    composite_score: v.composite_score,
    rank: v.rank,
  };
}

export function getSeedVenue(id: string): SeedVenue | undefined {
  return byId.get(id);
}

function sortVenues(list: SeedVenue[], sortBy?: string): SeedVenue[] {
  const arr = [...list];
  if (sortBy === 'name') arr.sort((a, b) => a.name.localeCompare(b.name));
  else arr.sort((a, b) => b.composite_score - a.composite_score);
  return arr;
}

// ── Read API (mirrors api.ts) ────────────────────────────────────────
export async function getVenues(params?: {
  entity_type?: string; city?: string; tags?: string;
  limit?: number; offset?: number; sort_by?: string;
}): Promise<VenueList> {
  let list = seed.venues;
  if (params?.entity_type) list = list.filter((v) => v.entity_type === params.entity_type);
  if (params?.city) list = list.filter((v) => v.city === params.city);
  if (params?.tags) {
    const want = params.tags.toLowerCase();
    list = list.filter((v) =>
      (v.cuisine_tags ?? []).some((t) => t.toLowerCase().includes(want)) ||
      v.tags.some((t) => t.toLowerCase().includes(want)),
    );
  }
  const sorted = sortVenues(list, params?.sort_by);
  const total = sorted.length;
  const offset = params?.offset ?? 0;
  const limit = params?.limit ?? 100;
  return { items: sorted.slice(offset, offset + limit).map(toVenueOut), total };
}

export async function getVenue(id: string): Promise<VenueOut> {
  const v = byId.get(id);
  if (!v) throw new Error('Venue not found');
  return toVenueOut(v);
}

export async function searchVenues(params: {
  q: string; entity_type?: string; limit?: number; offset?: number;
}): Promise<VenueList> {
  const q = params.q.trim().toLowerCase();
  if (!q) return { items: [], total: 0 };
  let list = seed.venues;
  if (params.entity_type) list = list.filter((v) => v.entity_type === params.entity_type);
  const matches = list.filter((v) => {
    const hay = [
      v.name, v.city, v.neighborhood ?? '', v.hotel_brand ?? '',
      ...(v.cuisine_tags ?? []), ...v.tags,
    ].join(' ').toLowerCase();
    return hay.includes(q);
  });
  const sorted = sortVenues(matches);
  return { items: sorted.map(toVenueOut), total: sorted.length };
}

export async function getCities(): Promise<string[]> {
  return seed.cities;
}

export async function getCityRankings(
  city: string,
  params?: { entity_type?: string; limit?: number; offset?: number },
): Promise<CityRankingOut[]> {
  let list = seed.venues.filter((v) => v.city === city);
  if (params?.entity_type) list = list.filter((v) => v.entity_type === params.entity_type);
  list = [...list].sort((a, b) => a.rank - b.rank);
  const offset = params?.offset ?? 0;
  const limit = params?.limit ?? 100;
  return list.slice(offset, offset + limit).map((v) => ({
    venue: toVenueOut(v),
    composite_score: v.composite_score,
    rank: v.rank,
    source_scores: v.source_scores,
  }));
}

export async function getVenueRecommendations(id: string): Promise<RecommendationOut[]> {
  const v = byId.get(id);
  if (!v) return [];
  return v.recommendations.map((r) => ({
    id: r.id,
    source: r.source,
    source_url: r.source_url,
    title: r.title,
    snippet: r.snippet,
    rating: r.rating,
    awards: r.awards,
  }));
}

/** Extended recommendation info the offline detail screen uses (label, weight, display). */
export function getVenueSourceBreakdown(id: string): SeedRec[] {
  return byId.get(id)?.recommendations ?? [];
}

export async function getVenueReservations(id: string): Promise<ReservationLinkOut[]> {
  const v = byId.get(id);
  if (!v) return [];
  return v.reservations.map((r) => ({
    id: r.id, platform: r.platform, booking_url: r.booking_url,
  }));
}

export async function getVenueSummary(id: string): Promise<VenueSummaryOut> {
  const v = byId.get(id);
  if (!v) return { photo_count: 0, review_count: 0 };
  const highlights = v.recommendations
    .slice(0, 4)
    .map((r) => `${r.source_label}: ${r.rating_display}`);
  const localReviews = getLocalReviews().filter((r) => r.venue_id === id);
  const sentiment: Record<string, number> = {};
  for (const r of localReviews) sentiment[r.verdict] = (sentiment[r.verdict] ?? 0) + 1;
  return {
    ai_summary: v.blurb ?? undefined,
    highlights,
    sentiment_breakdown: localReviews.length ? sentiment : undefined,
    photo_count: 0,
    review_count: localReviews.length,
  };
}

export async function getVenueReviews(id: string): Promise<ReviewOut[]> {
  return getLocalReviews()
    .filter((r) => r.venue_id === id)
    .map((r) => ({
      id: r.id,
      user_id: 'local',
      venue_id: r.venue_id,
      verdict: r.verdict,
      comment: r.comment,
      is_public: false,
      created_at: r.created_at,
      photos: [],
    }));
}
