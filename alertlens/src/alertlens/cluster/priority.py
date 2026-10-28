"""
Priority scoring, banding, and surfacing decision.

Formula (BACKEND_STRUCTURE §5.8):
    priority = 0.30·sev + 0.25·min(1, n_services/10)
             + 0.20·min(1, blast_radius/70)
             + 0.15·history_match
             + 0.10·min(1, ln(n_alerts)/ln(100))

Bands:
    RED        score >= 0.75  OR  max_severity == critical (4)
    ORANGE     0.55 <= score < 0.75
    YELLOW     surfaced by safety net, score < 0.55
    BACKGROUND not surfaced
"""
from __future__ import annotations

import math


SEV_WEIGHTS = {1: 0.0, 2: 0.33, 3: 0.67, 4: 1.0}


def priority_score(
    max_severity_num: int,
    n_services: int,
    blast_radius: int,
    history_match: float,
    n_alerts: int,
) -> float:
    sev       = SEV_WEIGHTS.get(max_severity_num, 0.0)
    svc_score = min(1.0, n_services / 10)
    blast     = min(1.0, blast_radius / 70)
    alert_s   = min(1.0, math.log(max(n_alerts, 1)) / math.log(100))
    return (
        0.30 * sev
        + 0.25 * svc_score
        + 0.20 * blast
        + 0.15 * history_match
        + 0.10 * alert_s
    )


def get_band(score: float, max_severity_num: int) -> str:
    if max_severity_num == 4 or score >= 0.75:
        return "RED"
    if score >= 0.55:
        return "ORANGE"
    return "YELLOW"


def should_surface(
    score: float,
    max_severity_num: int,
    history_match: float,
    n_groups: int,
    n_services: int,
    surface_threshold: float = 0.55,
) -> tuple[bool, str | None]:
    """Return (surfaced, reason_string_or_None)."""
    if score >= surface_threshold:
        return True, "priority"
    if max_severity_num == 4:
        return True, "critical_severity"
    if history_match >= 0.80 and n_groups >= 2:
        return True, "history_match"
    if n_services >= 4:
        return True, "multi_service"
    return False, None
