// ── Enums / Unions ──────────────────────────────────────────────────────────

export type EntityType = 'restaurant' | 'hotel';

export type ScoreTier = 'gold' | 'silver' | 'bronze' | 'none';

export type Verdict = 'go_back' | 'iffy' | 'would_not_go_back';

// ── Venues ──────────────────────────────────────────────────────────────────

export interface VenueOut {
  id: string;
  entity_type: string;
  name: string;
  address?: string;
  city: string;
  country?: string;
  lat?: number;
  lng?: number;
  tags?: string[];
  price_level?: number;
  cuisine_tags?: string[];
  star_rating?: number;
  hotel_brand?: string;
  composite_score?: number;
  rank?: number;
  google_place_id?: string;
}

export interface VenueList {
  items: VenueOut[];
  total: number;
}

// ── Recommendations / Reservations ──────────────────────────────────────────

export interface RecommendationOut {
  id: string;
  source: string;
  source_url?: string;
  title?: string;
  snippet?: string;
  rating?: number;
  awards?: string[];
  published_at?: string;
}

export interface ReservationLinkOut {
  id: string;
  platform: string;
  booking_url: string;
}

// ── Venue Summary ───────────────────────────────────────────────────────────

export interface VenueSummaryOut {
  ai_summary?: string;
  highlights?: string[];
  sentiment_breakdown?: Record<string, number>;
  photo_count: number;
  review_count: number;
}

// ── Reviews ─────────────────────────────────────────────────────────────────

export interface ReviewPhotoOut {
  id: string;
  image_url: string;
  caption?: string;
}

export interface ReviewCreate {
  verdict: Verdict;
  comment?: string;
  visited_at?: string;
}

export interface ReviewOut {
  id: string;
  user_id: string;
  venue_id: string;
  verdict: Verdict;
  comment?: string;
  is_public: boolean;
  visited_at?: string;
  created_at: string;
  photos: ReviewPhotoOut[];
}

// ── City Rankings ───────────────────────────────────────────────────────────

export interface CityRankingOut {
  venue: VenueOut;
  composite_score: number;
  rank: number;
  source_scores?: Record<string, number>;
}

// ── Users ───────────────────────────────────────────────────────────────────

export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string;
  reviews_public: boolean;
}

// ── Auth ────────────────────────────────────────────────────────────────────

export interface TokenOut {
  access_token: string;
  token_type: string;
}

export interface RefreshTokenOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ── Lists ───────────────────────────────────────────────────────────────────

export interface CustomListCreate {
  name: string;
  entity_type: 'restaurant' | 'hotel' | 'mixed';
  description?: string;
}

export interface CustomListItemOut {
  venue_id: string;
  position: number;
}

export interface CustomListOut {
  id: string;
  name: string;
  entity_type: string;
  description?: string;
  is_public: boolean;
  items: CustomListItemOut[];
}

// ── Want-to-go / Saved ──────────────────────────────────────────────────────

export interface WantToGoOut {
  venue_id: string;
  created_at: string;
}

export interface SavedVenueOut {
  venue_id: string;
  created_at: string;
}
