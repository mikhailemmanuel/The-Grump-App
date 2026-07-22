import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { EntityType } from '../../lib/types';
import { useVenues, useCities } from '../../lib/hooks';
import EntityToggle from '../../components/EntityToggle';
import VenueCard from '../../components/VenueCard';

export default function ExploreScreen() {
  const [entityType, setEntityType] = useState<EntityType>('restaurant');
  const [city, setCity] = useState('');
  const [showCityPicker, setShowCityPicker] = useState(false);

  const { data: cities } = useCities();
  const cityList = cities ?? [];

  useEffect(() => {
    if (cityList.length > 0 && !city) setCity(cityList[0]);
  }, [cityList, city]);

  const { data, isLoading, error, refetch } = useVenues(entityType, city || undefined);
  const venues = data?.items ?? [];

  return (
    <View style={styles.container}>
      {/* City picker */}
      <TouchableOpacity style={styles.cityPicker} onPress={() => setShowCityPicker(!showCityPicker)}>
        <Ionicons name="location" size={16} color="#1A6B5A" />
        <Text style={styles.cityText}>{city || 'All cities'}</Text>
        <Ionicons name={showCityPicker ? 'chevron-up' : 'chevron-down'} size={16} color="#6B7280" />
      </TouchableOpacity>

      {showCityPicker && (
        <View style={styles.cityDropdown}>
          <FlatList
            data={cityList}
            keyExtractor={(c) => c}
            style={{ maxHeight: 280 }}
            renderItem={({ item: c }) => (
              <TouchableOpacity
                style={[styles.cityOption, c === city && styles.cityOptionActive]}
                onPress={() => { setCity(c); setShowCityPicker(false); }}
              >
                <Text style={[styles.cityOptionText, c === city && styles.cityOptionTextActive]}>{c}</Text>
              </TouchableOpacity>
            )}
          />
        </View>
      )}

      <View style={styles.toggleWrap}>
        <EntityToggle value={entityType} onChange={setEntityType} />
      </View>

      {isLoading ? (
        <View style={styles.centered}><ActivityIndicator size="large" color="#1A6B5A" /></View>
      ) : error ? (
        <View style={styles.centered}>
          <Text style={{ color: '#EF4444', fontSize: 15, marginBottom: 12 }}>Failed to load venues</Text>
          <TouchableOpacity onPress={() => refetch()} style={styles.retryBtn}>
            <Text style={{ color: '#FFFFFF', fontWeight: '600' }}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={venues}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <VenueCard venue={item} />}
          contentContainerStyle={{ paddingTop: 8, paddingBottom: 32 }}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={styles.centered}>
              <Text style={{ color: '#9CA3AF' }}>No {entityType === 'restaurant' ? 'restaurants' : 'hotels'} in {city}</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAFA' },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 60 },
  retryBtn: { backgroundColor: '#1A6B5A', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  cityPicker: {
    flexDirection: 'row', alignItems: 'center', gap: 6, marginHorizontal: 16, marginTop: 12,
    paddingVertical: 10, paddingHorizontal: 14, backgroundColor: '#FFFFFF', borderRadius: 10,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 1,
  },
  cityText: { flex: 1, fontSize: 16, fontWeight: '700', color: '#1A1A2E' },
  cityDropdown: {
    marginHorizontal: 16, marginTop: 4, backgroundColor: '#FFFFFF', borderRadius: 10, overflow: 'hidden',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 8, elevation: 3,
  },
  cityOption: { paddingVertical: 12, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  cityOptionActive: { backgroundColor: '#E8F5F1' },
  cityOptionText: { fontSize: 15, color: '#1A1A2E' },
  cityOptionTextActive: { color: '#1A6B5A', fontWeight: '600' },
  toggleWrap: { paddingHorizontal: 16, paddingVertical: 12 },
});
