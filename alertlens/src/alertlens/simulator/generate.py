"""
simulator.py - Synthetic Alert, Service Graph, and Incident Cascade Generator for AlertLens.
Owned by Person A.

Generates:
1. data/dependencies.json: {"service": ["downstream_service", ...]} (70 services, 4 tiers DAG)
2. data/alerts.csv: alert_id,timestamp,source,service,severity,message,truth_incident_id
3. data/incidents.csv: incident_id,start,end,root_cause_service,type,buried

Also provides:
- --sample: outputs a lightweight 30-alert sample (data/sample/) by 8:00pm milestone
- --full: outputs 3 weeks (21 days) with 400-900 alerts/day, 2 buried incidents, held-out cert_expiry
"""

import argparse
import csv
import json
import os
import random
from datetime import datetime, timedelta, timezone

# Ensure deterministic generation
DEFAULT_SEED = 42

TIER_0_INFRA = [
    "db-primary", "db-replica", "cache-redis", "msg-queue",
    "dns", "object-storage", "log-cluster", "secrets-vault"
]

TIER_1_PLATFORM = [
    "auth-service", "identity", "config-service", "feature-flags",
    "rate-limiter", "scheduler", "search-index", "email-gateway",
    "sms-gateway", "payments-gateway", "file-service", "geo-service",
    "audit-log", "service-mesh"
]

TIER_2_BUSINESS = [
    "cart", "orders", "payments", "inventory", "catalog", "pricing",
    "search", "recommendations", "notifications", "billing", "shipping",
    "loyalty", "coupons", "tax", "fraud-detection", "user-profile",
    "subscriptions", "discounts", "returns", "analytics", "reviews",
    "warehouse", "fulfillment", "currency-exchange", "wishlist",
    "accounting", "invoicing", "vendor-portal", "customer-support", "feed-service"
]

TIER_3_EDGE = [
    "api-gateway", "web-frontend", "mobile-bff", "admin-portal",
    "partner-gateway", "cdn-origin", "graphql-gateway", "merchant-api",
    "webhook-dispatcher", "public-api", "iot-gateway", "internal-proxy",
    "ingress-controller", "checkout-web", "search-api", "pos-gateway",
    "stream-consumer", "event-broker"
]

# Total = 8 + 14 + 30 + 18 = 70 services
ALL_SERVICES = TIER_0_INFRA + TIER_1_PLATFORM + TIER_2_BUSINESS + TIER_3_EDGE

SERVICE_TIERS = {}
for s in TIER_0_INFRA:
    SERVICE_TIERS[s] = 0
for s in TIER_1_PLATFORM:
    SERVICE_TIERS[s] = 1
for s in TIER_2_BUSINESS:
    SERVICE_TIERS[s] = 2
for s in TIER_3_EDGE:
    SERVICE_TIERS[s] = 3

