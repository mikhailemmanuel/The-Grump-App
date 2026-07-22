import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { UserOut, RefreshTokenOut } from './types';
import { createStore } from './storage';

// ── Storage (web-safe: MMKV on native, localStorage on web) ─────────────────

const storage = createStore('auth');

const KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'user',
} as const;

/** Read tokens from MMKV – used by api.ts (no circular import). */
export function getTokens(): { access_token: string; refresh_token: string } | null {
  const at = storage.getString(KEYS.ACCESS_TOKEN);
  const rt = storage.getString(KEYS.REFRESH_TOKEN);
  if (!at || !rt) return null;
  return { access_token: at, refresh_token: rt };
}

/** Persist tokens to MMKV – used by api.ts refresh interceptor. */
export function setTokens(access_token: string, refresh_token: string): void {
  storage.set(KEYS.ACCESS_TOKEN, access_token);
  storage.set(KEYS.REFRESH_TOKEN, refresh_token);
}

function clearTokens(): void {
  storage.delete(KEYS.ACCESS_TOKEN);
  storage.delete(KEYS.REFRESH_TOKEN);
  storage.delete(KEYS.USER);
}

function getStoredUser(): UserOut | null {
  const raw = storage.getString(KEYS.USER);
  if (!raw) return null;
  try { return JSON.parse(raw) as UserOut; } catch { return null; }
}

function setStoredUser(user: UserOut): void {
  storage.set(KEYS.USER, JSON.stringify(user));
}

// ── Auth Context ────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: UserOut | null;
  isLoggedIn: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Inline fetch helpers (avoid importing api.ts → no circular dep) ─────────

const BASE_URL = __DEV__ ? 'http://localhost:8000' : 'https://api.foodgrump.com';

async function authFetch<T>(path: string, body: Record<string, unknown>, token?: string): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Auth ${res.status}: ${res.statusText}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Provider Component ──────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: validate stored tokens via refresh
  useEffect(() => {
    (async () => {
      const tokens = getTokens();
      if (tokens?.refresh_token) {
        try {
          const data = await authFetch<RefreshTokenOut>(
            '/auth/refresh',
            { refresh_token: tokens.refresh_token },
          );
          setTokens(data.access_token, data.refresh_token);
          // Try to load cached user
          const cached = getStoredUser();
          if (cached) setUser(cached);
        } catch {
          clearTokens();
        }
      }
      setIsLoading(false);
    })();
  }, []);

  const loginFn = useCallback(async (email: string, password: string) => {
    const data = await authFetch<RefreshTokenOut>('/auth/login', { email, password });
    setTokens(data.access_token, data.refresh_token);
    // Fetch user profile – we need a GET, do it manually
    const res = await fetch(`${BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });
    // If there's no /auth/me endpoint, we store a minimal user from the token.
    // For now, store email-based stub; screens can refetch.
    // TODO: replace with real /users/me when available
    if (res.ok) {
      const u: UserOut = await res.json();
      setStoredUser(u);
      setUser(u);
    }
  }, []);

  const registerFn = useCallback(async (email: string, password: string, displayName: string) => {
    const u = await authFetch<UserOut>('/auth/register', {
      email,
      password,
      display_name: displayName,
    });
    setStoredUser(u);
    setUser(u);
    // Auto-login after registration
    const data = await authFetch<RefreshTokenOut>('/auth/login', { email, password });
    setTokens(data.access_token, data.refresh_token);
  }, []);

  const logoutFn = useCallback(async () => {
    try {
      const tokens = getTokens();
      if (tokens?.access_token) {
        await authFetch<void>('/auth/logout', {}, tokens.access_token);
      }
    } catch { /* best-effort */ }
    clearTokens();
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    isLoggedIn: user !== null,
    isLoading,
    login: loginFn,
    register: registerFn,
    logout: logoutFn,
  };

  return React.createElement(AuthContext.Provider, { value }, children);
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
