import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ScoreTier } from '../lib/types';

const COLORS: Record<ScoreTier, string> = {
  gold: '#D4A843',
  silver: '#94A3B8',
  bronze: '#CD7F32',
  none: '#9CA3AF',
};

function getTier(score: number): ScoreTier {
  if (score >= 85) return 'gold';
  if (score >= 70) return 'silver';
  if (score >= 55) return 'bronze';
  return 'none';
}

interface Props {
  score: number;
  size?: 'small' | 'large';
}

export default function ScoreBadge({ score, size = 'small' }: Props) {
  const tier = getTier(score);
  const color = COLORS[tier];
  const isLarge = size === 'large';

  return (
    <View style={[styles.badge, { backgroundColor: color }, isLarge && styles.badgeLarge]}>
      <Text style={[styles.text, isLarge && styles.textLarge]}>{score}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 36,
  },
  badgeLarge: {
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 8,
    minWidth: 52,
  },
  text: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  textLarge: {
    fontSize: 22,
  },
});