# Alert Templates catalogue (~45 templates across monitoring, logging, uptime)
ALERT_TEMPLATES = {
    "latency_high": {
        "source": "monitoring", "severity": "high",
        "variants": [
            "p95 latency {ms}ms exceeds threshold on {host}",
            "Response time degraded: {ms}ms on {host}",
            "Slow responses detected, p99={ms}ms on host {host}",
            "Latency SLO burn rate {n}x on {host}"
        ]
    },
    "error_rate_5xx": {
        "source": "monitoring", "severity": "high",
        "variants": [
            "HTTP 500 internal server error spike ({pct}% errors) on {host}",
            "Elevated 5xx error rate ({pct}%) observed on {host}",
            "HTTP 502/503 upstream gateway error rate {pct}% on {host}"
        ]
    },
    "timeout_upstream": {
        "source": "logging", "severity": "medium",
        "variants": [
            "Connection timeout after {ms}ms contacting upstream service on {host}",
            "Upstream socket timeout ({ms}ms) requesting {host}",
            "Client request timed out waiting for downstream response on {host}"
        ]
    },
    "conn_refused": {
        "source": "logging", "severity": "high",
        "variants": [
            "Connection refused connecting to port {port} on {host}",
            "Failed to establish TCP connection to {host}:{port}: ECONNREFUSED",
            "Target host {host} actively refused socket connection"
        ]
    },
    "endpoint_down": {
        "source": "uptime", "severity": "critical",
        "variants": [
            "Synthetic ping check failed for endpoint {host}: target unreachable",
            "Health probe returned HTTP 503 for service {host}",
            "Blackbox probe failed: dial tcp {ip}: connection reset by peer"
        ]
    },
    "oom_killed": {
        "source": "logging", "severity": "high",
        "variants": [
            "Container killed: Out of Memory (OOMKilled) on worker {host}",
            "Process terminated by cgroup OOM killer: memory limit {n}MiB reached on {host}",
            "Fatal error: Java heap space out of memory on node {host}"
        ]
    },
    "restart_loop": {
        "source": "monitoring", "severity": "high",
        "variants": [
            "Pod CrashLoopBackOff: {n} restarts in 10 minutes on {host}",
            "Service restart loop detected on {host} ({n} crashes in window)",
            "Container failed liveness check after restart on {host}"
        ]
    },
    "replication_lag": {
        "source": "monitoring", "severity": "high",
        "variants": [
            "Database replication lag {n}s exceeds threshold on replica {host}",
            "Read-replica out of sync by {n} seconds behind primary on {host}",
            "Replication stream delayed by {n}s on {host}"
        ]
    },
    "disk_full": {
        "source": "monitoring", "severity": "critical",
        "variants": [
            "Disk utilization {pct}% exceeds critical threshold on {host}",
            "Filesystem /var/log is {pct}% full on node {host}",
            "No space left on device: disk space critical ({pct}%) on {host}"
        ]
    },
    "cert_expired": {
        "source": "uptime", "severity": "critical",
        "variants": [
            "SSL/TLS certificate has expired or is invalid for {host}",
            "TLS validation failed: certificate expired 0 days ago on {host}",
            "HTTPS handshake failed: certificate has expired on {host}"
        ]
    },
    "tls_handshake_fail": {
        "source": "logging", "severity": "high",
        "variants": [
            "SSL routine:tls_process_server_certificate:certificate verify failed for {host}",
            "TLS connection failed: certificate untrusted or expired on {host}",
            "Handshake exception: PKIX path validation failed contacting {host}"
        ]
    },
    "cache_miss_storm": {
        "source": "monitoring", "severity": "medium",
        "variants": [
            "Cache miss rate spike to {pct}% on cluster {host}",
            "Redis cache hit ratio dropped to {pct}% on {host}",
            "Eviction rate spike and cache degradation on {host}"
        ]
    },
    "queue_lag": {
        "source": "monitoring", "severity": "high",
        "variants": [
            "Message backlog in queue exceeds {n} messages on {host}",
            "Consumer group lag exceeds SLA ({n} messages pending) on {host}",
            "Kafka partition consumer lag {n} messages on broker {host}"
        ]
    },
    "dns_resolution_fail": {
        "source": "logging", "severity": "high",
        "variants": [
            "Failed to resolve hostname '{host}': NXDOMAIN",
            "DNS lookup timeout for {host} after {ms}ms",
            "Resolver error: host not found for service {host}"
        ]
    },
    "deploy_error_spike": {
        "source": "monitoring", "severity": "high",
        "variants": [
            "Error spike immediately following release v{n}.0 on {host}",
            "Rollout failure: canary error rate {pct}% exceeds baseline on {host}",
            "Post-deployment smoke tests failed on service {host}"
        ]
    },
    "packet_loss": {
        "source": "monitoring", "severity": "high",
        "variants": [
            "Inter-zone network packet loss {pct}% between regions on {host}",
            "Network interface packet drop rate elevated ({pct}%) on {host}",
            "TCP retransmission rate {pct}% between pods on {host}"
        ]
    },
    "payment_gateway_5xx": {
        "source": "logging", "severity": "critical",
        "variants": [
            "Payment processor returned HTTP 504 gateway timeout for cust-{cust}",
            "Charge authorization failed: upstream PSP unreachable for customer cust-{cust}",
            "Payment capture failure rate {pct}% on {host}"
        ]
    },
    "health_check_failed": {
        "source": "uptime", "severity": "medium",
        "variants": [
            "HTTP healthcheck probe failed on {host} (attempt {n}/3)",
            "Liveness probe failed for container on node {host}",
            "Target group health check failed on {host}: Connection timed out"
        ]
    },
    "cpu_throttled": {
        "source": "monitoring", "severity": "low",
        "variants": [
            "Container CPU throttling at {pct}% on host {host}",
            "CPU utilization exceeded 85% on {host}",
            "Periodic batch job high CPU load ({pct}%) on {host}"
        ]
    },
    "slow_query": {
        "source": "logging", "severity": "low",
        "variants": [
            "Slow query execution time {ms}ms logged on {host}",
            "Query elapsed {ms}ms exceeding slow-query threshold on {host}",
            "Reporting query took {ms}ms to complete on {host}"
        ]
    },
    "deprecated_api_call": {
        "source": "logging", "severity": "low",
        "variants": [
            "Deprecated v1 API called by client cust-{cust} on {host}",
            "Endpoint /api/v1/legacy invoked by cust-{cust} on {host}",
            "Warning: deprecated protocol header used in request on {host}"
        ]
    },
    "retry_rate_elevated": {
        "source": "monitoring", "severity": "low",
        "variants": [
            "RPC retry rate {pct}% elevated on client {host}",
            "Exponential backoff retry attempt {n} on {host}",
            "Transient retry burst detected on client {host}"
        ]
    }
}


