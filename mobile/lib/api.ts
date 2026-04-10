import { Venue, SearchResult, CityRanking, Review, CommunityStats, UserProfile } from './types';

const BASE_URL = __DEV__ ? 'http://localhost:3000/api' : 'https://api.foodgrump.com';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

// Venues
export const getVenues = (params?: { type?: string; city?: string; q?: string }) => {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return apiFetch<Venue[]>(`/venues${qs ? `?${qs}` : ''}`);
};

export const getVenue = (id: string) =>
  apiFetch<Venue>(`/venues/${id}`);

export const searchVenues = (query: string, type?: string) =>
  apiFetch<SearchResult>(`/search?q=${encodeURIComponent(query)}${type ? `&type=${type}` : ''}`);

// Rankings
export const getCityRankings = (city: string, type?: string) =>
  apiFetch<CityRanking>(`/rankings/${encodeURIComponent(city)}${type ? `?type=${type}` : ''}`);

// Reviews
export const submitReview = (review: Omit<Review, 'id' | 'createdAt'>) =>
  apiFetch<Review>('/reviews', { method: 'POST', body: JSON.stringify(review) });

export const getCommunityStats = (venueId: string) =>
  apiFetch<CommunityStats>(`/venues/${venueId}/community`);

// Recommendations
export const getRecommendations = (params?: { city?: string; type?: string }) => {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return apiFetch<Venue[]>(`/recommendations${qs ? `?${qs}` : ''}`);
};

// User
export const getProfile = () => apiFetch<UserProfile>('/me');

export const getUserLists = () => apiFetch<any[]>('/me/lists');

export const addToList = (listId: string, venueId: string) =>
  apiFetch<void>(`/me/lists/${listId}/venues`, {
    method: 'POST',
    body: JSON.stringify({ venueId }),
  });

export const toggleWantToGo = (venueId: string) =>
  apiFetch<void>(`/me/want-to-go/${venueId}`, { method: 'POST' });

export const toggleBookmark = (venueId: string) =>
  apiFetch<void>(`/me/bookmarks/${venueId}`, { method: 'POST' });
