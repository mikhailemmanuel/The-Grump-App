import React from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StyleSheet } from 'react-native';
import { AuthProvider } from '../lib/auth';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60 * 1000 },
  },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
      <GestureHandlerRootView style={styles.root}>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen
            name="venue/[id]"
            options={{
              headerShown: true,
              headerTitle: '',
              headerTransparent: true,
              headerBackTitle: 'Back',
            }}
          />
        </Stack>
      </GestureHandlerRootView>
      </AuthProvider>
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
