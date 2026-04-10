import React, { useCallback, useMemo, useRef, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import BottomSheet from '@gorhom/bottom-sheet';
import { EntityType } from '../../lib/types';
import { mockRestaurants, mockHotels } from '../../lib/mockData';
import EntityToggle from '../../components/EntityToggle';
import VenueCard from '../../components/VenueCard';

export default function ExploreScreen() {
  const [entityType, setEntityType] = useState<EntityType>('restaurant');
  const [listView, setListView] = useState(false);
  const bottomSheetRef = useRef<BottomSheet>(null);
  const snapPoints = useMemo(() => ['30%', '65%', '90%'], []);

  const venues = entityType === 'restaurant' ? mockRestaurants : mockHotels;

  const renderVenueList = useCallback(() => (
    <FlatList
      data={venues}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => <VenueCard venue={item} />}
      contentContainerStyle={{ paddingTop: 16, paddingBottom: 32 }}
      showsVerticalScrollIndicator={false}
    />
  ), [venues]);

  if (listView) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <View style={styles.toggleRow}>
            <View style={{ flex: 1 }}>
              <EntityToggle value={entityType} onChange={setEntityType} />
            </View>
            <TouchableOpacity style={styles.viewToggle} onPress={() => setListView(false)}>
              <Ionicons name="map-outline" size={20} color="#1A6B5A" />
            </TouchableOpacity>
          </View>
        </View>
        {renderVenueList()}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.toggleRow}>
          <View style={{ flex: 1 }}>
            <EntityToggle value={entityType} onChange={setEntityType} />
          </View>
          <TouchableOpacity style={styles.viewToggle} onPress={() => setListView(true)}>
            <Ionicons name="list-outline" size={20} color="#1A6B5A" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Map placeholder */}
      <View style={styles.mapPlaceholder}>
        <Ionicons name="map" size={48} color="#D1D5DB" />
        <Text style={styles.mapText}>Map loads here</Text>
        <Text style={styles.mapSubtext}>Requires native build with react-native-maps</Text>
      </View>

      <BottomSheet
        ref={bottomSheetRef}
        index={0}
        snapPoints={snapPoints}
        backgroundStyle={styles.sheetBg}
        handleIndicatorStyle={{ backgroundColor: '#D1D5DB' }}
      >
        <Text style={styles.sheetTitle}>
          {entityType === 'restaurant' ? 'Nearby Restaurants' : 'Nearby Hotels'}
        </Text>
        {renderVenueList()}
      </BottomSheet>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
    backgroundColor: '#FAFAFA',
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  viewToggle: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  mapPlaceholder: {
    flex: 1,
    backgroundColor: '#E5E7EB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  mapText: {
    fontSize: 16,
    color: '#9CA3AF',
    marginTop: 8,
    fontWeight: '600',
  },
  mapSubtext: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 4,
  },
  sheetBg: {
    backgroundColor: '#FAFAFA',
    borderRadius: 20,
  },
  sheetTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A2E',
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
});
