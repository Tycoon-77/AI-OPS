"""dashboard/components/badges.py — band/severity chip renderers."""
import streamlit as st

BAND_CSS = {
    "RED":        ("al-badge al-badge-red",    "● RED · CRITICAL"),
    "ORANGE":     ("al-badge al-badge-orange", "● ORANGE · HIGH"),
    "YELLOW":     ("al-badge al-badge-yellow", "● YELLOW · MEDIUM"),
    "BACKGROUND": ("al-badge al-badge-bg",     "● BACKGROUND"),
}

BAND_BORDER = {
    "RED":        "al-card-red",
    "ORANGE":     "al-card-orange",
    "YELLOW":     "al-card-yellow",
    "BACKGROUND": "al-card-background",
}

BAND_COLOR = {
    "RED":        "#FF4D5E",
    "ORANGE":     "#FF9F43",
    "YELLOW":     "#F5D547",
    "BACKGROUND": "#7C8AAE",
}

SEV_BADGE = {
    "critical": ("al-badge al-badge-red",    "🔴 CRITICAL"),
    "high":     ("al-badge al-badge-orange", "🟠 HIGH"),
    "medium":   ("al-badge al-badge-yellow", "🟡 MEDIUM"),
    "low":      ("al-badge al-badge-bg",     "⚪ LOW"),
}


def band_badge_html(band: str) -> str:
    css_cls, label = BAND_CSS.get(band.upper(), ("al-badge", band))
    return f'<span class="{css_cls}">{label}</span>'


def severity_badge_html(severity: str) -> str:
    css_cls, label = SEV_BADGE.get(severity.lower(), ("al-badge", severity))
    return f'<span class="{css_cls}">{label}</span>'


def action_chip_html(action: str) -> str:
    """Render an acknowledged/escalated chip."""
    if action == "acknowledge":
        return '<span class="al-badge al-badge-ok">✓ Acknowledged</span>'
    if action == "escalate":
        return '<span class="al-badge al-badge-red">⬆ Escalated</span>'
    return ""
