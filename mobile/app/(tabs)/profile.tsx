import React, { useState } from 'react';
import { View, Text, ScrollView, FlatList, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../lib/auth';
import { useUserWantToGo, useUserVisited, useUserSaved } from '../../lib/hooks';
import { USE_LOCAL_DATA } from '../../lib/config';
import type { VenueOut } from '../../lib/types';
import VenueCard from '../../components/VenueCard';

type SubTab = 'want_to_go' | 'visited' | 'saved';
type SubFilter = 'all' | 'restaurant' | 'hotel';

const SUB_TABS: { key: SubTab; label: string }[] = [
  { key: 'want_to_go', label: 'Want to Go' },
  { key: 'visited', label: 'Visited' },
  { key: 'saved', label: 'Saved' },
];

export default function ProfileScreen() {
  const { user, isLoggedIn, logout } = useAuth();
  const { data: wantToGoData, isLoading: wtgLoading } = useUserWantToGo();
  const { data: visitedData, isLoading: visLoading } = useUserVisited();
  const { data: savedData, isLoading: svdLoading } = useUserSaved();

  const [subTab, setSubTab] = useState<SubTab>('want_to_go');
  const [subFilter, setSubFilter] = useState<SubFilter>('all');

  // In offline mode there's no account — collections live on the device.
  if (!USE_LOCAL_DATA && (!isLoggedIn || !user)) {
    return (
      <View style={[styles.container, { alignItems: 'center', justifyContent: 'center', flex: 1 }]}>
        <Ionicons name="person-circle-outline" size={64} color="#D1D5DB" />
        <Text style={{ fontSize: 18, fontWeight: '600', color: '#1A1A2E', marginTop: 16 }}>
          Sign in to view your profile
        </Text>
        <Text style={{ fontSize: 14, color: '#9CA3AF', marginTop: 4 }}>
          Track your reviews, lists, and saved venues
        </Text>
      </View>
    );
  }

  const current = (): { items: VenueOut[]; loading: boolean } => {
    switch (subTab) {
      case 'want_to_go': return { items: (wantToGoData as VenueOut[]) ?? [], loading: wtgLoading };
      case 'visited': return { items: (visitedData as VenueOut[]) ?? [], loading: visLoading };
      case 'saved': return { items: (savedData as VenueOut[]) ?? [], loading: svdLoading };
    }
  };

  const { items, loading } = current();
  const filtered = subFilter === 'all' ? items : items.filter((v) => v.entity_type === subFilter);

  const emptyLabel =
    subTab === 'want_to_go' ? 'Tap the heart on any venue to add it here'
      : subTab === 'visited' ? 'Leave a verdict on a venue and it shows up here'
        : 'Bookmark venues to save them here';

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Ionicons name="person" size={32} color="#FFFFFF" />
        </View>
        <View style={styles.headerInfo}>
          <Text style={styles.name}>{USE_LOCAL_DATA ? 'Your Picks' : user?.display_name}</Text>
          <Text style={styles.stats}>
            {USE_LOCAL_DATA ? 'Saved on this device' : user?.email}
          </Text>
        </View>
        {!USE_LOCAL_DATA && (
          <TouchableOpacity style={styles.settingsBtn} onPress={logout}>
            <Ionicons name="log-out-outline" size={22} color="#6B7280" />
          </TouchableOpacity>
        )}
      </View>

      {/* Sub tabs */}
      <View style={styles.subTabs}>
        {SUB_TABS.map((t) => (
          <TouchableOpacity
            key={t.key}
            style={[styles.subTab, subTab === t.key && styles.subTabActive]}
            onPress={() => setSubTab(t.key)}
          >
            <Text style={[styles.subTabText, subTab === t.key && styles.subTabTextActive]}>
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Sub filter */}
      <View style={styles.filterRow}>
        {(['all', 'restaurant', 'hotel'] as const).map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterChip, subFilter === f && styles.filterChipActive]}
            onPress={() => setSubFilter(f)}
          >
            <Text style={[styles.filterChipText, subFilter === f && styles.filterChipTextActive]}>
              {f === 'all' ? 'All' : f === 'restaurant' ? 'Restaurants' : 'Hotels'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      {loading ? (
        <View style={styles.placeholder}>
          <ActivityIndicator size="large" color="#1A6B5A" />
        </View>
      ) : filtered.length > 0 ? (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <VenueCard venue={item} />}
          contentContainerStyle={{ paddingTop: 8, paddingBottom: 40 }}
        />
      ) : (
        <ScrollView contentContainerStyle={styles.placeholder}>
          <Ionicons
            name={subTab === 'want_to_go' ? 'heart-outline' : subTab === 'visited' ? 'checkmark-circle-outline' : 'bookmark-outline'}
            size={44}
            color="#D1D5DB"
          />
          <Text style={styles.placeholderTitle}>
            {subTab === 'want_to_go' ? 'Nothing saved yet' : subTab === 'visited' ? 'No verdicts yet' : 'Nothing bookmarked'}
          </Text>
          <Text style={styles.placeholderSub}>{emptyLabel}</Text>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAFA' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, paddingTop: 20 },
  avatar: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: '#1A6B5A',
    alignItems: 'center', justifyContent: 'center',
  },
  headerInfo: { flex: 1, marginLeft: 14 },
  name: { fontSize: 22, fontWeight: '700', color: '#1A1A2E' },
  stats: { fontSize: 13, color: '#6B7280', marginTop: 2 },
  settingsBtn: { padding: 8 },
  subTabs: { flexDirection: 'row', paddingHorizontal: 12, marginBottom: 10, gap: 8 },
  subTab: {
    flex: 1, paddingVertical: 8, borderRadius: 8, backgroundColor: '#F3F4F6', alignItems: 'center',
  },
  subTabActive: { backgroundColor: '#1A6B5A' },
  subTabText: { fontSize: 13, fontWeight: '600', color: '#6B7280' },
  subTabTextActive: { color: '#FFFFFF' },
  filterRow: { flexDirection: 'row', paddingHorizontal: 16, gap: 8, marginBottom: 12 },
  filterChip: {
    paddingHorizontal: 12, paddingVertical: 5, borderRadius: 6,
    borderWidth: 1, borderColor: '#E5E7EB',
  },
  filterChipActive: { borderColor: '#1A6B5A', backgroundColor: '#E8F5F1' },
  filterChipText: { fontSize: 12, color: '#6B7280', fontWeight: '500' },
  filterChipTextActive: { color: '#1A6B5A' },
  placeholder: { alignItems: 'center', justifyContent: 'center', paddingVertical: 64, flexGrow: 1 },
  placeholderTitle: { fontSize: 16, fontWeight: '600', color: '#1A1A2E', marginTop: 12 },
  placeholderSub: { fontSize: 13, color: '#9CA3AF', marginTop: 4, textAlign: 'center', paddingHorizontal: 32 },
});
