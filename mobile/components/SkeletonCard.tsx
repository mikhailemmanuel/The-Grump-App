import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming } from 'react-native-reanimated';

export default function SkeletonCard() {
  const opacity = useSharedValue(0.3);
  useEffect(() => {
    opacity.value = withRepeat(withTiming(1, { duration: 800 }), -1, true);
  }, []);
  const animStyle = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <View style={styles.info}>
          <Animated.View style={[styles.line, styles.lineShort, animStyle]} />
          <Animated.View style={[styles.line, styles.lineLong, animStyle]} />
          <View style={styles.tagsRow}>
            <Animated.View style={[styles.tagPlaceholder, animStyle]} />
            <Animated.View style={[styles.tagPlaceholder, animStyle]} />
          </View>
        </View>
        <Animated.View style={[styles.scorePlaceholder, animStyle]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 16, marginHorizontal: 16, marginBottom: 10 },
  row: { flexDirection: 'row', alignItems: 'center' },
  info: { flex: 1, marginRight: 12 },
  line: { height: 12, borderRadius: 6, backgroundColor: '#E5E7EB', marginBottom: 8 },
  lineShort: { width: '40%' },
  lineLong: { width: '70%' },
  tagsRow: { flexDirection: 'row', gap: 6 },
  tagPlaceholder: { width: 50, height: 20, borderRadius: 6, backgroundColor: '#E5E7EB' },
  scorePlaceholder: { width: 36, height: 36, borderRadius: 8, backgroundColor: '#E5E7EB' },
});
