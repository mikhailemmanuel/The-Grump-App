import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { EntityType } from '../../lib/types';
import { useSearch } from '../../lib/hooks';
import VenueCard from '../../components/VenueCard';

const RECENT_SEARCHES = ['Le Bernardin', 'Thai food LES', 'rooftop hotel'];
const TRENDING = ['Tatiana', 'Dhamaka', 'Aman New York', 'Don Angie'];

export default function SearchScreen() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filter, setFilter] = useState<EntityType | 'all'>('all');

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
          {/* Recent searches */}
          <Text style={styles.sectionTitle}>Recent Searches</Text>
          {RECENT_SEARCHES.map((s) => (
            <TouchableOpacity key={s} style={styles.suggestionRow} onPress={() => setQuery(s)}>
              <Ionicons name="time-outline" size={16} color="#9CA3AF" />
              <Text style={styles.suggestionText}>{s}</Text>
            </TouchableOpacity>
          ))}

          {/* Trending */}
          <Text style={[styles.sectionTitle, { marginTop: 24 }]}>Trending</Text>
          {TRENDING.map((s) => (
            <TouchableOpacity key={s} style={styles.suggestionRow} onPress={() => setQuery(s)}>
              <Ionicons name="trending-up" size={16} color="#1A6B5A" />
              <Text style={styles.suggestionText}>{s}</Text>
            </TouchableOpacity>
          ))}
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
  suggestionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  suggestionText: {
    fontSize: 15,
    color: '#1A1A2E',
  },
});
