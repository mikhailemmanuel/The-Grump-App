export type EntityType = 'restaurant' | 'hotel';

export type ScoreTier = 'gold' | 'silver' | 'bronze' | 'none';

export type Verdict = 'go_back' | 'iffy' | 'would_not';

export interface SourceRating {
  source: string;
  rating: string;
  url?: string;
  icon?: string;
}

export interface Venue {
  id: string;
  type: EntityType;
  name: string;
  city: string;
  neighborhood?: string;
  cuisine?: string;        // restaurants
  amenityTags?: string[];  // hotels
  cuisineTags?: string[];  // restaurants
  priceLevel: number;      // 1-4
  compositeScore: number;  // 0-100
  rank?: number;
  sourceRatings: SourceRating[];
  heroImage?: string;
  latitude?: number;
  longitude?: number;
  address?: string;
  phone?: string;
  website?: string;
  reservationUrl?: string;
  bookingUrl?: string;
}

export interface UserProfile {
  id: string;
  name: string;
  avatarUrl?: string;
  reviewCount: number;
  listsCount: number;
}

export interface Review {
  id: string;
  venueId: string;
  userId: string;
  verdict: Verdict;
  comment?: string;
  photoUrls?: string[];
  createdAt: string;
}

export interface VenueList {
  id: string;
  name: string;
  venueIds: string[];
  isPublic: boolean;
}

export interface CommunityStats {
  venueId: string;
  goBackCount: number;
  iffyCount: number;
  wouldNotCount: number;
  aiSummary?: string;
  topDishes?: string[];
  highlights?: string[];
}

export interface SearchResult {
  venues: Venue[];
  total: number;
}

export interface CityRanking {
  city: string;
  venues: Venue[];
}