def build_service_graph(rng: random.Random):
    """
    Builds a 70-service, 4-tier DAG.
    Returns:
      downstream_map: dict {service: [downstream_services...]}
      Where 'downstream_service' means services that depend on 'service'
      (i.e., when 'service' fails, 'downstream_service' is impacted).
    """
    # Initialize adjacency: service -> list of downstream dependents
    downstream_map = {s: [] for s in ALL_SERVICES}
    # Also track upstream for validation: s -> list of services s depends on
    depends_on = {s: [] for s in ALL_SERVICES}

    # Tier 1 depends on 1-3 Tier 0 services
    for t1 in TIER_1_PLATFORM:
        num_deps = rng.randint(1, 3)
        chosen_t0 = rng.sample(TIER_0_INFRA, num_deps)
        for t0 in chosen_t0:
            downstream_map[t0].append(t1)
            depends_on[t1].append(t0)

    # Tier 2 depends on 2-4 from Tiers 0 and 1
    # Critical business services (payments, orders, cart) must depend on db-primary
    critical_tier2 = ["payments", "orders", "cart"]
    for crit in critical_tier2:
        if "db-primary" not in depends_on[crit]:
            downstream_map["db-primary"].append(crit)
            depends_on[crit].append("db-primary")

    for t2 in TIER_2_BUSINESS:
        # choose 1-2 from Tier 0, 1-2 from Tier 1
        num_t0 = rng.randint(1, 2)
        num_t1 = rng.randint(1, 2)
        chosen_t0 = rng.sample(TIER_0_INFRA, num_t0)
        chosen_t1 = rng.sample(TIER_1_PLATFORM, num_t1)
        for t0 in chosen_t0:
            if t2 not in downstream_map[t0]:
                downstream_map[t0].append(t2)
                depends_on[t2].append(t0)
        for t1 in chosen_t1:
            if t2 not in downstream_map[t1]:
                downstream_map[t1].append(t2)
                depends_on[t2].append(t1)

    # Tier 3 depends on 2-4 Tier 2 services
    for t3 in TIER_3_EDGE:
        num_deps = rng.randint(2, 4)
        chosen_t2 = rng.sample(TIER_2_BUSINESS, num_deps)
        for t2 in chosen_t2:
            if t3 not in downstream_map[t2]:
                downstream_map[t2].append(t3)
                depends_on[t3].append(t2)

    # Ensure every Tier 0 service has at least 6 transitive dependents
    for t0 in TIER_0_INFRA:
        # compute transitive dependents
        visited = set()
        queue = list(downstream_map[t0])
        while queue:
            curr = queue.pop(0)
            if curr not in visited:
                visited.add(curr)
                queue.extend(downstream_map[curr])
        # If less than 6, connect to additional Tier 1 or Tier 2
        while len(visited) < 6:
            candidates = [s for s in TIER_1_PLATFORM + TIER_2_BUSINESS if s not in visited]
            if not candidates:
                break
            pick = rng.choice(candidates)
            downstream_map[t0].append(pick)
            visited.add(pick)
            queue.extend(downstream_map[pick])

    # Sort all target lists for determinism
    for k in downstream_map:
        downstream_map[k] = sorted(list(set(downstream_map[k])))

    return downstream_map


