import apiClient, { checkBackendHealth } from './api';
import { mockServices, initialServiceNodes, initialServiceEdges } from '../data/mockServices';

export const serviceGraphService = {
  // GET /api/services/graph
  async getServiceGraph() {
    const isLive = await checkBackendHealth();
    if (isLive) {
      try {
        const response = await apiClient.get('/api/services/graph');
        return { data: response.data, isMock: false };
      } catch (err) {
        console.warn('Backend /api/services/graph failed, falling back to mock graph', err);
      }
    }

    return {
      data: {
        services: mockServices,
        nodes: initialServiceNodes,
        edges: initialServiceEdges,
      },
      isMock: true,
      dataSource: 'Sample Service Dependency Topology (Configured Model)'
    };
  }
};
