import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';

interface Props {
  message?: string;
}

export default function LoadingState({ message }: Props) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#1A6B5A" />
      {message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 48 },
  message: { color: '#6B7280', fontSize: 14, marginTop: 12 },
});
