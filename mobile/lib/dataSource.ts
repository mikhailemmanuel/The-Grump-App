/**
 * Read-path indirection: in offline mode (config.USE_LOCAL_DATA) reads resolve
 * against the bundled dataset (localData); otherwise they hit the live backend
 * (api). Hooks import their read functions from here so the rest of the app
 * doesn't care which mode it's in.
 */
import { USE_LOCAL_DATA } from './config';
import * as api from './api';
import * as local from './localData';

export const getVenues = USE_LOCAL_DATA ? local.getVenues : api.getVenues;
export const getVenue = USE_LOCAL_DATA ? local.getVenue : api.getVenue;
export const searchVenues = USE_LOCAL_DATA ? local.searchVenues : api.searchVenues;
export const getCities = USE_LOCAL_DATA ? local.getCities : api.getCities;
export const getCityRankings = USE_LOCAL_DATA ? local.getCityRankings : api.getCityRankings;
export const getVenueRecommendations =
  USE_LOCAL_DATA ? local.getVenueRecommendations : api.getVenueRecommendations;
export const getVenueReservations =
  USE_LOCAL_DATA ? local.getVenueReservations : api.getVenueReservations;
export const getVenueSummary = USE_LOCAL_DATA ? local.getVenueSummary : api.getVenueSummary;
export const getVenueReviews = USE_LOCAL_DATA ? local.getVenueReviews : api.getVenueReviews;
