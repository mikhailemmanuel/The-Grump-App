import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from '@tanstack/react-query';
import { useAuth } from './auth';
import * as api from './api';
import type { ReviewCreate, CustomListCreate } from './types';

// ── Query Hooks ─────────────────────────────────────────────────────────────

export function useVenues(
  entityType?: string,
  city?: string,
  params?: { tags?: string; limit?: number; offset?: number; sort_by?: string },
) {
  return useQuery({
    queryKey: ['venues', entityType, city, params] as const,
    queryFn: () =>
      api.getVenues({ entity_type: entityType, city, ...params }),
  });
}

export function useVenue(id: string) {
  return useQuery({
    queryKey: ['venue', id] as const,
    queryFn: () => api.getVenue(id),
    enabled: !!id,
  });
}

export function useSearch(query: string, entityType?: string) {
  return useQuery({
    queryKey: ['search', query, entityType] as const,
    queryFn: () => api.searchVenues({ q: query, entity_type: entityType }),
    enabled: query.trim().length > 0,
    placeholderData: keepPreviousData,
  });
}

export function useCities() {
  return useQuery({
    queryKey: ['cities'] as const,
    queryFn: () => api.getCities(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useCityRankings(city: string, entityType?: string) {
  return useQuery({
    queryKey: ['rankings', city, entityType] as const,
    queryFn: () => api.getCityRankings(city, { entity_type: entityType }),
    enabled: !!city,
  });
}

export function useVenueSummary(id: string) {
  return useQuery({
    queryKey: ['venue-summary', id] as const,
    queryFn: () => api.getVenueSummary(id),
    enabled: !!id,
  });
}

export function useVenueReviews(id: string) {
  return useQuery({
    queryKey: ['venue-reviews', id] as const,
    queryFn: () => api.getVenueReviews(id),
    enabled: !!id,
  });
}

export function useVenueRecommendations(id: string) {
  return useQuery({
    queryKey: ['venue-recommendations', id] as const,
    queryFn: () => api.getVenueRecommendations(id),
    enabled: !!id,
  });
}

export function useVenueReservations(id: string) {
  return useQuery({
    queryKey: ['venue-reservations', id] as const,
    queryFn: () => api.getVenueReservations(id),
    enabled: !!id,
  });
}

export function useUserWantToGo() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-want-to-go', userId] as const,
    queryFn: () => api.getWantToGo(userId!),
    enabled: !!userId,
  });
}

export function useUserVisited() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-visited', userId] as const,
    queryFn: () => api.getVisited(userId!),
    enabled: !!userId,
  });
}

export function useUserLists() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-lists', userId] as const,
    queryFn: () => api.getUserLists(userId!),
    enabled: !!userId,
  });
}

export function useUserSaved() {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: ['user-saved', userId] as const,
    queryFn: () => api.getSaved(userId!),
    enabled: !!userId,
  });
}

// ── Mutation Hooks ──────────────────────────────────────────────────────────

export function useSubmitReview(venueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ReviewCreate) => api.submitReview(venueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['venue-reviews', venueId] });
      queryClient.invalidateQueries({ queryKey: ['venue-summary', venueId] });
    },
  });
}

export function useToggleWantToGo() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ venueId, action }: { venueId: string; action: 'add' | 'remove' }) => {
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
    mutationFn: ({ venueId, action }: { venueId: string; action: 'add' | 'remove' }) => {
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
