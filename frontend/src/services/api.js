import axios from 'axios';

// Default to environment variable or localhost:8000
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 4000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Track whether backend is responding or we are using local intelligence engine / mock data
export let isBackendConnected = false;

// Connectivity check helper
export const checkBackendHealth = async () => {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/health`, { timeout: 1500 });
    isBackendConnected = res.status === 200;
    return isBackendConnected;
  } catch (err) {
    isBackendConnected = false;
    return false;
  }
};

export default apiClient;
