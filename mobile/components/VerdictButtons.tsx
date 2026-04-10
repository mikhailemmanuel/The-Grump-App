import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';
import { Verdict } from '../lib/types';

interface Props {
  selected?: Verdict;
  onSelect: (verdict: Verdict) => void;
}

const VERDICTS: { key: Verdict; emoji: string; label: string }[] = [
  { key: 'go_back', emoji: '👍', label: "I'd go back" },
  { key: 'iffy', emoji: '🤷', label: "I'm iffy" },
  { key: 'would_not', emoji: '👎', label: "I wouldn't go back" },
];

export default function VerdictButtons({ selected, onSelect }: Props) {
  const handlePress = (verdict: Verdict) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onSelect(verdict);
  };

  return (
    <View style={styles.container}>
      {VERDICTS.map(({ key, emoji, label }) => (
        <TouchableOpacity
          key={key}
          style={[styles.button, selected === key && styles.selected]}
          onPress={() => handlePress(key)}
          activeOpacity={0.7}
        >
          <Text style={styles.emoji}>{emoji}</Text>
          <Text style={[styles.label, selected === key && styles.selectedLabel]} numberOfLines={2}>
            {label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    gap: 10,
  },
  button: {
    flex: 1,
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 8,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  selected: {
    borderColor: '#1A6B5A',
    backgroundColor: '#E8F5F1',
  },
  emoji: {
    fontSize: 24,
    marginBottom: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6B7280',
    textAlign: 'center',
  },
  selectedLabel: {
    color: '#1A6B5A',
  },
});
