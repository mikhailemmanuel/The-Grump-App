import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { EntityType } from '../../lib/types';
import { useSearch, useCities } from '../../lib/hooks';
import VenueCard from '../../components/VenueCard';

const CUISINES = ['Sushi', 'BBQ', 'Italian', 'Ramen', 'Seafood', 'Steakhouse', 'Tacos', 'French'];

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filter, setFilter] = useState<EntityType | 'all'>('all');
  const { data: cities } = useCities();

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isLoading } = useSearch(debouncedQuery, filter === 'all' ? undefined : filter);
  const results = data?.items ?? [];

  const hasQuery = query.trim().length > 0;

  return (
    <View style={styles.container}>
      {/* Search bar */}
      <View style={styles.searchBar}>
        <Ionicons name="search" size={18} color="#9CA3AF" />
        <TextInput
          style={styles.input}
          placeholder="Search restaurants, hotels, cuisines..."
          placeholderTextColor="#9CA3AF"
          value={query}
          onChangeText={setQuery}
          autoCorrect={false}
        />
        {hasQuery && (
          <TouchableOpacity onPress={() => setQuery('')}>
            <Ionicons name="close-circle" size={18} color="#9CA3AF" />
          </TouchableOpacity>
        )}
      </View>

      {/* Filter tabs */}
      <View style={styles.filterRow}>
        {(['all', 'restaurant', 'hotel'] as const).map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterTab, filter === f && styles.filterActive]}
            onPress={() => setFilter(f)}
          >
            <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>
              {f === 'all' ? 'All' : f === 'restaurant' ? 'Restaurants' : 'Hotels'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {hasQuery ? (
        isLoading ? (
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 60 }}>
            <ActivityIndicator size="large" color="#1A6B5A" />
          </View>
        ) : (
        <FlatList
          data={results}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <VenueCard venue={item as any} />}
          contentContainerStyle={{ paddingTop: 12, paddingBottom: 32 }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="search-outline" size={40} color="#D1D5DB" />
              <Text style={styles.emptyText}>No results for "{query}"</Text>
            </View>
          }
        />
        )
      ) : (
        <View style={styles.suggestions}>
          {/* Browse by city */}
          <Text style={styles.sectionTitle}>Browse by City</Text>
          <View style={styles.chipWrap}>
            {(cities ?? []).map((c) => (
              <TouchableOpacity key={c} style={styles.chip} onPress={() => setQuery(c)}>
                <Ionicons name="location-outline" size={14} color="#1A6B5A" />
                <Text style={styles.chipText}>{c}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Browse by cuisine */}
          <Text style={[styles.sectionTitle, { marginTop: 24 }]}>Popular Cuisines</Text>
          <View style={styles.chipWrap}>
            {CUISINES.map((s) => (
              <TouchableOpacity key={s} style={styles.chip} onPress={() => setQuery(s)}>
                <Ionicons name="restaurant-outline" size={14} color="#1A6B5A" />
                <Text style={styles.chipText}>{s}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: '#1A1A2E',
  },
  filterRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingTop: 12,
    gap: 8,
  },
  filterTab: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#F3F4F6',
  },
  filterActive: {
    backgroundColor: '#1A6B5A',
  },
  filterText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
  },
  filterTextActive: {
    color: '#FFFFFF',
  },
  empty: {
    alignItems: 'center',
    paddingTop: 60,
  },
  emptyText: {
    color: '#9CA3AF',
    fontSize: 15,
    marginTop: 12,
  },
  suggestions: {
    paddingHorizontal: 16,
    paddingTop: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1A1A2E',
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  chipText: {
    fontSize: 14,
    color: '#1A1A2E',
    fontWeight: '500',
  },
});
