// Mock Alert Dataset for SignalIQ
// Problem statement: AO-01: 400 alerts, 3 real incidents (93.75% noise reduction)

const baseServices = [
  { name: 'postgres-primary-db', type: 'Database' },
  { name: 'payment-api', type: 'Service' },
  { name: 'api-gateway', type: 'Gateway' },
  { name: 'order-service', type: 'Service' },
  { name: 'auth-service', type: 'Service' },
  { name: 'notification-service', type: 'Service' },
  { name: 'redis-cluster', type: 'Cache' },
  { name: 'search-indexer', type: 'Worker' }
];

const sources = ['Prometheus/Alertmanager', 'Datadog APM', 'AWS CloudWatch', 'Kubernetes Event', 'OpenTelemetry'];

// Incident 1 Alert Templates (Database degradation -> 182 alerts)
const inc1Templates = [
  { msg: 'Postgres Connection pool saturated: active connections > 98%', sev: 'CRITICAL', service: 'postgres-primary-db' },
  { msg: 'Query execution time exceeded threshold: pg_stat_activity query > 8200ms', sev: 'CRITICAL', service: 'postgres-primary-db' },
  { msg: 'Postgres CPU utilization sustained > 94% on primary node', sev: 'CRITICAL', service: 'postgres-primary-db' },
  { msg: 'Read replica replication lag exceeded 15000ms', sev: 'WARNING', service: 'postgres-primary-db' },
  { msg: 'Disk I/O latency spike on /var/lib/postgresql/data: await > 45ms', sev: 'WARNING', service: 'postgres-primary-db' },
  { msg: 'Payment API DB connection timeout after 30000ms: pool exhausted', sev: 'CRITICAL', service: 'payment-api' },
  { msg: 'Payment checkout transaction lock wait timeout exceeded', sev: 'CRITICAL', service: 'payment-api' },
  { msg: 'Order Service failed to persist pending state: db_unavailable', sev: 'CRITICAL', service: 'order-service' },
  { msg: 'API Gateway 500 Internal Server Error rate spike for /v1/checkout', sev: 'CRITICAL', service: 'api-gateway' },
  { msg: 'HTTP client circuit breaker tripped: postgres-client pool', sev: 'WARNING', service: 'payment-api' }
];

// Incident 2 Alert Templates (API Gateway latency & timeouts -> 114 alerts)
const inc2Templates = [
  { msg: 'Envoy ingress upstream response time p99 > 4200ms', sev: 'CRITICAL', service: 'api-gateway' },
  { msg: '504 Gateway Timeout spike: 342 req/min on route /v1/orders', sev: 'CRITICAL', service: 'api-gateway' },
  { msg: 'API Gateway worker thread starvation: active connections > 15000', sev: 'CRITICAL', service: 'api-gateway' },
  { msg: 'TLS handshake latency degraded on cloudfront ingress', sev: 'WARNING', service: 'api-gateway' },
  { msg: 'Auth token validation RPC call timeout between gateway and auth-service', sev: 'CRITICAL', service: 'auth-service' },
  { msg: 'Rate limiter Redis backend cluster connection dropped', sev: 'WARNING', service: 'api-gateway' },
  { msg: 'Order Service ingress queue backpressure: socket closed prematurely', sev: 'WARNING', service: 'order-service' }
];

// Incident 3 Alert Templates (Payment provider error surge -> 79 alerts)
const inc3Templates = [
  { msg: 'Third-party Payment Gateway webhook callback latency > 12000ms', sev: 'CRITICAL', service: 'payment-api' },
  { msg: 'Payment capture failure rate: 42% failed in 5-min sliding window', sev: 'CRITICAL', service: 'payment-api' },
  { msg: 'Dead letter queue depth surged: payment-retry-queue > 5000 items', sev: 'WARNING', service: 'payment-api' },
  { msg: 'Notification Service SMS dispatch worker stalled awaiting payment callback', sev: 'WARNING', service: 'notification-service' },
  { msg: 'Order status transition failed: state machine stuck in PENDING_PAYMENT', sev: 'WARNING', service: 'order-service' }
];

// Uncorrelated sporadic / noisy alerts (25 alerts)
const uncorrelatedTemplates = [
  { msg: 'Cron job backup-s3-snapshot completed with non-zero exit code 2', sev: 'WARNING', service: 'search-indexer' },
  { msg: 'Kubernetes Pod evicted due to ephemeral-storage pressure: runner-tmp-89', sev: 'WARNING', service: 'auth-service' },
  { msg: 'Redis cache hit ratio dropped below 75% for namespace:session_temp', sev: 'INFO', service: 'redis-cluster' },
  { msg: 'DNS lookup jitter observed on kube-dns core-dns-pod-3', sev: 'INFO', service: 'api-gateway' },
  { msg: 'SSL Certificate expiration warning: wildcard.domain.internal in 14 days', sev: 'INFO', service: 'api-gateway' },
  { msg: 'Elasticsearch worker node garbage collection pause > 1200ms', sev: 'WARNING', service: 'search-indexer' },
  { msg: 'Logstash buffer consumption rate slowed: consumer lag 4100', sev: 'INFO', service: 'search-indexer' }
];

