from alertlens.eval.scorecard import evaluate


def _data():
    alerts = {f"alt_{i}": {"timestamp": "2026-03-03T10:00:00Z", "truth_incident_id": "I1" if i < 4 else ""} for i in range(10)}
    incidents = {"I1": {"start": "2026-03-03T10:00:00Z", "root_cause_service": "db", "type": "x", "buried": False}}
    clusters = [
        {"cluster_id": "c1", "band": "RED", "origin": "web", "origin_candidates": ["web", "db"],
         "alert_ids": ["alt_0", "alt_1", "alt_2", "alt_3", "alt_4", "alt_5", "ghost"]},
        {"cluster_id": "c2", "band": "YELLOW", "origin": "q", "alert_ids": ["alt_6", "alt_7"]},
        {"cluster_id": "c3", "band": "BACKGROUND", "origin": "q", "alert_ids": ["alt_8", "alt_9"]},
    ]
    return clusters, alerts, incidents


def test_card_precision_purity_recall_origin():
    c, a, i = _data()
    r = evaluate(c, a, i, "all")
    assert r["cards"] == 2 and r["card_precision"] == 0.5
    assert r["foreign_alert_ids_ignored"] == 1           # unknown id ignored
    assert r["per_incident"]["I1"]["purity_of_best_card"] == round(4 / 6, 4)
    assert r["recall_at_least_50pct_in_one_card"] == 1.0
    assert r["origin_top1"] == 0.0 and r["origin_top3"] == 1.0   # uses origin_candidates


def test_test_scope_excludes_early_incidents():
    c, a, i = _data()
    assert evaluate(c, a, i, "test")["n_incidents"] == 0