def format_message(template_str: str, service: str, rng: random.Random) -> str:
    """Formats an alert message with realistic parameters."""
    host = f"{service}-prod-{rng.randint(1, 16):02d}"
    ip = f"10.{rng.randint(10, 192)}.{rng.randint(1, 254)}.{rng.randint(1, 254)}"
    ms = rng.choice([450, 820, 1250, 2400, 4800, 7500])
    pct = rng.choice([25, 48, 72, 89, 95, 99])
    n = rng.choice([3, 5, 8, 12, 24, 45])
    cust = f"cust-{rng.randint(1000, 9999)}"
    port = rng.choice([5432, 6379, 8080, 8443, 9092, 443])
    return template_str.format(host=host, ip=ip, ms=ms, pct=pct, n=n, cust=cust, port=port)


def generate_cascade_alerts(
    incident_id: str,
    incident_type: str,
    root_service: str,
    start_time: datetime,
    duration_min: int,
    downstream_map: dict,
    rng: random.Random,
    alert_counter: list
):
    """
    Simulates alert cascade propagation from root cause service along downstream dependency edges.
    Features:
    - Hop propagation probability p_hop = 0.85 * (0.9 ** depth)
    - Jitter delay per hop (20-90s)
    - 15% silent hops
    - Multi-tool alerts (monitoring, logging, uptime)
    - Alert flapping/repeating every 2-5 minutes
    """
    alerts = []

    # Map incident types to alert signatures
    type_signatures = {
        "db_slowdown": {
            "root_templates": ["replication_lag", "latency_high"],
            "cascade_templates": ["latency_high", "timeout_upstream", "error_rate_5xx"]
        },
        "bad_deploy": {
            "root_templates": ["deploy_error_spike", "error_rate_5xx"],
            "cascade_templates": ["error_rate_5xx", "latency_high", "timeout_upstream"]
        },
        "memory_leak": {
            "root_templates": ["oom_killed", "restart_loop"],
            "cascade_templates": ["endpoint_down", "timeout_upstream"]
        },
        "payment_outage": {
            "root_templates": ["payment_gateway_5xx", "conn_refused"],
            "cascade_templates": ["error_rate_5xx", "timeout_upstream", "endpoint_down"]
        },
        "cert_expiry": {
            "root_templates": ["cert_expired", "tls_handshake_fail"],
            "cascade_templates": ["endpoint_down", "conn_refused"]
        },
        "disk_full": {
            "root_templates": ["disk_full"],
            "cascade_templates": ["error_rate_5xx", "timeout_upstream"]
        },
        "cache_failure": {
            "root_templates": ["conn_refused", "cache_miss_storm"],
            "cascade_templates": ["latency_high", "timeout_upstream"]
        },
        "queue_backlog": {
            "root_templates": ["queue_lag"],
            "cascade_templates": ["latency_high", "timeout_upstream"]
        },
        "dns_failure": {
            "root_templates": ["dns_resolution_fail"],
            "cascade_templates": ["timeout_upstream", "endpoint_down"]
        }
    }

    sig = type_signatures.get(incident_type, type_signatures["db_slowdown"])

    # Traverse downstream using BFS
    queue = [(root_service, 0, start_time)]
    visited_services = {root_service}
    affected_services = {root_service: start_time}

    while queue:
        curr_svc, depth, curr_time = queue.pop(0)
        downstreams = downstream_map.get(curr_svc, [])
        for down_svc in downstreams:
            if down_svc in visited_services:
                continue
            # 15% silent hops
            if rng.random() < 0.15:
                continue
            # Hop propagation probability decays with depth
            p_hop = 0.85 * (0.9 ** depth)
            if rng.random() < p_hop:
                hop_delay = timedelta(seconds=rng.randint(20, 90))
                svc_time = curr_time + hop_delay
                visited_services.add(down_svc)
                affected_services[down_svc] = svc_time
                queue.append((down_svc, depth + 1, svc_time))

    # For each affected service, emit alerts (root service gets root templates; cascades get cascade templates)
    for svc, svc_start in affected_services.items():
        is_root = (svc == root_service)
        tmpl_pool = sig["root_templates"] if is_root else sig["cascade_templates"]

        # Number of flapping waves during incident duration
        num_waves = max(2, duration_min // rng.randint(3, 6))
        for wave in range(num_waves):
            wave_time = svc_start + timedelta(minutes=wave * rng.randint(2, 5), seconds=rng.randint(0, 45))
            if wave_time > start_time + timedelta(minutes=duration_min):
                break

            # 1 to 2 alerts per wave on this service
            chosen_tmpl_keys = rng.sample(tmpl_pool, min(len(tmpl_pool), rng.randint(1, 2)))
            for tmpl_key in chosen_tmpl_keys:
                tmpl_info = ALERT_TEMPLATES[tmpl_key]
                msg_variant = rng.choice(tmpl_info["variants"])
                message = format_message(msg_variant, svc, rng)

                alert_counter[0] += 1
                alert_id = f"alt_{alert_counter[0]:06d}"
                alerts.append({
                    "alert_id": alert_id,
                    "timestamp": wave_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "source": tmpl_info["source"],
                    "service": svc,
                    "severity": tmpl_info["severity"],
                    "message": message,
                    "truth_incident_id": incident_id
                })

    return alerts


def generate_noise_alerts(
    day_start: datetime,
    is_noise_storm: bool,
    rng: random.Random,
    alert_counter: list
):
    """
    Generates background noise for a given 24h day.
    Includes rules N1-N7, random singletons, and noise storms (on buried days).
    Target: 400-900 baseline alerts per day; storm adds 600-800 alerts.
    """
    alerts = []

    # Noise rules definitions
    # N1: disk_80pct on log-cluster every ~15 min
    for minute in range(0, 1440, rng.randint(13, 17)):
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "monitoring",
            "service": "log-cluster",
            "severity": "medium",
            "message": format_message("Disk usage warning: /var/log reached 80% on {host}", "log-cluster", rng),
            "truth_incident_id": ""
        })

    # N2: healthcheck blips on random edge services (~10/hour across the day)
    for _ in range(rng.randint(180, 240)):
        minute = rng.randint(0, 1439)
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        svc = rng.choice(TIER_3_EDGE)
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "uptime",
            "service": svc,
            "severity": "low",
            "message": format_message("Transient healthcheck probe timeout (1/3) on {host}", svc, rng),
            "truth_incident_id": ""
        })

    # N3: nightly batch CPU spikes (02:00-02:45)
    for _ in range(rng.randint(25, 40)):
        minute = rng.randint(120, 165)
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        svc = rng.choice(["analytics", "accounting", "invoicing", "scheduler"])
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "monitoring",
            "service": svc,
            "severity": "low",
            "message": format_message("Scheduled nightly job CPU spike at {pct}% on {host}", svc, rng),
            "truth_incident_id": ""
        })

    # N4: slow query info (~40/day)
    for _ in range(rng.randint(35, 45)):
        minute = rng.randint(0, 1439)
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "logging",
            "service": "analytics",
            "severity": "low",
            "message": format_message("Reporting query elapsed {ms}ms on {host}", "analytics", rng),
            "truth_incident_id": ""
        })

    # N5: deprecated API call (~50/day)
    for _ in range(rng.randint(45, 60)):
        minute = rng.randint(0, 1439)
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        svc = rng.choice(TIER_2_BUSINESS + TIER_3_EDGE)
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "logging",
            "service": svc,
            "severity": "low",
            "message": format_message("Deprecated v1 API invoked by client cust-{cust} on {host}", svc, rng),
            "truth_incident_id": ""
        })

    # N6: retry rate elevated (~40/day)
    for _ in range(rng.randint(35, 50)):
        minute = rng.randint(0, 1439)
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        svc = rng.choice(TIER_2_BUSINESS)
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "monitoring",
            "service": svc,
            "severity": "low",
            "message": format_message("Transient RPC retry rate elevated ({pct}%) on {host}", svc, rng),
            "truth_incident_id": ""
        })

    # N7: Ambiguous latency warning on search service (~20/day)
    for _ in range(rng.randint(18, 25)):
        minute = rng.randint(0, 1439)
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "monitoring",
            "service": "search",
            "severity": "medium",
            "message": format_message("Search query p95 latency warning {ms}ms on {host}", "search", rng),
            "truth_incident_id": ""
        })

    # Random singletons across any service
    for _ in range(rng.randint(120, 180)):
        minute = rng.randint(0, 1439)
        ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
        svc = rng.choice(ALL_SERVICES)
        tmpl_key = rng.choice(["health_check_failed", "cpu_throttled", "slow_query", "retry_rate_elevated"])
        tmpl_info = ALERT_TEMPLATES[tmpl_key]
        msg = format_message(rng.choice(tmpl_info["variants"]), svc, rng)
        alert_counter[0] += 1
        alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": tmpl_info["source"],
            "service": svc,
            "severity": tmpl_info["severity"],
            "message": msg,
            "truth_incident_id": ""
        })

    # If it is a noise storm day (buried incidents), add 600-800 extra alerts over a 3-hour window
    if is_noise_storm:
        storm_start_min = rng.randint(500, 700)  # midday storm
        for _ in range(rng.randint(650, 800)):
            minute = storm_start_min + rng.randint(0, 180)
            if minute >= 1440:
                minute = 1439
            ts = day_start + timedelta(minutes=minute, seconds=rng.randint(0, 59))
            svc = rng.choice(TIER_2_BUSINESS + TIER_3_EDGE)
            tmpl_key = rng.choice(["latency_high", "error_rate_5xx", "timeout_upstream", "retry_rate_elevated"])
            tmpl_info = ALERT_TEMPLATES[tmpl_key]
            msg = format_message(rng.choice(tmpl_info["variants"]), svc, rng)
            alert_counter[0] += 1
            alerts.append({
                "alert_id": f"alt_{alert_counter[0]:06d}",
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": tmpl_info["source"],
                "service": svc,
                "severity": tmpl_info["severity"],
                "message": f"[STORM] {msg}",
                "truth_incident_id": ""
            })

    return alerts


