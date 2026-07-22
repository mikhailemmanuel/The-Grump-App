import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  ActivityIndicator, StyleSheet, Linking,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { Verdict } from '../../lib/types';
import {
  useVenue, useVenueSummary, useVenueReservations,
  useSubmitReview, useToggleSaved, useToggleWantToGo, useUploadReviewPhoto,
} from '../../lib/hooks';
import { USE_LOCAL_DATA } from '../../lib/config';
import { getVenueSourceBreakdown } from '../../lib/localData';
import * as localStore from '../../lib/localStore';
import ScoreBadge from '../../components/ScoreBadge';
import VerdictButtons from '../../components/VerdictButtons';

// Source badge colors for the "Where it's recommended" section.
const SOURCE_COLORS: Record<string, string> = {
  michelin: '#B01B2E', eater: '#D4451F', conde_nast: '#1A1A2E',
  infatuation: '#E8484E', beli: '#2E7D6B', google: '#4285F4', reddit: '#FF4500',
};

export default function VenueDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: venue, isLoading, error, refetch } = useVenue(id!);
  const { data: summary } = useVenueSummary(id!);
  const { data: reservations } = useVenueReservations(id!);

  const submitReview = useSubmitReview(id!);
  const uploadReviewPhoto = useUploadReviewPhoto(id!);
  const toggleSaved = useToggleSaved();
  const toggleWantToGo = useToggleWantToGo();

  const existingReview = USE_LOCAL_DATA ? localStore.getLocalReview(id!) : undefined;
  const [verdict, setVerdict] = useState<Verdict | undefined>(existingReview?.verdict);
  const [comment, setComment] = useState(existingReview?.comment ?? '');
  const [showComment, setShowComment] = useState(!!existingReview);
  const [submitted, setSubmitted] = useState(!!existingReview);
  const [bookmarked, setBookmarked] = useState(USE_LOCAL_DATA ? localStore.isSaved(id!) : false);
  const [wantToGo, setWantToGo] = useState(USE_LOCAL_DATA ? localStore.isWantToGo(id!) : false);
  const [submittedReviewId, setSubmittedReviewId] = useState<string | undefined>(existingReview?.id);

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1A6B5A" />
      </View>
    );
  }

  if (error || !venue) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error ? 'Failed to load venue' : 'Venue not found'}</Text>
        <TouchableOpacity onPress={() => refetch()} style={{ marginTop: 12 }}>
          <Text style={{ color: '#1A6B5A', fontWeight: '600' }}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const tags = venue.cuisine_tags || venue.tags || [];
  const priceDots = '●'.repeat(venue.price_level ?? 0) + '○'.repeat(4 - (venue.price_level ?? 0));
  const isRestaurant = venue.entity_type === 'restaurant';
  const sources = getVenueSourceBreakdown(id!);
  const sentiment = summary?.sentiment_breakdown;
  const goBackCount = sentiment?.go_back ?? 0;
  const iffyCount = sentiment?.iffy ?? 0;
  const wouldNotCount = sentiment?.would_not_go_back ?? 0;

  const handleVerdict = (v: Verdict) => {
    setVerdict(v);
    setShowComment(true);
  };

  const handleSubmitReview = () => {
    if (!verdict) return;
    submitReview.mutate(
      { verdict, comment: comment || undefined },
      { onSuccess: (review: any) => { setSubmittedReviewId(review?.id); setSubmitted(true); } },
    );
  };

  const handleBookmark = () => {
    toggleSaved.mutate({ venueId: id!, action: bookmarked ? 'remove' : 'add' });
    setBookmarked(!bookmarked);
  };

  const handleWantToGo = () => {
    toggleWantToGo.mutate({ venueId: id!, action: wantToGo ? 'remove' : 'add' });
    setWantToGo(!wantToGo);
  };

  const handleCta = () => {
    if (reservations?.length) {
      Linking.openURL(reservations[0].booking_url);
      return;
    }
    // Fallback: search the venue on Google Maps.
    const q = encodeURIComponent(`${venue.name} ${venue.city}`);
    Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${q}`);
  };

  const pickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return;
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 });
    if (result.canceled || !result.assets.length) return;
    const asset = result.assets[0];
    if (!submittedReviewId) return;
    uploadReviewPhoto.mutate({
      reviewId: submittedReviewId,
      localUri: asset.uri,
      mimeType: asset.mimeType ?? 'image/jpeg',
    });
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      {/* Hero */}
      <View style={styles.hero}>
        <Ionicons name={isRestaurant ? 'restaurant' : 'bed'} size={44} color="#B9C4C0" />
        <TouchableOpacity style={styles.bookmarkBtn} onPress={handleBookmark}>
          <Ionicons
            name={bookmarked ? 'bookmark' : 'bookmark-outline'}
            size={24}
            color={bookmarked ? '#1A6B5A' : '#FFFFFF'}
          />
        </TouchableOpacity>
      </View>

      {/* Info */}
      <View style={styles.infoSection}>
        <View style={styles.nameRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{venue.name}</Text>
            <Text style={styles.meta}>{venue.city} · {priceDots}</Text>
            <View style={styles.tags}>
              {tags.map((tag) => (
                <View key={tag} style={styles.tag}><Text style={styles.tagText}>{tag}</Text></View>
              ))}
            </View>
          </View>
          <View style={styles.scoreCol}>
            <ScoreBadge score={Math.round(venue.composite_score ?? 0)} size="large" />
            {venue.rank ? <Text style={styles.rankLabel}>#{venue.rank} in {venue.city}</Text> : null}
          </View>
        </View>

        {summary?.ai_summary && (
          <Text style={styles.blurb}>{summary.ai_summary}</Text>
        )}

        <TouchableOpacity style={styles.ctaButton} activeOpacity={0.8} onPress={handleCta}>
          <Ionicons name={isRestaurant ? 'restaurant-outline' : 'bed-outline'} size={18} color="#FFFFFF" />
          <Text style={styles.ctaText}>
            {reservations?.length ? (isRestaurant ? 'Reserve' : 'Book') : 'View on Maps'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Where it's recommended */}
      {sources.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Where it's recommended</Text>
          <Text style={styles.sectionSub}>
            Composite score blends these sources — the % shows each source's weight in the ranking.
          </Text>
          <View style={styles.sectionContent}>
            {sources.map((s) => (
              <View key={s.id} style={styles.sourceRow}>
                <View style={[styles.sourceDot, { backgroundColor: SOURCE_COLORS[s.source] ?? '#6B7280' }]} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.sourceName}>{s.source_label}</Text>
                  {s.snippet && s.snippet !== s.rating_display ? (
                    <Text style={styles.sourceSnippet} numberOfLines={2}>{s.snippet}</Text>
                  ) : null}
                </View>
                <View style={styles.sourceRight}>
                  <Text style={styles.sourceRating}>{s.rating_display}</Text>
                  {s.weight > 0 && (
                    <Text style={styles.sourceWeight}>{Math.round(s.weight * 100)}%</Text>
                  )}
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Your Review */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Your Verdict</Text>
        <View style={styles.sectionContent}>
          <VerdictButtons selected={verdict} onSelect={handleVerdict} />
          {showComment && (
            <View style={styles.commentArea}>
              <TextInput
                style={styles.commentInput}
                placeholder="Add a note (optional)..."
                placeholderTextColor="#9CA3AF"
                value={comment}
                onChangeText={setComment}
                multiline
                numberOfLines={3}
              />
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
                {!USE_LOCAL_DATA && (
                  <TouchableOpacity style={styles.photoBtn} onPress={pickImage}>
                    <Ionicons name="camera-outline" size={18} color="#1A6B5A" />
                    <Text style={styles.photoBtnText}>Add Photo</Text>
                  </TouchableOpacity>
                )}
                <TouchableOpacity
                  style={[styles.photoBtn, { backgroundColor: '#1A6B5A' }]}
                  onPress={handleSubmitReview}
                >
                  <Text style={[styles.photoBtnText, { color: '#FFFFFF' }]}>
                    {submitted ? 'Update' : 'Save Verdict'}
                  </Text>
                </TouchableOpacity>
              </View>
              {submitted && (
                <Text style={styles.savedNote}>Saved to your Visited list ✓</Text>
              )}
            </View>
          )}
        </View>
      </View>

      {/* Community (only meaningful once there are local verdicts) */}
      {sentiment && (goBackCount + iffyCount + wouldNotCount > 0) && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Verdicts</Text>
          <View style={styles.sectionContent}>
            <View style={styles.breakdownBar}>
              <View style={[styles.barSegment, { flex: goBackCount || 0.001, backgroundColor: '#1A6B5A' }]} />
              <View style={[styles.barSegment, { flex: iffyCount || 0.001, backgroundColor: '#D4A843' }]} />
              <View style={[styles.barSegment, { flex: wouldNotCount || 0.001, backgroundColor: '#DC2626' }]} />
            </View>
            <View style={styles.breakdownLabels}>
              <Text style={styles.breakdownLabel}>👍 {goBackCount}</Text>
              <Text style={styles.breakdownLabel}>🤷 {iffyCount}</Text>
              <Text style={styles.breakdownLabel}>👎 {wouldNotCount}</Text>
            </View>
          </View>
        </View>
      )}

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionBtn, wantToGo && styles.actionBtnActive]}
          onPress={handleWantToGo}
        >
          <Ionicons name={wantToGo ? 'heart' : 'heart-outline'} size={18} color={wantToGo ? '#FFFFFF' : '#1A6B5A'} />
          <Text style={[styles.actionBtnText, wantToGo && styles.actionBtnTextActive]}>Want to Go</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionBtn, bookmarked && styles.actionBtnActive]}
          onPress={handleBookmark}
        >
          <Ionicons name={bookmarked ? 'bookmark' : 'bookmark-outline'} size={18} color={bookmarked ? '#FFFFFF' : '#1A6B5A'} />
          <Text style={[styles.actionBtnText, bookmarked && styles.actionBtnTextActive]}>Save</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAFA' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#9CA3AF' },
  hero: { height: 200, backgroundColor: '#DCE4E1', alignItems: 'center', justifyContent: 'center' },
  bookmarkBtn: {
    position: 'absolute', top: 56, right: 16, width: 40, height: 40, borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.3)', alignItems: 'center', justifyContent: 'center',
  },
  infoSection: { padding: 16 },
  nameRow: { flexDirection: 'row', alignItems: 'flex-start' },
  name: { fontSize: 24, fontWeight: '800', color: '#1A1A2E', marginBottom: 4 },
  meta: { fontSize: 14, color: '#6B7280', marginBottom: 8 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  tag: { backgroundColor: '#F3F4F6', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 },
  tagText: { fontSize: 12, color: '#6B7280', fontWeight: '500' },
  scoreCol: { alignItems: 'center', marginLeft: 12 },
  rankLabel: { fontSize: 11, color: '#6B7280', marginTop: 4, fontWeight: '500' },
  blurb: { fontSize: 15, color: '#374151', lineHeight: 22, marginTop: 14 },
  ctaButton: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    backgroundColor: '#1A6B5A', borderRadius: 12, paddingVertical: 14, marginTop: 16, gap: 8,
  },
  ctaText: { fontSize: 16, fontWeight: '700', color: '#FFFFFF' },
  section: { marginTop: 20 },
  sectionTitle: {
    fontSize: 14, fontWeight: '700', color: '#1A1A2E', textTransform: 'uppercase',
    letterSpacing: 0.5, paddingHorizontal: 16, marginBottom: 6,
  },
  sectionSub: { fontSize: 12, color: '#9CA3AF', paddingHorizontal: 16, marginBottom: 12, lineHeight: 17 },
  sectionContent: { paddingHorizontal: 16 },
  sourceRow: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFFFFF',
    borderRadius: 12, padding: 14, marginBottom: 8, gap: 12,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1,
  },
  sourceDot: { width: 10, height: 10, borderRadius: 5 },
  sourceName: { fontSize: 15, fontWeight: '600', color: '#1A1A2E' },
  sourceSnippet: { fontSize: 12, color: '#6B7280', marginTop: 2, lineHeight: 16 },
  sourceRight: { alignItems: 'flex-end' },
  sourceRating: { fontSize: 14, fontWeight: '700', color: '#1A6B5A' },
  sourceWeight: { fontSize: 11, color: '#9CA3AF', marginTop: 2, fontWeight: '600' },
  commentArea: { marginTop: 14 },
  commentInput: {
    backgroundColor: '#FFFFFF', borderRadius: 10, padding: 12, fontSize: 14, color: '#1A1A2E',
    minHeight: 72, textAlignVertical: 'top', borderWidth: 1, borderColor: '#E5E7EB',
  },
  photoBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start',
    paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8, borderWidth: 1, borderColor: '#1A6B5A',
  },
  photoBtnText: { fontSize: 13, fontWeight: '600', color: '#1A6B5A' },
  savedNote: { fontSize: 12, color: '#1A6B5A', marginTop: 10, fontWeight: '600' },
  breakdownBar: { flexDirection: 'row', height: 8, borderRadius: 4, overflow: 'hidden', gap: 2 },
  barSegment: { borderRadius: 4 },
  breakdownLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  breakdownLabel: { fontSize: 13, color: '#6B7280' },
  actions: { flexDirection: 'row', gap: 10, paddingHorizontal: 16, marginTop: 24 },
  actionBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    paddingVertical: 12, borderRadius: 10, borderWidth: 1.5, borderColor: '#1A6B5A',
  },
  actionBtnActive: { backgroundColor: '#1A6B5A' },
  actionBtnText: { fontSize: 14, fontWeight: '600', color: '#1A6B5A' },
  actionBtnTextActive: { color: '#FFFFFF' },
});
