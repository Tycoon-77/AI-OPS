// Mock Incidents Dataset for SignalIQ
// 3 Correlated Incidents covering 375 of the 400 alerts

export const mockIncidents = [
  {
    id: 'INC-001',
    title: 'Database Performance Degradation',
    severity: 'CRITICAL',
    status: 'ACTIVE',
    probableRootCauseService: 'postgres-primary-db',
    confidenceScore: 96,
    relatedAlertsCount: 182,
    affectedServices: ['postgres-primary-db', 'payment-api', 'order-service', 'api-gateway'],
    firstDetected: '2026-10-28T15:15:22Z',
    lastUpdated: '2026-10-28T15:45:10Z',
    noiseReduction: '94.5%',
    suspectedCauseType: 'Resource Contention / Connection Pool Starvation',
    probableRootCause: {
      service: 'postgres-primary-db',
      confidenceScore: 96,
      suspectedOrigin: 'Primary Node (pg-primary-node-01)',
      explanation: 'Sustained 98% connection pool saturation and unindexed query lock contention triggered cascading timeouts across dependent transaction pipelines.',
      isConfirmed: false, // Probable vs confirmed distinction required
      evidence: [
        {
          id: 'ev-1',
          type: 'CONFIRMED_METRIC',
          title: 'Active Connection Ceiling Breached',
          description: 'pg_stat_database active connections pegged at 98.4% capacity (492/500 max conns) at 15:15:10Z.',
          confidence: 100,
          isFact: true
        },
        {
          id: 'ev-2',
          type: 'CONFIRMED_METRIC',
          title: 'Query Latency Spike',
          description: 'pg_stat_activity shows 14 queries executing longer than 8,200ms on table `orders_partition_oct`.',
          confidence: 100,
          isFact: true
        },
        {
          id: 'ev-3',
          type: 'PROBABLE_CORRELATION',
          title: 'Cascading Downstream Pool Exhaustion',
          description: 'Payment API connection acquisition wait time rose to 30,000ms within 45 seconds of DB saturation.',
          confidence: 96,
          isFact: false
        },
        {
          id: 'ev-4',
          type: 'PROBABLE_CORRELATION',
          title: 'Circuit Breaker Ingress Tripping',
          description: 'API Gateway returned 500 errors to clients after Payment API rejected incoming order checkout RPCs.',
          confidence: 94,
          isFact: false
        }
      ]
    },
    correlationExplanation: {
      timeProximity: '182 alerts triggered within a synchronized 4-minute time envelope (15:15:22Z to 15:19:30Z).',
      serviceDependency: 'Topology graph maps postgres-primary-db as Tier-0 upstream dependency for Payment API, Order Service, and API Gateway.',
      similarMessages: 'Dense semantic clustering (cosine distance 0.94) on terms "Connection pool timeout", "query execution threshold", and "pg_stat_activity".',
      historicalAssociation: 'Matches incident signature FP-DB-CONN-04 from 14 days ago during end-of-month batch settlement.'
    },
    dependencyChain: [
      { id: 'postgres-primary-db', name: 'Database (Postgres)', role: 'ROOT_CAUSE', status: 'CRITICAL' },
      { id: 'payment-api', name: 'Payment API', role: 'DOWNSTREAM_AFFECTED', status: 'CRITICAL' },
      { id: 'order-service', name: 'Order Service', role: 'DOWNSTREAM_AFFECTED', status: 'CRITICAL' },
      { id: 'api-gateway', name: 'API Gateway', role: 'DOWNSTREAM_AFFECTED', status: 'WARNING' }
    ],
    timeline: [
      { time: '15:15:10Z', event: 'Long-running query initiated on postgres-primary-db by analytics cron worker', type: 'ROOT_CAUSE_EVENT' },
      { time: '15:15:22Z', event: 'First alert ALT-0001: Connection pool saturated > 98%', type: 'ALERT_TRIGGER' },
      { time: '15:16:05Z', event: 'Payment API connection timeout alerts surge (45 alerts in 60s)', type: 'CASCADE' },
      { time: '15:17:30Z', event: 'API Gateway starts returning HTTP 500 for /v1/checkout endpoints', type: 'IMPACT' },
      { time: '15:19:00Z', event: 'SignalIQ AI Engine correlated 182 alerts into INC-001 (Confidence: 96%)', type: 'INTELLIGENCE' }
    ]
  },
  {
    id: 'INC-002',
    title: 'API Gateway Latency Spike',
    severity: 'CRITICAL',
    status: 'INVESTIGATING',
    probableRootCauseService: 'api-gateway',
    confidenceScore: 92,
    relatedAlertsCount: 114,
    affectedServices: ['api-gateway', 'auth-service', 'order-service'],
    firstDetected: '2026-10-28T15:00:15Z',
    lastUpdated: '2026-10-28T15:38:40Z',
    noiseReduction: '92.1%',
    suspectedCauseType: 'Ingress Thread Contention / Ingress Proxy Saturation',
    probableRootCause: {
      service: 'api-gateway',
      confidenceScore: 92,
      suspectedOrigin: 'Envoy Ingress Proxy Layer (ingress-02, ingress-04)',
      explanation: 'Surge in concurrent TLS handshakes and upstream timeout buffer exhaustion caused ingress worker thread starvation, triggering 504 Gateway Timeouts.',
      isConfirmed: false,
      evidence: [
        {
          id: 'ev-201',
          type: 'CONFIRMED_METRIC',
          title: 'Envoy Upstream Response p99 Exceeded',
          description: 'Ingress proxy p99 latency spiked from baseline 45ms to 4,200ms at 15:00:15Z.',
          confidence: 100,
          isFact: true
        },
        {
          id: 'ev-202',
          type: 'CONFIRMED_METRIC',
          title: 'HTTP 504 Gateway Timeout Burst',
          description: 'Gateway emitted 342 req/min HTTP 504 responses across `/v1/orders` and `/v1/auth/verify`.',
          confidence: 100,
          isFact: true
        },
        {
          id: 'ev-203',
          type: 'PROBABLE_CORRELATION',
          title: 'Auth Service RPC Timeout Degradation',
          description: 'Auth service reported socket hangup due to gateway buffer exhaustion rather than internal CPU overload.',
          confidence: 91,
          isFact: false
        }
      ]
    },
    correlationExplanation: {
      timeProximity: '114 alerts occurred within a 7-minute burst across ingress controllers and edge reverse proxies.',
      serviceDependency: 'API Gateway sits at the perimeter fronting Auth Service and Order Service routes.',
      similarMessages: 'Keywords match "504 Gateway Timeout", "Envoy ingress response time p99", and "upstream buffer overflow".',
      historicalAssociation: 'Correlates with previously logged ddos/traffic surge pattern from ingress perimeter.'
    },
    dependencyChain: [
      { id: 'api-gateway', name: 'API Gateway', role: 'ROOT_CAUSE', status: 'CRITICAL' },
      { id: 'auth-service', name: 'Authentication Service', role: 'DOWNSTREAM_AFFECTED', status: 'WARNING' },
      { id: 'order-service', name: 'Order Service', role: 'DOWNSTREAM_AFFECTED', status: 'WARNING' }
    ],
    timeline: [
      { time: '15:00:02Z', event: 'Traffic burst on /v1/orders exceeded 18,000 req/sec at Cloudfront CDN edge', type: 'TRAFFIC_SPIKE' },
      { time: '15:00:15Z', event: 'First alert: Envoy upstream p99 > 4200ms', type: 'ALERT_TRIGGER' },
      { time: '15:02:10Z', event: '504 Gateway Timeout alerts emitted from 4 ingress pods', type: 'CASCADE' },
      { time: '15:05:00Z', event: 'SignalIQ grouped 114 noisy alerts into INC-002 with 92% confidence', type: 'INTELLIGENCE' }
    ]
  },
  {
    id: 'INC-003',
    title: 'Payment Service Error Surge',
    severity: 'WARNING',
    status: 'MONITORING',
    probableRootCauseService: 'payment-api',
    confidenceScore: 88,
    relatedAlertsCount: 79,
    affectedServices: ['payment-api', 'notification-service', 'order-service'],
    firstDetected: '2026-10-28T14:30:45Z',
    lastUpdated: '2026-10-28T15:20:18Z',
    noiseReduction: '91.8%',
    suspectedCauseType: 'Third-Party Webhook Latency / Retry Queue Backpressure',
    probableRootCause: {
      service: 'payment-api',
      confidenceScore: 88,
      suspectedOrigin: 'Webhook Dispatcher Worker Pool',
      explanation: 'Degraded response from external card processing gateway caused internal retry queues to fill up, delaying asynchronous order state transitions.',
      isConfirmed: false,
      evidence: [
        {
          id: 'ev-301',
          type: 'CONFIRMED_METRIC',
          title: 'External Webhook Latency > 12s',
          description: 'Payment provider acknowledgment latency increased by 650% starting at 14:30:45Z.',
          confidence: 100,
          isFact: true
        },
        {
          id: 'ev-302',
          type: 'CONFIRMED_METRIC',
          title: 'Dead Letter Queue Surging',
          description: 'payment-retry-queue accumulated 5,120 unacknowledged settlement messages.',
          confidence: 100,
          isFact: true
        },
        {
          id: 'ev-303',
          type: 'PROBABLE_CORRELATION',
          title: 'Notification Delay Backpressure',
          description: 'Order confirmation SMS workers paused waiting for completed payment intent tokens.',
          confidence: 86,
          isFact: false
        }
      ]
    },
    correlationExplanation: {
      timeProximity: '79 alerts recorded across asynchronous worker queues within 12 minutes.',
      serviceDependency: 'Payment API dispatches confirmation events to Notification Service and Order Service state machine.',
      similarMessages: 'Alerts shared keywords: "webhook callback latency", "payment-retry-queue", "PENDING_PAYMENT".',
      historicalAssociation: 'Similar degradation noted during vendor maintenance window.'
    },
    dependencyChain: [
      { id: 'payment-api', name: 'Payment API', role: 'ROOT_CAUSE', status: 'WARNING' },
      { id: 'order-service', name: 'Order Service', role: 'DOWNSTREAM_AFFECTED', status: 'WARNING' },
      { id: 'notification-service', name: 'Notification Service', role: 'DOWNSTREAM_AFFECTED', status: 'INFO' }
    ],
    timeline: [
      { time: '14:30:45Z', event: 'Third-party provider API latency increased to 12.4s', type: 'EXTERNAL_DEGRADE' },
      { time: '14:32:00Z', event: 'Alert: Payment capture failure rate exceeded 40%', type: 'ALERT_TRIGGER' },
      { time: '14:36:20Z', event: 'Dead letter retry queue crossed threshold (> 5000 items)', type: 'CASCADE' },
      { time: '14:40:00Z', event: 'SignalIQ grouped 79 related worker/queue alerts into INC-003', type: 'INTELLIGENCE' }
    ]
  }
];
