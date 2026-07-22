/**
 * Cross-platform key/value storage.
 *
 * On native we use react-native-mmkv (fast, synchronous). On web MMKV's JSI
 * module isn't available, so we fall back to localStorage (also synchronous),
 * and to an in-memory map if even that is missing (SSR / prerender).
 */
import { Platform } from 'react-native';

export interface KVStore {
  getString(key: string): string | undefined;
  set(key: string, value: string): void;
  delete(key: string): void;
}

function makeWebStore(id: string): KVStore {
  const prefix = `fg:${id}:`;
  const hasLS = (() => {
    try {
      return typeof localStorage !== 'undefined' && localStorage !== null;
    } catch {
      return false;
    }
  })();
  if (!hasLS) {
    const mem = new Map<string, string>();
    return {
      getString: (k) => mem.get(prefix + k),
      set: (k, v) => { mem.set(prefix + k, v); },
      delete: (k) => { mem.delete(prefix + k); },
    };
  }
  return {
    getString: (k) => localStorage.getItem(prefix + k) ?? undefined,
    set: (k, v) => localStorage.setItem(prefix + k, v),
    delete: (k) => localStorage.removeItem(prefix + k),
  };
}

export function createStore(id: string): KVStore {
  if (Platform.OS === 'web') {
    return makeWebStore(id);
  }
  // Lazily require so web bundles never touch the native module.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { MMKV } = require('react-native-mmkv');
  return new MMKV({ id });
}
