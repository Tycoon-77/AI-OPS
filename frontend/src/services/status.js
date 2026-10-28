import { useSyncExternalStore } from 'react';
import axios from 'axios';
import { API_BASE_URL } from './api';

// Single source of truth for "is the backend live" and the headline counts.
// Everything in the navbar/sidebar/footer reads from here; nothing is hardcoded.
let state = {
  live: null, // null = checking, true = live data, false = mock fallback
  health: null,
  stats: null, // /api/incidents/stats
  checkedAt: null,
};
const listeners = new Set();
const emit = () => listeners.forEach((l) => l());
const set = (patch) => {
  state = { ...state, ...patch };
  emit();
};

export const refreshStatus = async () => {
  try {
    const [h, s] = await Promise.all([
      axios.get(`${API_BASE_URL}/api/health`, { timeout: 2500 }),
      axios.get(`${API_BASE_URL}/api/incidents/stats`, { timeout: 4000 }),
    ]);
    set({ live: h.status === 200, health: h.data, stats: s.data, checkedAt: Date.now() });
  } catch (e) {
    set({ live: false, health: null, stats: null, checkedAt: Date.now() });
  }
};

let started = false;
const start = () => {
  if (started) return;
  started = true;
  refreshStatus();
  setInterval(refreshStatus, 10000);
};

export const useBackendStatus = () => {
  start();
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
  );
};

export const fmtInt = (n) => (typeof n === 'number' ? n.toLocaleString('en-US') : '—');
