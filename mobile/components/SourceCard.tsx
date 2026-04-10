import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SourceRating } from '../lib/types';

interface Props {
  source: SourceRating;
}

export default function SourceCard({ source }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.name}>{source.source}</Text>
      <Text style={styles.rating}>{source.rating}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 14,
    marginRight: 10,
    minWidth: 120,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
    borderWidth: 1,
    borderColor: '#F0F0F0',
  },
  name: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '600',
    marginBottom: 6,
  },
  rating: {
    fontSize: 16,
    color: '#1A1A2E',
    fontWeight: '700',
  },
});