def generate_tiny_sample(output_dir: str = "data/sample"):
    """
    Generates a tiny 30-alert sample for Person B and Person C to unblock early work (Milestone 8:00pm).
    Contains:
    - 1 real incident cascade on 'db-primary' (18 alerts)
    - 12 noise alerts
    - data/sample/dependencies.json
    - data/sample/alerts.csv
    - data/sample/incidents.csv
    - data/sample/clusters.json (mock for Person C's UI)
    """
    os.makedirs(output_dir, exist_ok=True)
    rng = random.Random(DEFAULT_SEED)

    downstream_map = build_service_graph(rng)
    with open(os.path.join(output_dir, "dependencies.json"), "w", encoding="utf-8") as f:
        json.dump(downstream_map, f, indent=2)

    start_time = datetime(2026, 3, 2, 14, 0, 0, tzinfo=timezone.utc)
    inc_id = "inc_sample_01"
    inc_end = start_time + timedelta(minutes=35)

    # 1 incident record
    incidents = [{
        "incident_id": inc_id,
        "start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": inc_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root_cause_service": "db-primary",
        "type": "db_slowdown",
        "buried": False
    }]

    # Cascade alerts
    alert_counter = [0]
    cascade_alerts = generate_cascade_alerts(
        incident_id=inc_id,
        incident_type="db_slowdown",
        root_service="db-primary",
        start_time=start_time,
        duration_min=30,
        downstream_map=downstream_map,
        rng=rng,
        alert_counter=alert_counter
    )

    # Select 18 cascade alerts to keep sample compact
    if len(cascade_alerts) > 18:
        # keep first 3 (root) and sample rest
        cascade_alerts = cascade_alerts[:3] + cascade_alerts[3:18]

    # Generate 12 noise alerts around the same time window
    noise_alerts = []
    for i in range(12):
        ts = start_time + timedelta(minutes=rng.randint(0, 30), seconds=rng.randint(0, 59))
        svc = rng.choice(["analytics", "scheduler", "log-cluster", "email-gateway"])
        tmpl_key = rng.choice(["slow_query", "cpu_throttled", "health_check_failed"])
        tmpl_info = ALERT_TEMPLATES[tmpl_key]
        alert_counter[0] += 1
        noise_alerts.append({
            "alert_id": f"alt_{alert_counter[0]:06d}",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": tmpl_info["source"],
            "service": svc,
            "severity": tmpl_info["severity"],
            "message": format_message(rng.choice(tmpl_info["variants"]), svc, rng),
            "truth_incident_id": ""
        })

    all_sample_alerts = cascade_alerts + noise_alerts
    all_sample_alerts.sort(key=lambda x: x["timestamp"])

    # Write sample alerts.csv
    with open(os.path.join(output_dir, "alerts.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "alert_id", "timestamp", "source", "service", "severity", "message", "truth_incident_id"
        ])
        writer.writeheader()
        writer.writerows(all_sample_alerts)

    # Write sample incidents.csv
    with open(os.path.join(output_dir, "incidents.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "incident_id", "start", "end", "root_cause_service", "type", "buried"
        ])
        writer.writeheader()
        writer.writerows(incidents)

    # Write mock clusters.json for Person C
    sample_cluster_services = list(set(a["service"] for a in cascade_alerts))
    sample_cluster_alert_ids = [a["alert_id"] for a in cascade_alerts]
    mock_clusters = [
        {
            "cluster_id": "c1",
            "band": "RED",
            "origin": "db-primary",
            "alert_ids": sample_cluster_alert_ids,
            "services": sample_cluster_services,
            "start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": inc_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "alert_count": len(sample_cluster_alert_ids),
            "dep_path": ["db-primary", "auth-service", "api-gateway"],
            "reasons": [
                f"{len(sample_cluster_alert_ids)} alerts within 30 min",
                "All services depend on db-primary",
                "Near-identical latency & timeout templates"
            ]
        }
    ]
    with open(os.path.join(output_dir, "clusters.json"), "w", encoding="utf-8") as f:
        json.dump(mock_clusters, f, indent=2)

    print(f"Sample data written to '{output_dir}/': {len(all_sample_alerts)} alerts, 1 incident, dependencies.json, clusters.json")


