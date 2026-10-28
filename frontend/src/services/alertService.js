import apiClient, { API_BASE_URL, checkBackendHealth } from './api';
import { initialMockAlerts } from '../data/mockAlerts';

// Local in-memory alert storage that persists across sessions if modified/uploaded
let alertCache = [...initialMockAlerts];

export const alertService = {
  // GET /api/alerts
  async getAlerts(params = {}) {
    const isLive = await checkBackendHealth();
    if (isLive) {
      try {
        const response = await apiClient.get('/api/alerts', { params });
        return { data: response.data, isMock: false };
      } catch (err) {
        console.warn('Backend /api/alerts failed, falling back to mock dataset', err);
      }
    }

    // Client-side filtering & pagination for Mock Mode
    let results = [...alertCache];

    if (params.search) {
      const q = params.search.toLowerCase();
      results = results.filter(
        (a) =>
          a.id.toLowerCase().includes(q) ||
          a.message.toLowerCase().includes(q) ||
          a.service.toLowerCase().includes(q) ||
          a.source.toLowerCase().includes(q)
      );
    }

    if (params.severity && params.severity !== 'ALL') {
      results = results.filter((a) => a.severity.toUpperCase() === params.severity.toUpperCase());
    }

    if (params.service && params.service !== 'ALL') {
      results = results.filter((a) => a.service.toLowerCase() === params.service.toLowerCase());
    }

    if (params.status && params.status !== 'ALL') {
      results = results.filter((a) => a.correlationStatus.toUpperCase() === params.status.toUpperCase());
    }

    const page = parseInt(params.page || 1, 10);
    const limit = parseInt(params.limit || 20, 10);
    const startIndex = (page - 1) * limit;
    const paginated = results.slice(startIndex, startIndex + limit);

    return {
      data: {
        total: results.length,
        page,
        limit,
        totalPages: Math.ceil(results.length / limit),
        alerts: paginated,
        stats: {
          total: alertCache.length,
          critical: alertCache.filter((a) => a.severity === 'CRITICAL').length,
          warning: alertCache.filter((a) => a.severity === 'WARNING').length,
          info: alertCache.filter((a) => a.severity === 'INFO').length,
          duplicates: alertCache.filter((a) => a.isDuplicate).length,
          correlated: alertCache.filter((a) => a.correlationStatus === 'CORRELATED').length,
          uncorrelated: alertCache.filter((a) => a.correlationStatus === 'UNCORRELATED').length,
        }
      },
      isMock: true,
      dataSource: 'SignalIQ Local Dataset (400 alerts)'
    };
  },

  // GET /api/alerts/{id}
  async getAlertById(id) {
    const isLive = await checkBackendHealth();
    if (isLive) {
      try {
        const response = await apiClient.get(`/api/alerts/${id}`);
        return { data: response.data, isMock: false };
      } catch (err) {
        console.warn(`Backend /api/alerts/${id} failed, falling back to mock`, err);
      }
    }

    const found = alertCache.find((a) => a.id.toLowerCase() === id.toLowerCase());
    if (!found) {
      throw new Error(`Alert with ID ${id} not found.`);
    }
    return { data: found, isMock: true };
  },

  // POST /api/alerts/upload
  async uploadAlertsFile(file, onProgress) {
    const isLive = await checkBackendHealth();
    if (isLive) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await apiClient.post('/api/alerts/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
              const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              onProgress(percent);
            }
          }
        });
        return { data: response.data, isMock: false };
      } catch (err) {
        console.warn('Backend /api/alerts/upload failed, falling back to mock parser', err);
      }
    }

    // Client-side parser for CSV / JSON in Mock Demo mode
    return new Promise((resolve, reject) => {
      let progress = 0;
      const interval = setInterval(() => {
        progress += 20;
        if (onProgress) onProgress(progress);
        if (progress >= 100) {
          clearInterval(interval);
          try {
            const reader = new FileReader();
            reader.onload = (e) => {
              const text = e.target.result;
              let parsedAlertsCount = 0;

              if (file.name.endsWith('.json')) {
                const json = JSON.parse(text);
                const array = Array.isArray(json) ? json : (json.alerts || []);
                parsedAlertsCount = array.length || 24;
              } else {
                // Basic CSV lines count
                const lines = text.split('\n').filter(Boolean);
                parsedAlertsCount = Math.max(lines.length - 1, 12);
              }

              resolve({
                data: {
                  message: 'Dataset processed successfully',
                  filename: file.name,
                  fileSize: file.size,
                  alertsParsed: parsedAlertsCount,
                  duplicatesIdentified: Math.floor(parsedAlertsCount * 0.28),
                  noiseReducedPercentage: '92.4%',
                  timestamp: new Date().toISOString()
                },
                isMock: true
              });
            };
            reader.onerror = () => reject(new Error('Failed to read file on client side'));
            reader.readAsText(file);
          } catch (error) {
            reject(error);
          }
        }
      }, 150);
    });
  },

  // Reset or seed alerts
  resetAlerts() {
    alertCache = [...initialMockAlerts];
    return alertCache;
  }
};
