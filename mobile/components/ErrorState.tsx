import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({ message = 'Something went wrong', onRetry }: Props) {
  return (
    <View style={styles.container}>
      <Ionicons name="alert-circle-outline" size={40} color="#DC2626" />
      <Text style={styles.message}>{message}</Text>
      {onRetry && (
        <TouchableOpacity style={styles.button} onPress={onRetry}>
          <Text style={styles.buttonText}>Retry</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 48 },
  message: { color: '#6B7280', fontSize: 15, marginTop: 12, textAlign: 'center', paddingHorizontal: 32 },
  button: { marginTop: 16, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8, backgroundColor: '#1A6B5A' },
  buttonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '600' },
});
