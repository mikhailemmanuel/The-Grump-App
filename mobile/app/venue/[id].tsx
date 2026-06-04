import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  ActivityIndicator, StyleSheet, Dimensions, Linking,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { Verdict } from '../../lib/types';
import { useVenue, useVenueSummary, useVenueReviews, useVenueReservations, useSubmitReview, useToggleSaved, useToggleWantToGo, useUploadReviewPhoto } from '../../lib/hooks';
import { useAuth } from '../../lib/auth';
import ScoreBadge from '../../components/ScoreBadge';
import VerdictButtons from '../../components/VerdictButtons';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function VenueDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: venue, isLoading, error, refetch } = useVenue(id!);
  const { data: summary } = useVenueSummary(id!);
  const { data: reviews } = useVenueReviews(id!);
  const { data: reservations } = useVenueReservations(id!);

  const submitReview = useSubmitReview(id!);
  const uploadReviewPhoto = useUploadReviewPhoto(id!);
  const toggleSaved = useToggleSaved();
  const toggleWantToGo = useToggleWantToGo();

  const [verdict, setVerdict] = useState<Verdict | undefined>();
  const [comment, setComment] = useState('');
  const [showComment, setShowComment] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [wantToGo, setWantToGo] = useState(false);
  const [submittedReviewId, setSubmittedReviewId] = useState<string | undefined>();

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
      { onSuccess: (review) => setSubmittedReviewId(review.id) },
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
    }
  };

  const pickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) return;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
    });
    if (result.canceled || !result.assets.length) return;
    const asset = result.assets[0];
    const reviewId = submittedReviewId;
    if (!reviewId) return;
    uploadReviewPhoto.mutate({
      reviewId,
      localUri: asset.uri,
      mimeType: asset.mimeType ?? 'image/jpeg',
    });
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      {/* Hero image placeholder */}
      <View style={styles.hero}>
        <Ionicons name="image-outline" size={48} color="#D1D5DB" />
        <Text style={styles.heroText}>Photo</Text>
        {/* Bookmark */}
        <TouchableOpacity
          style={styles.bookmarkBtn}
          onPress={handleBookmark}
        >
          <Ionicons
            name={bookmarked ? 'bookmark' : 'bookmark-outline'}
            size={24}
            color={bookmarked ? '#1A6B5A' : '#FFFFFF'}
          />
        </TouchableOpacity>
      </View>

      {/* Info section */}
      <View style={styles.infoSection}>
        <View style={styles.nameRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{venue.name}</Text>
            <Text style={styles.meta}>
              {venue.city} · {priceDots}
            </Text>
            <View style={styles.tags}>
              {tags.map((tag) => (
                <View key={tag} style={styles.tag}>
                  <Text style={styles.tagText}>{tag}</Text>
                </View>
              ))}
            </View>
          </View>
          <View style={styles.scoreCol}>
            <ScoreBadge score={venue.composite_score ?? 0} size="large" />
            {venue.rank && <Text style={styles.rankLabel}>#{venue.rank} in {venue.city}</Text>}
          </View>
        </View>

        {/* CTA Button */}
        <TouchableOpacity style={styles.ctaButton} activeOpacity={0.8} onPress={handleCta}>
          <Ionicons name={isRestaurant ? 'restaurant-outline' : 'bed-outline'} size={18} color="#FFFFFF" />
          <Text style={styles.ctaText}>{isRestaurant ? 'Reserve' : 'Book'}</Text>
        </TouchableOpacity>
      </View>

      {/* Review section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Your Review</Text>
        <View style={styles.sectionContent}>
          <VerdictButtons selected={verdict} onSelect={handleVerdict} />
          {showComment && (
            <View style={styles.commentArea}>
              <TextInput
                style={styles.commentInput}
                placeholder="Add a comment (optional)..."
                placeholderTextColor="#9CA3AF"
                value={comment}
                onChangeText={setComment}
                multiline
                numberOfLines={3}
              />
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 10 }}>
                <TouchableOpacity style={styles.photoBtn} onPress={pickImage}>
                  <Ionicons name="camera-outline" size={18} color="#1A6B5A" />
                  <Text style={styles.photoBtnText}>Add Photo</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.photoBtn, { backgroundColor: '#1A6B5A' }]}
                  onPress={handleSubmitReview}
                >
                  <Text style={[styles.photoBtnText, { color: '#FFFFFF' }]}>Submit</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        </View>
      </View>

      {/* Community section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Community</Text>
        <View style={styles.sectionContent}>
          {summary ? (
            <>
              {/* Verdict breakdown bar */}
              {sentiment && (goBackCount + iffyCount + wouldNotCount > 0) && (
                <>
                  <View style={styles.breakdownBar}>
                    <View style={[styles.barSegment, { flex: goBackCount, backgroundColor: '#1A6B5A' }]} />
                    <View style={[styles.barSegment, { flex: iffyCount, backgroundColor: '#D4A843' }]} />
                    <View style={[styles.barSegment, { flex: wouldNotCount, backgroundColor: '#DC2626' }]} />
                  </View>
                  <View style={styles.breakdownLabels}>
                    <Text style={styles.breakdownLabel}>👍 {goBackCount}</Text>
                    <Text style={styles.breakdownLabel}>🤷 {iffyCount}</Text>
                    <Text style={styles.breakdownLabel}>👎 {wouldNotCount}</Text>
                  </View>
                </>
              )}

              {/* Review & photo counts */}
              <Text style={{ fontSize: 13, color: '#6B7280', marginTop: 10 }}>
                {summary.review_count} reviews · {summary.photo_count} photos
              </Text>

              {/* AI Summary */}
              {summary.ai_summary && (
                <View style={styles.aiSummary}>
                  <Ionicons name="sparkles" size={14} color="#1A6B5A" />
                  <Text style={styles.aiSummaryText}>{summary.ai_summary}</Text>
                </View>
              )}

              {/* Highlights */}
              {summary.highlights && summary.highlights.length > 0 && (
                <View style={styles.highlights}>
                  <Text style={styles.highlightsTitle}>Highlights</Text>
                  {summary.highlights.map((h) => (
                    <Text key={h} style={styles.highlightItem}>💡 {h}</Text>
                  ))}
                </View>
              )}

              {/* Photo gallery placeholder */}
              <View style={styles.galleryGrid}>
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <View key={i} style={styles.galleryItem}>
                    <Ionicons name="image-outline" size={20} color="#D1D5DB" />
                  </View>
                ))}
              </View>
            </>
          ) : (
            <View style={styles.noCommunity}>
              <Ionicons name="people-outline" size={32} color="#D1D5DB" />
              <Text style={styles.noCommunityText}>Be the first to review!</Text>
            </View>
          )}
        </View>
      </View>

      {/* Action buttons */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionBtn, wantToGo && styles.actionBtnActive]}
          onPress={handleWantToGo}
        >
          <Ionicons
            name={wantToGo ? 'heart' : 'heart-outline'}
            size={18}
            color={wantToGo ? '#FFFFFF' : '#1A6B5A'}
          />
          <Text style={[styles.actionBtnText, wantToGo && styles.actionBtnTextActive]}>
            Want to Go
          </Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn}>
          <Ionicons name="add-outline" size={18} color="#1A6B5A" />
          <Text style={styles.actionBtnText}>Add to List</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorText: {
    fontSize: 16,
    color: '#9CA3AF',
  },
  hero: {
    height: 240,
    backgroundColor: '#E5E7EB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroText: {
    color: '#9CA3AF',
    marginTop: 6,
    fontSize: 13,
  },
  bookmarkBtn: {
    position: 'absolute',
    top: 56,
    right: 16,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0,0,0,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoSection: {
    padding: 16,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  name: {
    fontSize: 24,
    fontWeight: '800',
    color: '#1A1A2E',
    marginBottom: 4,
  },
  meta: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 8,
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  tag: {
    backgroundColor: '#F3F4F6',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  tagText: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  scoreCol: {
    alignItems: 'center',
    marginLeft: 12,
  },
  rankLabel: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 4,
    fontWeight: '500',
  },
  ctaButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1A6B5A',
    borderRadius: 12,
    paddingVertical: 14,
    marginTop: 16,
    gap: 8,
  },
  ctaText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  section: {
    marginTop: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1A1A2E',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  sectionContent: {
    paddingHorizontal: 16,
  },
  commentArea: {
    marginTop: 14,
  },
  commentInput: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    color: '#1A1A2E',
    minHeight: 72,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  photoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 10,
    alignSelf: 'flex-start',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#1A6B5A',
  },
  photoBtnText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1A6B5A',
  },
  breakdownBar: {
    flexDirection: 'row',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    gap: 2,
  },
  barSegment: {
    borderRadius: 4,
  },
  breakdownLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  breakdownLabel: {
    fontSize: 13,
    color: '#6B7280',
  },
  aiSummary: {
    flexDirection: 'row',
    gap: 8,
    backgroundColor: '#E8F5F1',
    borderRadius: 10,
    padding: 12,
    marginTop: 14,
    alignItems: 'flex-start',
  },
  aiSummaryText: {
    flex: 1,
    fontSize: 13,
    color: '#1A1A2E',
    lineHeight: 20,
  },
  highlights: {
    marginTop: 14,
  },
  highlightsTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1A1A2E',
    marginBottom: 6,
  },
  highlightItem: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 22,
  },
  galleryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 16,
  },
  galleryItem: {
    width: (SCREEN_WIDTH - 32 - 12) / 3,
    height: (SCREEN_WIDTH - 32 - 12) / 3,
    backgroundColor: '#E5E7EB',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  noCommunity: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  noCommunityText: {
    color: '#9CA3AF',
    marginTop: 8,
    fontSize: 14,
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 16,
    marginTop: 24,
  },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: '#1A6B5A',
  },
  actionBtnActive: {
    backgroundColor: '#1A6B5A',
  },
  actionBtnText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1A6B5A',
  },
  actionBtnTextActive: {
    color: '#FFFFFF',
  },
});
