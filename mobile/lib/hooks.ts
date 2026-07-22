import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from '@tanstack/react-query';
import { useAuth } from './auth';
import * as api from './api';
import * as data from './dataSource';
import * as localStore from './localStore';
import { getSeedVenue } from './localData';
import { USE_LOCAL_DATA } from './config';
import type { ReviewCreate, CustomListCreate, VenueOut } from './types';

// ── Query Hooks ─────────────────────────────────────────────────────────────

export function useVenues(
  entityType?: string,
  city?: string,
  params?: { tags?: string; limit?: number; offset?: number; sort_by?: string },
) {
  return useQuery({
    queryKey: ['venues', entityType, city, params] as const,
    queryFn: () =>
      data.getVenues({ entity_type: entityType, city, ...params }),
  });
}

export function useVenue(id: string) {
  return useQuery({
    queryKey: ['venue', id] as const,
    queryFn: () => data.getVenue(id),
    enabled: !!id,
  });
}

export function useSearch(query: string, entityType?: string) {
  return useQuery({
    queryKey: ['search', query, entityType] as const,
    queryFn: () => data.searchVenues({ q: query, entity_type: entityType }),
    enabled: query.trim().length > 0,
    placeholderData: keepPreviousData,
  });
}

export function useCities() {
  return useQuery({
    queryKey: ['cities'] as const,
    queryFn: () => data.getCities(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useCityRankings(city: string, entityType?: string) {
  return useQuery({
    queryKey: ['rankings', city, entityType] as const,
    queryFn: () => data.getCityRankings(city, { entity_type: entityType }),
    enabled: !!city,
  });
}

export function useVenueSummary(id: string) {
  return useQuery({
    queryKey: ['venue-summary', id] as const,
    queryFn: () => data.getVenueSummary(id),
    enabled: !!id,
  });
}

export function useVenueReviews(id: string) {
  return useQuery({
    queryKey: ['venue-reviews', id] as const,
    queryFn: () => data.getVenueReviews(id),
    enabled: !!id,
  });
}

export function useVenueRecommendations(id: string) {
  return useQuery({
    queryKey: ['venue-recommendations', id] as const,
    queryFn: () => data.getVenueRecommendations(id),
    enabled: !!id,
  });
}

export function useVenueReservations(id: string) {
  return useQuery({
    queryKey: ['venue-reservations', id] as const,
    queryFn: () => data.getVenueReservations(id),
    enabled: !!id,
  });
}

// ── Personal collections ────────────────────────────────────────────────────
// In offline mode these read from device-local storage (no account needed).

function localVenues(ids: string[]): VenueOut[] {
  return ids
    .map((id) => getSeedVenue(id))
    .filter((v): v is NonNullable<typeof v> => !!v)
    .map((v) => ({
      id: v.id, entity_type: v.entity_type, name: v.name, city: v.city,
      address: v.address ?? undefined, country: v.country ?? undefined,
      lat: v.lat ?? undefined, lng: v.lng ?? undefined, tags: v.tags,
      price_level: v.price_level ?? undefined, cuisine_tags: v.cuisine_tags ?? undefined,
      star_rating: v.star_rating ?? undefined, hotel_brand: v.hotel_brand ?? undefined,
      composite_score: v.composite_score, rank: v.rank,
    }));
}

export function useUserWantToGo() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-want-to-go', USE_LOCAL_DATA ? 'local' : userId] as const,
    queryFn: (): Promise<any[]> =>
      USE_LOCAL_DATA
        ? Promise.resolve(localVenues(localStore.getWantToGoIds()))
        : api.getWantToGo(userId!),
    enabled: USE_LOCAL_DATA || !!userId,
  });
}

export function useUserVisited() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-visited', USE_LOCAL_DATA ? 'local' : userId] as const,
    queryFn: (): Promise<any[]> =>
      USE_LOCAL_DATA
        ? Promise.resolve(localVenues(localStore.getVisitedIds()))
        : api.getVisited(userId!),
    enabled: USE_LOCAL_DATA || !!userId,
  });
}

export function useUserLists() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-lists', USE_LOCAL_DATA ? 'local' : userId] as const,
    queryFn: (): Promise<any[]> => (USE_LOCAL_DATA ? Promise.resolve([]) : api.getUserLists(userId!)),
    enabled: USE_LOCAL_DATA || !!userId,
  });
}

export function useUserSaved() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-saved', USE_LOCAL_DATA ? 'local' : userId] as const,
    queryFn: (): Promise<any[]> =>
      USE_LOCAL_DATA
        ? Promise.resolve(localVenues(localStore.getSavedIds()))
        : api.getSaved(userId!),
    enabled: USE_LOCAL_DATA || !!userId,
  });
}

// ── Mutation Hooks ──────────────────────────────────────────────────────────

export function useSubmitReview(venueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ReviewCreate) =>
      USE_LOCAL_DATA
        ? Promise.resolve(localStore.upsertLocalReview(venueId, data.verdict, data.comment))
        : api.submitReview(venueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['venue-reviews', venueId] });
      queryClient.invalidateQueries({ queryKey: ['venue-summary', venueId] });
      queryClient.invalidateQueries({ queryKey: ['user-visited'] });
    },
  });
}

export function useToggleWantToGo() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ venueId, action }: { venueId: string; action: 'add' | 'remove' }): Promise<any> => {
      if (USE_LOCAL_DATA) {
        localStore.setWantToGo(venueId, action === 'add');
        return Promise.resolve();
      }
      const userId = user!.id;
      return action === 'add'
        ? api.addWantToGo(userId, venueId)
        : api.removeWantToGo(userId, venueId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-want-to-go'] });
    },
  });
}

export function useToggleSaved() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ venueId, action }: { venueId: string; action: 'add' | 'remove' }): Promise<any> => {
      if (USE_LOCAL_DATA) {
        localStore.setSaved(venueId, action === 'add');
        return Promise.resolve();
      }
      const userId = user!.id;
      return action === 'add'
        ? api.addSaved(userId, venueId)
        : api.removeSaved(userId, venueId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-saved'] });
    },
  });
}

export function useCreateList() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CustomListCreate) => api.createList(user!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-lists'] });
    },
  });
}

export function useUploadReviewPhoto(venueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      reviewId,
      localUri,
      mimeType,
      caption,
    }: {
      reviewId: string;
      localUri: string;
      mimeType?: string;
      caption?: string;
    }) => {
      const objectKey = await api.uploadPhoto(localUri, mimeType ?? 'image/jpeg');
      return api.attachReviewPhoto(venueId, reviewId, objectKey, caption);
    },
    onSuccess: (_data, { reviewId }) => {
      queryClient.invalidateQueries({ queryKey: ['venue-reviews', venueId] });
      queryClient.invalidateQueries({ queryKey: ['venue-summary', venueId] });
    },
  });
}
