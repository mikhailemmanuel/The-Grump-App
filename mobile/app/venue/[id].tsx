import React, { useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  FlatList, StyleSheet, Dimensions,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { allMockVenues } from '../../lib/mockData';
import { mockCommunityStats } from '../../lib/mockData';
import { Verdict } from '../../lib/types';
import ScoreBadge from '../../components/ScoreBadge';
import SourceCard from '../../components/SourceCard';
import VerdictButtons from '../../components/VerdictButtons';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function VenueDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const venue = allMockVenues.find((v) => v.id === id);
  const community = id ? mockCommunityStats[id] : undefined;

  const [verdict, setVerdict] = useState<Verdict | undefined>();
  const [comment, setComment] = useState('');
  const [showComment, setShowComment] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [wantToGo, setWantToGo] = useState(false);

  if (!venue) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Venue not found</Text>
      </View>
    );
  }

  const tags = venue.cuisineTags || venue.amenityTags || [];
  const priceDots = '●'.repeat(venue.priceLevel) + '○'.repeat(4 - venue.priceLevel);
  const isRestaurant = venue.type === 'restaurant';
  const totalVotes = community
    ? community.goBackCount + community.iffyCount + community.wouldNotCount
    : 0;

  const handleVerdict = (v: Verdict) => {
    setVerdict(v);
    setShowComment(true);
  };

  const pickImage = async () => {
    await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
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
          onPress={() => setBookmarked(!bookmarked)}
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
              {venue.neighborhood || venue.city} · {priceDots}
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
            <ScoreBadge score={venue.compositeScore} size="large" />
            {venue.rank && <Text style={styles.rankLabel}>#{venue.rank} in {venue.city}</Text>}
          </View>
        </View>

        {/* CTA Button */}
        <TouchableOpacity style={styles.ctaButton} activeOpacity={0.8}>
          <Ionicons name={isRestaurant ? 'restaurant-outline' : 'bed-outline'} size={18} color="#FFFFFF" />
          <Text style={styles.ctaText}>{isRestaurant ? 'Reserve' : 'Book'}</Text>
        </TouchableOpacity>
      </View>

      {/* Source cards */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Ratings</Text>
        <FlatList
          horizontal
          data={venue.sourceRatings}
          keyExtractor={(item) => item.source}
          renderItem={({ item }) => <SourceCard source={item} />}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 16 }}
        />
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
              <TouchableOpacity style={styles.photoBtn} onPress={pickImage}>
                <Ionicons name="camera-outline" size={18} color="#1A6B5A" />
                <Text style={styles.photoBtnText}>Add Photo</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </View>

      {/* Community section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Community</Text>
        <View style={styles.sectionContent}>
          {community ? (
            <>
              {/* Verdict breakdown bar */}
              <View style={styles.breakdownBar}>
                <View style={[styles.barSegment, { flex: community.goBackCount, backgroundColor: '#1A6B5A' }]} />
                <View style={[styles.barSegment, { flex: community.iffyCount, backgroundColor: '#D4A843' }]} />
                <View style={[styles.barSegment, { flex: community.wouldNotCount, backgroundColor: '#DC2626' }]} />
              </View>
              <View style={styles.breakdownLabels}>
                <Text style={styles.breakdownLabel}>👍 {community.goBackCount}</Text>
                <Text style={styles.breakdownLabel}>🤷 {community.iffyCount}</Text>
                <Text style={styles.breakdownLabel}>👎 {community.wouldNotCount}</Text>
              </View>

              {/* AI Summary */}
              {community.aiSummary && (
                <View style={styles.aiSummary}>
                  <Ionicons name="sparkles" size={14} color="#1A6B5A" />
                  <Text style={styles.aiSummaryText}>{community.aiSummary}</Text>
                </View>
              )}

              {/* Top dishes / highlights */}
              {community.topDishes && community.topDishes.length > 0 && (
                <View style={styles.highlights}>
                  <Text style={styles.highlightsTitle}>
                    {isRestaurant ? 'Top Dishes' : 'Highlights'}
                  </Text>
                  {community.topDishes.map((d) => (
                    <Text key={d} style={styles.highlightItem}>• {d}</Text>
                  ))}
                </View>
              )}

              {community.highlights && community.highlights.length > 0 && (
                <View style={styles.highlights}>
                  <Text style={styles.highlightsTitle}>Tips</Text>
                  {community.highlights.map((h) => (
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
          onPress={() => setWantToGo(!wantToGo)}
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
