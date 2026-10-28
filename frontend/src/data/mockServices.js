// Service Topology and Graph Metadata for SignalIQ Service Dependency Map

export const mockServices = [
  {
    id: 'api-gateway',
    name: 'API Gateway',
    type: 'Gateway / Ingress',
    status: 'CRITICAL',
    uptime: '99.91%',
    latency: '340ms',
    rps: '14,250 req/s',
    errorRate: '4.8%',
    activeAlerts: 114,
    associatedIncidents: ['INC-001', 'INC-002'],
    dependencies: ['auth-service', 'order-service', 'payment-api'],
    description: 'Envoy-based edge ingress gateway managing TLS termination, authentication routing, and global rate limiting.',
    maintainer: 'Platform-Traffic-Team',
    healthReason: 'Ingress thread starvation & 504 timeout cascade (INC-002)'
  },
  {
    id: 'auth-service',
    name: 'Authentication Service',
    type: 'Core Service',
    status: 'WARNING',
    uptime: '99.98%',
    latency: '85ms',
    rps: '4,100 req/s',
    errorRate: '1.2%',
    activeAlerts: 18,
    associatedIncidents: ['INC-002'],
    dependencies: ['postgres-primary-db', 'redis-cluster'],
    description: 'OAuth2/JWT token issuance and validation microservice.',
    maintainer: 'Security-Infra',
    healthReason: 'Downstream RPC timeouts triggered by API Gateway thread exhaustion'
  },
  {
    id: 'order-service',
    name: 'Order Service',
    type: 'Core Service',
    status: 'CRITICAL',
    uptime: '99.85%',
    latency: '520ms',
    rps: '2,800 req/s',
    errorRate: '6.4%',
    activeAlerts: 46,
    associatedIncidents: ['INC-001', 'INC-002', 'INC-003'],
    dependencies: ['postgres-primary-db', 'payment-api', 'notification-service'],
    description: 'Order lifecycle orchestration, checkout state machine, and inventory allocation.',
    maintainer: 'Commerce-Core',
    healthReason: 'Database connection exhaustion & payment failure backpressure'
  },
  {
    id: 'payment-api',
    name: 'Payment API',
    type: 'Financial Service',
    status: 'CRITICAL',
    uptime: '99.72%',
    latency: '980ms',
    rps: '950 req/s',
    errorRate: '8.2%',
    activeAlerts: 92,
    associatedIncidents: ['INC-001', 'INC-003'],
    dependencies: ['postgres-primary-db'],
    description: 'PCI-compliant transaction orchestrator interfacing with card networks and external banking APIs.',
    maintainer: 'FinTech-Squad',
    healthReason: 'Primary database connection pool timeouts & webhook queue surges'
  },
  {
    id: 'postgres-primary-db',
    name: 'Database (PostgreSQL)',
    type: 'Primary Datastore',
    status: 'CRITICAL',
    uptime: '99.99%',
    latency: '1,420ms',
    rps: '18,500 qps',
    errorRate: '12.4%',
    activeAlerts: 182,
    associatedIncidents: ['INC-001'],
    dependencies: [],
    description: 'Multi-AZ PostgreSQL cluster storing core ledger, account data, and order transaction records.',
    maintainer: 'DBA-Reliability',
    healthReason: 'Suspected Root Cause for INC-001: Connection pool 98% saturated, query locks'
  },
  {
    id: 'notification-service',
    name: 'Notification Service',
    type: 'Background Worker',
    status: 'HEALTHY',
    uptime: '99.99%',
    latency: '45ms',
    rps: '620 msg/s',
    errorRate: '0.05%',
    activeAlerts: 6,
    associatedIncidents: ['INC-003'],
    dependencies: ['redis-cluster'],
    description: 'Multi-channel messaging service dispatching email, SMS, and mobile push notifications.',
    maintainer: 'Growth-Eng',
    healthReason: 'Operating normally with slight queue delay due to payment state sync'
  },
  {
    id: 'redis-cluster',
    name: 'Redis Cache Cluster',
    type: 'In-Memory Cache',
    status: 'HEALTHY',
    uptime: '100%',
    latency: '1.2ms',
    rps: '38,000 ops/s',
    errorRate: '0.00%',
    activeAlerts: 1,
    associatedIncidents: [],
    dependencies: [],
    description: 'High-throughput Redis cluster used for session caching, distributed locks, and rate limiting tokens.',
    maintainer: 'Platform-Infra',
    healthReason: 'All nodes healthy, memory utilization 42%'
  }
];

// Initial React Flow Node positions
export const initialServiceNodes = [
  {
    id: 'api-gateway',
    type: 'serviceNode',
    position: { x: 50, y: 160 },
    data: { serviceId: 'api-gateway' }
  },
  {
    id: 'auth-service',
    type: 'serviceNode',
    position: { x: 380, y: 50 },
    data: { serviceId: 'auth-service' }
  },
  {
    id: 'order-service',
    type: 'serviceNode',
    position: { x: 380, y: 200 },
    data: { serviceId: 'order-service' }
  },
  {
    id: 'payment-api',
    type: 'serviceNode',
    position: { x: 380, y: 350 },
    data: { serviceId: 'payment-api' }
  },
  {
    id: 'postgres-primary-db',
    type: 'serviceNode',
    position: { x: 740, y: 270 },
    data: { serviceId: 'postgres-primary-db' }
  },
  {
    id: 'notification-service',
    type: 'serviceNode',
    position: { x: 740, y: 100 },
    data: { serviceId: 'notification-service' }
  },
  {
    id: 'redis-cluster',
    type: 'serviceNode',
    position: { x: 740, y: -40 },
    data: { serviceId: 'redis-cluster' }
  }
];

export const initialServiceEdges = [
  { id: 'e-gw-auth', source: 'api-gateway', target: 'auth-service', animated: true, style: { stroke: '#6366F1' } },
  { id: 'e-gw-order', source: 'api-gateway', target: 'order-service', animated: true, style: { stroke: '#EF4444', strokeWidth: 2 } },
  { id: 'e-gw-payment', source: 'api-gateway', target: 'payment-api', animated: true, style: { stroke: '#EF4444', strokeWidth: 2 } },
  { id: 'e-order-payment', source: 'order-service', target: 'payment-api', animated: true, style: { stroke: '#EF4444', strokeWidth: 2 } },
  { id: 'e-order-db', source: 'order-service', target: 'postgres-primary-db', animated: true, style: { stroke: '#EF4444', strokeWidth: 3 } },
  { id: 'e-payment-db', source: 'payment-api', target: 'postgres-primary-db', animated: true, style: { stroke: '#EF4444', strokeWidth: 3 } },
  { id: 'e-order-notif', source: 'order-service', target: 'notification-service', animated: false, style: { stroke: '#38BDF8' } },
  { id: 'e-auth-redis', source: 'auth-service', target: 'redis-cluster', animated: false, style: { stroke: '#22C55E' } },
  { id: 'e-auth-db', source: 'auth-service', target: 'postgres-primary-db', animated: false, style: { stroke: '#94A3B8' } },
  { id: 'e-notif-redis', source: 'notification-service', target: 'redis-cluster', animated: false, style: { stroke: '#22C55E' } }
];
