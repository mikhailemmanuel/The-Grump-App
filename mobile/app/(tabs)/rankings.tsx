import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { EntityType } from '../../lib/types';
import { useCities, useCityRankings } from '../../lib/hooks';
import EntityToggle from '../../components/EntityToggle';
import ScoreBadge from '../../components/ScoreBadge';
import { useRouter } from 'expo-router';

export default function RankingsScreen() {
  const [city, setCity] = useState('');
  const [showCityPicker, setShowCityPicker] = useState(false);
  const [entityType, setEntityType] = useState<EntityType>('restaurant');
  const router = useRouter();

  const { data: cities } = useCities();
  const cityList = cities ?? [];

  // Set initial city from first loaded city
  useEffect(() => {
    if (cityList.length > 0 && !city) {
      setCity(cityList[0]);
    }
  }, [cityList, city]);

  const { data: rankings, isLoading, error, refetch } = useCityRankings(city, entityType);

  return (
    <View style={styles.container}>
      {/* City picker */}
      <TouchableOpacity style={styles.cityPicker} onPress={() => setShowCityPicker(!showCityPicker)}>
        <Ionicons name="location" size={16} color="#1A6B5A" />
        <Text style={styles.cityText}>{city}</Text>
        <Ionicons name={showCityPicker ? 'chevron-up' : 'chevron-down'} size={16} color="#6B7280" />
      </TouchableOpacity>

      {showCityPicker && (
        <View style={styles.cityDropdown}>
          {cityList.map((c) => (
            <TouchableOpacity
              key={c}
              style={[styles.cityOption, c === city && styles.cityOptionActive]}
              onPress={() => { setCity(c); setShowCityPicker(false); }}
            >
              <Text style={[styles.cityOptionText, c === city && styles.cityOptionTextActive]}>{c}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <View style={styles.toggleWrap}>
        <EntityToggle value={entityType} onChange={setEntityType} />
      </View>

      {isLoading ? (
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 60 }}>
          <ActivityIndicator size="large" color="#1A6B5A" />
        </View>
      ) : error ? (
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 60 }}>
          <Text style={{ color: '#EF4444', fontSize: 15, marginBottom: 12 }}>Failed to load rankings</Text>
          <TouchableOpacity onPress={() => refetch()} style={{ backgroundColor: '#1A6B5A', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 }}>
            <Text style={{ color: '#FFFFFF', fontWeight: '600' }}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : (
      <FlatList
        data={rankings ?? []}
        keyExtractor={(item) => item.venue.id}
        contentContainerStyle={{ paddingBottom: 32 }}
        renderItem={({ item }) => {
          const tags = item.venue.cuisine_tags || item.venue.tags || [];
          const sources = Object.keys(item.source_scores || {});
          return (
            <TouchableOpacity
              style={styles.rankRow}
              onPress={() => router.push(`/venue/${item.venue.id}`)}
              activeOpacity={0.7}
            >
              <Text style={styles.rankNum}>#{item.rank}</Text>
              <View style={styles.rankInfo}>
                <Text style={styles.rankName}>{item.venue.name}</Text>
                <Text style={styles.rankMeta}>{item.venue.city} · {tags.slice(0, 2).join(', ')}</Text>
                <View style={styles.sourceBadges}>
                  {sources.slice(0, 3).map((source) => (
                    <View key={source} style={styles.sourceBadge}>
                      <Text style={styles.sourceBadgeText}>{source}</Text>
                    </View>
                  ))}
                </View>
              </View>
              <ScoreBadge score={item.composite_score} />
            </TouchableOpacity>
          );
        }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No venues found in {city}</Text>
          </View>
        }
      />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
  },
  cityPicker: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginHorizontal: 16,
    marginTop: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
  },
  cityText: {
    flex: 1,
    fontSize: 16,
    fontWeight: '700',
    color: '#1A1A2E',
  },
  cityDropdown: {
    marginHorizontal: 16,
    marginTop: 4,
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cityOption: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  cityOptionActive: {
    backgroundColor: '#E8F5F1',
  },
  cityOptionText: {
    fontSize: 15,
    color: '#1A1A2E',
  },
  cityOptionTextActive: {
    color: '#1A6B5A',
    fontWeight: '600',
  },
  toggleWrap: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  rankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 14,
    borderRadius: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  rankNum: {
    fontSize: 18,
    fontWeight: '800',
    color: '#D4A843',
    width: 36,
  },
  rankInfo: {
    flex: 1,
    marginRight: 10,
  },
  rankName: {
    fontSize: 17,
    fontWeight: '700',
    color: '#1A1A2E',
  },
  rankMeta: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 2,
  },
  sourceBadges: {
    flexDirection: 'row',
    gap: 4,
    marginTop: 6,
  },
  sourceBadge: {
    backgroundColor: '#F3F4F6',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  sourceBadgeText: {
    fontSize: 10,
    color: '#6B7280',
    fontWeight: '600',
  },
  empty: {
    alignItems: 'center',
    paddingTop: 60,
  },
  emptyText: {
    color: '#9CA3AF',
    fontSize: 15,
  },
});
