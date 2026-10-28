import apiClient, { checkBackendHealth } from './api';
import { mockIncidents } from '../data/mockIncidents';

export const incidentService = {
  // GET /api/incidents
  async getIncidents(params = {}) {
    const isLive = await checkBackendHealth();
    if (isLive) {
      try {
        const response = await apiClient.get('/api/incidents', { params });
        return { data: response.data, isMock: false };
      } catch (err) {
        console.warn('Backend /api/incidents failed, falling back to mock dataset', err);
      }
    }

    let results = [...mockIncidents];
    if (params.severity && params.severity !== 'ALL') {
      results = results.filter((inc) => inc.severity.toUpperCase() === params.severity.toUpperCase());
    }
    if (params.status && params.status !== 'ALL') {
      results = results.filter((inc) => inc.status.toUpperCase() === params.status.toUpperCase());
    }

    return {
      data: results,
      total: results.length,
      isMock: true,
      dataSource: 'SignalIQ Intelligence Engine (Mock Model)'
    };
  },

  // GET /api/incidents/{id}
  async getIncidentById(id) {
    const isLive = await checkBackendHealth();
    if (isLive) {
      try {
        const response = await apiClient.get(`/api/incidents/${id}`);
        return { data: response.data, isMock: false };
      } catch (err) {
        console.warn(`Backend /api/incidents/${id} failed, falling back to mock`, err);
      }
    }

    const found = mockIncidents.find((inc) => inc.id.toLowerCase() === id.toLowerCase());
    if (!found) {
      throw new Error(`Incident with ID ${id} not found.`);
    }
    return { data: found, isMock: true };
  },

  // POST /api/incidents/detect
  async triggerDetection(options = {}) {
    const isLive = await checkBackendHealth();
    if (isLive) {
      try {
        const response = await apiClient.post('/api/incidents/detect', options);
        return { data: response.data, isMock: false };
      } catch (err) {
        console.warn('Backend /api/incidents/detect failed, simulating correlation', err);
      }
    }

    // Simulated correlation execution delay
    await new Promise((res) => setTimeout(res, 800));

    return {
      data: {
        status: 'COMPLETED',
        alertsProcessed: 400,
        incidentsIdentified: 3,
        correlationRate: '93.75%',
        incidents: mockIncidents
      },
      isMock: true
    };
  }
};
