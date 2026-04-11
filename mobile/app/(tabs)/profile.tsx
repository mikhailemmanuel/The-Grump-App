import React, { useState } from 'react';
import { View, Text, ScrollView, TouchableOpacity, Switch, ActivityIndicator, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../lib/auth';
import { useUserWantToGo, useUserVisited, useUserLists, useUserSaved } from '../../lib/hooks';

type SubTab = 'want_to_go' | 'visited' | 'lists' | 'saved';
type SubFilter = 'all' | 'restaurant' | 'hotel';

const SUB_TABS: { key: SubTab; label: string }[] = [
  { key: 'want_to_go', label: 'Want to Go' },
  { key: 'visited', label: 'Visited' },
  { key: 'lists', label: 'Lists' },
  { key: 'saved', label: 'Saved' },
];

export default function ProfileScreen() {
  const { user, isLoggedIn, logout } = useAuth();
  const { data: wantToGoData, isLoading: wtgLoading } = useUserWantToGo();
  const { data: visitedData, isLoading: visLoading } = useUserVisited();
  const { data: listsData, isLoading: lstLoading } = useUserLists();
  const { data: savedData, isLoading: svdLoading } = useUserSaved();

  const [subTab, setSubTab] = useState<SubTab>('want_to_go');
  const [subFilter, setSubFilter] = useState<SubFilter>('all');
  const [reviewPrivacy, setReviewPrivacy] = useState(false);

  if (!isLoggedIn || !user) {
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

  const subTabData = (): { count: number; loading: boolean } => {
    switch (subTab) {
      case 'want_to_go': return { count: wantToGoData?.length ?? 0, loading: wtgLoading };
      case 'visited': return { count: visitedData?.length ?? 0, loading: visLoading };
      case 'lists': return { count: listsData?.length ?? 0, loading: lstLoading };
      case 'saved': return { count: savedData?.length ?? 0, loading: svdLoading };
    }
  };

  const { count: tabCount, loading: tabLoading } = subTabData();

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.avatar}>
          <Ionicons name="person" size={32} color="#FFFFFF" />
        </View>
        <View style={styles.headerInfo}>
          <Text style={styles.name}>{user.display_name}</Text>
          <Text style={styles.stats}>{user.email}</Text>
        </View>
        <TouchableOpacity style={styles.settingsBtn} onPress={logout}>
          <Ionicons name="log-out-outline" size={22} color="#6B7280" />
        </TouchableOpacity>
      </View>

      {/* Sub tabs */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.subTabs}>
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
      </ScrollView>

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

      {/* Tab content */}
      <View style={styles.placeholder}>
        {tabLoading ? (
          <ActivityIndicator size="large" color="#1A6B5A" />
        ) : tabCount > 0 ? (
          <>
            <Ionicons
              name={subTab === 'want_to_go' ? 'heart' : subTab === 'visited' ? 'checkmark-circle' : subTab === 'lists' ? 'list' : 'bookmark'}
              size={40}
              color="#1A6B5A"
            />
            <Text style={styles.placeholderTitle}>{tabCount} items</Text>
          </>
        ) : (
          <>
            <Ionicons
              name={subTab === 'want_to_go' ? 'heart-outline' : subTab === 'visited' ? 'checkmark-circle-outline' : subTab === 'lists' ? 'list-outline' : 'bookmark-outline'}
              size={40}
              color="#D1D5DB"
            />
            <Text style={styles.placeholderTitle}>
              {subTab === 'want_to_go' ? 'Your Want to Go list' :
               subTab === 'visited' ? 'Places you\'ve been' :
               subTab === 'lists' ? 'Your custom lists' : 'Saved venues'}
            </Text>
            <Text style={styles.placeholderSub}>
              Start exploring to add venues here
            </Text>
          </>
        )}
      </View>

      {/* Settings section */}
      <View style={styles.settingsSection}>
        <Text style={styles.sectionTitle}>Settings</Text>
        <View style={styles.settingRow}>
          <View>
            <Text style={styles.settingLabel}>Review Privacy</Text>
            <Text style={styles.settingDesc}>Hide your reviews from other users</Text>
          </View>
          <Switch
            value={reviewPrivacy}
            onValueChange={setReviewPrivacy}
            trackColor={{ false: '#E5E7EB', true: '#1A6B5A' }}
            thumbColor="#FFFFFF"
          />
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAFAFA',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    paddingTop: 20,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#1A6B5A',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerInfo: {
    flex: 1,
    marginLeft: 14,
  },
  name: {
    fontSize: 22,
    fontWeight: '700',
    color: '#1A1A2E',
  },
  stats: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 2,
  },
  settingsBtn: {
    padding: 8,
  },
  subTabs: {
    paddingHorizontal: 12,
    marginBottom: 10,
  },
  subTab: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginHorizontal: 4,
    borderRadius: 8,
    backgroundColor: '#F3F4F6',
  },
  subTabActive: {
    backgroundColor: '#1A6B5A',
  },
  subTabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  subTabTextActive: {
    color: '#FFFFFF',
  },
  filterRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    gap: 8,
    marginBottom: 16,
  },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  filterChipActive: {
    borderColor: '#1A6B5A',
    backgroundColor: '#E8F5F1',
  },
  filterChipText: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  filterChipTextActive: {
    color: '#1A6B5A',
  },
  placeholder: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  placeholderTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A2E',
    marginTop: 12,
  },
  placeholderSub: {
    fontSize: 13,
    color: '#9CA3AF',
    marginTop: 4,
  },
  settingsSection: {
    marginTop: 24,
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1A1A2E',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FFFFFF',
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  settingLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1A1A2E',
  },
  settingDesc: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
});
