import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { VenueOut } from '../lib/types';
import ScoreBadge from './ScoreBadge';

interface Props {
  venue: VenueOut;
}

export default function VenueCard({ venue }: Props) {
  const router = useRouter();
  const tags = venue.cuisine_tags || venue.tags || [];
  const priceDots = '●'.repeat(venue.price_level ?? 0) + '○'.repeat(4 - (venue.price_level ?? 0));

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/venue/${venue.id}`)}
      activeOpacity={0.7}
    >
      <View style={styles.row}>
        <View style={styles.info}>
          {venue.rank && (
            <Text style={styles.rank}>#{venue.rank}</Text>
          )}
          <Text style={styles.name} numberOfLines={1}>{venue.name}</Text>
          <Text style={styles.meta}>
            {venue.city} · {priceDots}
          </Text>
          <View style={styles.tags}>
            {tags.slice(0, 3).map((tag) => (
              <View key={tag} style={styles.tag}>
                <Text style={styles.tagText}>{tag}</Text>
              </View>
            ))}
          </View>
        </View>
        <ScoreBadge score={venue.composite_score ?? 0} />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  info: {
    flex: 1,
    marginRight: 12,
  },
  rank: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6B7280',
    marginBottom: 2,
  },
  name: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A2E',
    marginBottom: 4,
  },
  meta: {
    fontSize: 13,
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
    paddingVertical: 3,
  },
  tagText: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
});