export const generateMockAlerts = () => {
  const alerts = [];
  let alertCount = 1;
  const now = new Date('2026-10-28T16:00:00Z');

  // Helper to format ID
  const makeId = (num) => `ALT-${String(num).padStart(4, '0')}`;

  // Helper to offset time
  const getTime = (minutesAgo, secondsOffset = 0) => {
    const d = new Date(now.getTime() - (minutesAgo * 60 + secondsOffset) * 1000);
    return d.toISOString();
  };

  // Generate 182 alerts for INC-001 (Database degradation, between 45m and 15m ago)
  for (let i = 0; i < 182; i++) {
    const tmpl = inc1Templates[i % inc1Templates.length];
    const isDup = i > 15 && (i % 3 === 0 || i % 5 === 0);
    const minAgo = 45 - Math.floor((i / 182) * 30);
    const secOffset = (i * 17) % 60;
    
    alerts.push({
      id: makeId(alertCount++),
      timestamp: getTime(minAgo, secOffset),
      service: tmpl.service,
      severity: tmpl.sev,
      source: sources[i % sources.length],
      message: isDup ? `${tmpl.msg} (deduplicated #${(i % 8) + 1})` : tmpl.msg,
      correlationStatus: isDup ? 'DUPLICATE' : 'CORRELATED',
      incidentId: 'INC-001',
      incidentTitle: 'Database Performance Degradation',
      isDuplicate: isDup,
      duplicateCount: isDup ? Math.floor(Math.random() * 8) + 2 : 1,
      environment: 'production',
      region: 'us-east-1',
      host: `${tmpl.service}-pod-${(i % 5) + 1}`,
      rawPayload: {
        metric: tmpl.service === 'postgres-primary-db' ? 'pg_stat_database_active_connections' : 'http_req_duration_ms',
        value: tmpl.sev === 'CRITICAL' ? (92 + (i % 8)) : (70 + (i % 15)),
        threshold: 80,
        cluster: 'prod-eks-cluster-01',
        fingerprint: `sha256:d8a9f${(i % 12).toString(16)}b9e`
      }
    });
  }

  // Generate 114 alerts for INC-002 (API Gateway latency spike, between 60m and 30m ago)
  for (let i = 0; i < 114; i++) {
    const tmpl = inc2Templates[i % inc2Templates.length];
    const isDup = i > 10 && (i % 2 === 0 || i % 4 === 0);
    const minAgo = 60 - Math.floor((i / 114) * 30);
    const secOffset = (i * 23) % 60;

    alerts.push({
      id: makeId(alertCount++),
      timestamp: getTime(minAgo, secOffset),
      service: tmpl.service,
      severity: tmpl.sev,
      source: sources[(i + 1) % sources.length],
      message: isDup ? `${tmpl.msg} (deduplicated #${(i % 6) + 1})` : tmpl.msg,
      correlationStatus: isDup ? 'DUPLICATE' : 'CORRELATED',
      incidentId: 'INC-002',
      incidentTitle: 'API Gateway Latency Spike',
      isDuplicate: isDup,
      duplicateCount: isDup ? Math.floor(Math.random() * 6) + 2 : 1,
      environment: 'production',
      region: 'us-east-1',
      host: `${tmpl.service}-ingress-${(i % 4) + 1}`,
      rawPayload: {
        metric: 'envoy_cluster_upstream_rq_time',
        value: 4120 + (i * 12),
        threshold: 2000,
        cluster: 'prod-eks-cluster-01',
        fingerprint: `sha256:c7e2b${(i % 14).toString(16)}a1f`
      }
    });
  }

  // Generate 79 alerts for INC-003 (Payment Service Error Surge, between 90m and 40m ago)
  for (let i = 0; i < 79; i++) {
    const tmpl = inc3Templates[i % inc3Templates.length];
    const isDup = i > 8 && (i % 3 === 0);
    const minAgo = 90 - Math.floor((i / 79) * 50);
    const secOffset = (i * 31) % 60;

    alerts.push({
      id: makeId(alertCount++),
      timestamp: getTime(minAgo, secOffset),
      service: tmpl.service,
      severity: tmpl.sev,
      source: sources[(i + 2) % sources.length],
      message: isDup ? `${tmpl.msg} (deduplicated #${(i % 5) + 1})` : tmpl.msg,
      correlationStatus: isDup ? 'DUPLICATE' : 'CORRELATED',
      incidentId: 'INC-003',
      incidentTitle: 'Payment Service Error Surge',
      isDuplicate: isDup,
      duplicateCount: isDup ? Math.floor(Math.random() * 5) + 2 : 1,
      environment: 'production',
      region: 'us-east-1',
      host: `${tmpl.service}-worker-${(i % 3) + 1}`,
      rawPayload: {
        metric: 'payment_webhook_response_code',
        value: 504,
        threshold: 200,
        cluster: 'prod-eks-cluster-01',
        fingerprint: `sha256:b1d4a${(i % 10).toString(16)}e7c`
      }
    });
  }

  // Generate remaining 25 alerts as UNCORRELATED noise (total 182 + 114 + 79 + 25 = 400 alerts)
  for (let i = 0; i < 25; i++) {
    const tmpl = uncorrelatedTemplates[i % uncorrelatedTemplates.length];
    const minAgo = 110 - Math.floor((i / 25) * 100);
    const secOffset = (i * 47) % 60;

    alerts.push({
      id: makeId(alertCount++),
      timestamp: getTime(minAgo, secOffset),
      service: tmpl.service,
      severity: tmpl.sev,
      source: sources[(i + 3) % sources.length],
      message: tmpl.msg,
      correlationStatus: 'UNCORRELATED',
      incidentId: null,
      incidentTitle: null,
      isDuplicate: false,
      duplicateCount: 1,
      environment: 'production',
      region: 'us-east-1',
      host: `${tmpl.service}-node-${(i % 2) + 1}`,
      rawPayload: {
        metric: 'system_log_anomaly_score',
        value: 0.42,
        threshold: 0.85,
        cluster: 'prod-eks-cluster-01',
        fingerprint: `sha256:a9f1c${(i % 8).toString(16)}3d8`
      }
    });
  }

  // Sort by timestamp descending (newest first)
  return alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
};

export const initialMockAlerts = generateMockAlerts();