def generate_full_dataset(output_dir: str = "data", days: int = 21, seed: int = DEFAULT_SEED):
    """
    Generates the full multi-week dataset:
    - 21 days (Week 1 & 2 = train, Week 3 = test)
    - 400-900 alerts/day
    - 5 core incident types + held-out cert_expiry + 2 buried incidents in noise storms
    - Writes:
      data/dependencies.json
      data/alerts.csv
      data/incidents.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    rng = random.Random(seed)

    downstream_map = build_service_graph(rng)
    with open(os.path.join(output_dir, "dependencies.json"), "w", encoding="utf-8") as f:
        json.dump(downstream_map, f, indent=2)

    base_start = datetime(2026, 3, 2, 0, 0, 0, tzinfo=timezone.utc)  # Monday
    alert_counter = [0]
    all_alerts = []
    all_incidents = []

    # Incident schedule across 3 weeks (21 days)
    # Day offsets (0 = Week 1 Mon, ..., 20 = Week 3 Sun)
    incident_schedule = [
        # Week 1 (Train)
        {"day": 1, "type": "db_slowdown", "root": "db-primary", "time": "14:15", "dur": 40, "buried": False},
        {"day": 3, "type": "bad_deploy", "root": "orders", "time": "16:30", "dur": 35, "buried": False},
        {"day": 5, "type": "memory_leak", "root": "cart", "time": "11:20", "dur": 45, "buried": False},

        # Week 2 (Train)
        {"day": 7, "type": "disk_full", "root": "log-cluster", "time": "09:40", "dur": 30, "buried": False},
        {"day": 9, "type": "cache_failure", "root": "cache-redis", "time": "15:00", "dur": 35, "buried": False},
        # BURIED #1: network_partition on Day 10 (Thursday) during storm
        {"day": 10, "type": "payment_outage", "root": "payments", "time": "11:00", "dur": 50, "buried": True},
        {"day": 11, "type": "queue_backlog", "root": "msg-queue", "time": "13:10", "dur": 30, "buried": False},

        # Week 3 (Test)
        {"day": 14, "type": "dns_failure", "root": "dns", "time": "10:15", "dur": 25, "buried": False},
        # HELD-OUT TYPE: cert_expiry on Day 16 (Wednesday)
        {"day": 16, "type": "cert_expiry", "root": "auth-service", "time": "15:45", "dur": 35, "buried": False},
        # BURIED #2: db_slowdown on Day 17 (Thursday) during storm
        {"day": 17, "type": "db_slowdown", "root": "db-primary", "time": "11:30", "dur": 45, "buried": True},
        {"day": 18, "type": "bad_deploy", "root": "inventory", "time": "14:00", "dur": 30, "buried": False},
    ]

    # Pre-index incidents by day
    incidents_by_day = {}
    for inc in incident_schedule:
        incidents_by_day.setdefault(inc["day"], []).append(inc)

    for day_idx in range(days):
        current_day_start = base_start + timedelta(days=day_idx)
        has_buried = any(inc["buried"] for inc in incidents_by_day.get(day_idx, []))

        # 1. Generate background noise
        noise = generate_noise_alerts(
            day_start=current_day_start,
            is_noise_storm=has_buried,
            rng=rng,
            alert_counter=alert_counter
        )
        all_alerts.extend(noise)

        # 2. Generate scheduled incidents
        for inc_spec in incidents_by_day.get(day_idx, []):
            hour, minute = map(int, inc_spec["time"].split(":"))
            inc_start = current_day_start + timedelta(hours=hour, minutes=minute)
            inc_end = inc_start + timedelta(minutes=inc_spec["dur"])
            inc_id = f"inc_{day_idx + 1:02d}_{inc_spec['type'][:3]}"

            all_incidents.append({
                "incident_id": inc_id,
                "start": inc_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": inc_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "root_cause_service": inc_spec["root"],
                "type": inc_spec["type"],
                "buried": inc_spec["buried"]
            })

            cascade = generate_cascade_alerts(
                incident_id=inc_id,
                incident_type=inc_spec["type"],
                root_service=inc_spec["root"],
                start_time=inc_start,
                duration_min=inc_spec["dur"],
                downstream_map=downstream_map,
                rng=rng,
                alert_counter=alert_counter
            )
            all_alerts.extend(cascade)

    # Sort all alerts chronologically
    all_alerts.sort(key=lambda x: x["timestamp"])

    # Write alerts.csv
    alerts_file = os.path.join(output_dir, "alerts.csv")
    with open(alerts_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "alert_id", "timestamp", "source", "service", "severity", "message", "truth_incident_id"
        ])
        writer.writeheader()
        writer.writerows(all_alerts)

    # Write incidents.csv
    incidents_file = os.path.join(output_dir, "incidents.csv")
    with open(incidents_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "incident_id", "start", "end", "root_cause_service", "type", "buried"
        ])
        writer.writeheader()
        writer.writerows(all_incidents)

    # Print summary statistics
    print("=" * 60)
    print(f"Full Dataset Generated ({days} days) in '{output_dir}/':")
    print(f"- Total Alerts: {len(all_alerts)} (avg {len(all_alerts) // days} / day)")
    print(f"- Total Incidents: {len(all_incidents)}")
    print(f"  * Buried Incidents: {sum(1 for i in all_incidents if i['buried'])}")
    print(f"  * Cert Expiry (Held-Out): {sum(1 for i in all_incidents if i['type'] == 'cert_expiry')}")
    print(f"- Dependencies JSON: {len(downstream_map)} services written")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AlertLens Simulator (Person A)")
    parser.add_argument("--sample", action="store_true", help="Generate tiny 30-alert sample (data/sample/)")
    parser.add_argument("--full", action="store_true", help="Generate full 21-day dataset (data/)")
    parser.add_argument("--days", type=int, default=21, help="Number of days to simulate (default: 21)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG Seed for reproducibility")
    parser.add_argument("--out", type=str, default="data", help="Output directory")

    args = parser.parse_args()

    if args.sample:
        generate_tiny_sample(output_dir="data/sample")
    else:
        # Generate both by default so nobody is blocked!
        generate_tiny_sample(output_dir="data/sample")
        generate_full_dataset(output_dir=args.out, days=args.days, seed=args.seed)
