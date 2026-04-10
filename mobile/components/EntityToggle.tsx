import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { EntityType } from '../lib/types';

interface Props {
  value: EntityType;
  onChange: (value: EntityType) => void;
}

export default function EntityToggle({ value, onChange }: Props) {
  return (
    <View style={styles.container}>
      {(['restaurant', 'hotel'] as const).map((type) => (
        <TouchableOpacity
          key={type}
          style={[styles.button, value === type && styles.active]}
          onPress={() => onChange(type)}
        >
          <Text style={[styles.label, value === type && styles.activeLabel]}>
            {type === 'restaurant' ? 'Restaurants' : 'Hotels'}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#F0F0F0',
    borderRadius: 10,
    padding: 3,
  },
  button: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 8,
  },
  active: {
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  activeLabel: {
    color: '#1A1A2E',
  },
});
