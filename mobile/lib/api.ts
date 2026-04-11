import { getTokens, setTokens } from './auth';
import type {
  VenueOut,
  VenueList,
  RecommendationOut,
  ReservationLinkOut,
  VenueSummaryOut,
  ReviewOut,
  ReviewCreate,
  CityRankingOut,
  UserOut,
  RefreshTokenOut,
  CustomListCreate,
  CustomListOut,
  WantToGoOut,
  SavedVenueOut,
} from './types';

const BASE_URL = __DEV__ ? 'http://localhost:8000' : 'https://api.foodgrump.com';

// ── Core fetch with 401 refresh-and-retry ───────────────────────────────────

let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const tokens = getTokens();
  if (!tokens?.refresh_token) return false;
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    });
    if (!res.ok) return false;
    const data: RefreshTokenOut = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const doFetch = () => {
    const tokens = getTokens();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string>),
    };
    if (tokens?.access_token) {
      headers['Authorization'] = `Bearer ${tokens.access_token}`;
    }
    return fetch(`${BASE_URL}${path}`, { ...options, headers });
  };

  let res = await doFetch();

  if (res.status === 401) {
    // Deduplicate concurrent refresh attempts
    if (!refreshPromise) {
      refreshPromise = tryRefresh().finally(() => { refreshPromise = null; });
    }
    const ok = await refreshPromise;
    if (ok) {
      res = await doFetch();
    }
  }

  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: Record<string, string | number | undefined>): string {
  const filtered: Record<string, string> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) filtered[k] = String(v);
  }
  const s = new URLSearchParams(filtered).toString();
  return s ? `?${s}` : '';
}

// ── Auth ────────────────────────────────────────────────────────────────────

export const register = (email: string, password: string, display_name: string) =>
  apiFetch<import('./types').UserOut>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, display_name }),
  });

export const login = (email: string, password: string) =>
  apiFetch<RefreshTokenOut>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

export const refreshToken = (refresh_token: string) =>
  apiFetch<RefreshTokenOut>('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token }),
  });

export const logout = () =>
  apiFetch<void>('/auth/logout', { method: 'POST' });

export const logoutAll = () =>
  apiFetch<void>('/auth/logout-all', { method: 'POST' });

// ── Venues ──────────────────────────────────────────────────────────────────

export const getVenues = (params?: {
  entity_type?: string;
  city?: string;
  tags?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
}) => apiFetch<VenueList>(`/venues${qs(params ?? {})}`);

export const getRestaurants = (params?: {
  city?: string; tags?: string; limit?: number; offset?: number; sort_by?: string;
}) => apiFetch<VenueList>(`/restaurants${qs(params ?? {})}`);

export const getHotels = (params?: {
  city?: string; tags?: string; limit?: number; offset?: number; sort_by?: string;
}) => apiFetch<VenueList>(`/hotels${qs(params ?? {})}`);

export const getVenue = (id: string) =>
  apiFetch<VenueOut>(`/venues/${id}`);

export const getVenueRecommendations = (venueId: string) =>
  apiFetch<RecommendationOut[]>(`/venues/${venueId}/recommendations`);

export const getVenueReservations = (venueId: string) =>
  apiFetch<ReservationLinkOut[]>(`/venues/${venueId}/reservations`);

export const getVenueSummary = (venueId: string) =>
  apiFetch<VenueSummaryOut>(`/venues/${venueId}/summary`);

export const getVenueReviews = (venueId: string, params?: { limit?: number; offset?: number }) =>
  apiFetch<ReviewOut[]>(`/venues/${venueId}/reviews${qs(params ?? {})}`);

export const submitReview = (venueId: string, review: ReviewCreate) =>
  apiFetch<ReviewOut>(`/venues/${venueId}/review`, {
    method: 'POST',
    body: JSON.stringify(review),
  });

// ── Cities ──────────────────────────────────────────────────────────────────

export const getCities = () =>
  apiFetch<string[]>('/cities');

export const getCityRankings = (
  city: string,
  params?: { entity_type?: string; limit?: number; offset?: number },
) => apiFetch<CityRankingOut[]>(`/cities/${encodeURIComponent(city)}/rankings${qs(params ?? {})}`);

// ── Search ──────────────────────────────────────────────────────────────────

export const searchVenues = (params: {
  q: string; entity_type?: string; limit?: number; offset?: number;
}) => apiFetch<VenueList>(`/search${qs(params)}`);

// ── Users ───────────────────────────────────────────────────────────────────

export const getUserReviews = (userId: string) =>
  apiFetch<ReviewOut[]>(`/users/${userId}/reviews`);

export const getWantToGo = (userId: string) =>
  apiFetch<WantToGoOut[]>(`/users/${userId}/want-to-go`);

export const addWantToGo = (userId: string, venueId: string) =>
  apiFetch<WantToGoOut>(`/users/${userId}/want-to-go/${venueId}`, { method: 'POST' });

export const removeWantToGo = (userId: string, venueId: string) =>
  apiFetch<void>(`/users/${userId}/want-to-go/${venueId}`, { method: 'DELETE' });

export const getVisited = (userId: string) =>
  apiFetch<ReviewOut[]>(`/users/${userId}/visited`);

export const getUserLists = (userId: string) =>
  apiFetch<CustomListOut[]>(`/users/${userId}/lists`);

export const createList = (userId: string, list: CustomListCreate) =>
  apiFetch<CustomListOut>(`/users/${userId}/lists`, {
    method: 'POST',
    body: JSON.stringify(list),
  });

export const getList = (userId: string, listId: string) =>
  apiFetch<CustomListOut>(`/users/${userId}/lists/${listId}`);

export const updateList = (userId: string, listId: string, data: Partial<CustomListCreate>) =>
  apiFetch<CustomListOut>(`/users/${userId}/lists/${listId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

export const deleteList = (userId: string, listId: string) =>
  apiFetch<void>(`/users/${userId}/lists/${listId}`, { method: 'DELETE' });

export const addVenueToList = (userId: string, listId: string, venueId: string) =>
  apiFetch<void>(`/users/${userId}/lists/${listId}/venues/${venueId}`, { method: 'POST' });

export const removeVenueFromList = (userId: string, listId: string, venueId: string) =>
  apiFetch<void>(`/users/${userId}/lists/${listId}/venues/${venueId}`, { method: 'DELETE' });

export const getSaved = (userId: string) =>
  apiFetch<SavedVenueOut[]>(`/users/${userId}/saved`);

export const addSaved = (userId: string, venueId: string) =>
  apiFetch<SavedVenueOut>(`/users/${userId}/saved/${venueId}`, { method: 'POST' });

export const removeSaved = (userId: string, venueId: string) =>
  apiFetch<void>(`/users/${userId}/saved/${venueId}`, { method: 'DELETE' });

export const updateUserSettings = (userId: string, settings: { reviews_public: boolean }) =>
  apiFetch<UserOut>(`/users/${userId}/settings`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
