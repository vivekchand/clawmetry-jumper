import math

import pytest

from clawmetry_jumper.evidence import EvidenceStore
from clawmetry_jumper.monitor import DeskMonitor, NotificationOutbox


def snapshot(at=0., *, right=.3, height=.3, tilt=0):
    return {"time_s": at, "finite": True, "evidence_kind": "simulation",
            "position_m": [0., 0., height], "tilt_deg": tilt,
            "collision_aabb_m": {"min": [-.3, -.2, height-.1], "max": [right, .2, height+.1]},
            "table_bounds_m": {"min": [-.86, -.58, 0], "max": [.86, .58, 0]},
            "table_margin_m": min(.56, .86-right, .38)}


def kinds(alerts):
    return [a["type"] for a in alerts]


def test_full_body_edge_approach_crossing_and_episode_recovery():
    monitor = DeskMonitor()
    assert monitor.update(snapshot(), 0) == []
    near = monitor.update(snapshot(.1, right=.78), .1)
    assert kinds(near) == ["boundary_approach"]
    # The base remains at the desk center, while one extended body crosses.
    crossed = monitor.update(snapshot(.2, right=.9), .2)
    assert kinds(crossed) == ["boundary_crossed"]
    assert crossed[0]["severity"] == "critical"
    assert crossed[0]["measurements"]["table_margin_m"] == pytest.approx(-.04)
    assert monitor.update(snapshot(.3, right=.9), .3) == []
    assert monitor.update(snapshot(.4, right=.78), .4) == []
    assert monitor.update(snapshot(.5), .5) == []
    assert kinds(monitor.update(snapshot(.6, right=.78), .6)) == ["boundary_approach"]
    assert all(a["evidence_kind"] == "simulation" and not a["physical_stop_confirmed"] for a in near+crossed)


def test_lift_and_tilt_alerts_are_measured_and_deduplicated():
    monitor = DeskMonitor()
    monitor.update(snapshot(), 0)
    alerts = monitor.update(snapshot(.1, height=.37, tilt=40), .1)
    assert set(kinds(alerts)) == {"unexpected_lift", "excessive_tilt"}
    assert monitor.update(snapshot(.2, height=.37, tilt=40), .2) == []
    monitor.update(snapshot(.3), .3)
    assert "unexpected_lift" in kinds(monitor.update(snapshot(.4, height=.4), .4))
    authorized = DeskMonitor(baseline_height_m=.3, movement_authorized=True)
    assert kinds(authorized.update(snapshot(0, height=.5, tilt=40), 0)) == ["excessive_tilt"]


def test_observation_gap_is_unknown_and_does_not_clear_hazard_evidence():
    monitor = DeskMonitor()
    monitor.update(snapshot(0, right=.9), 0)
    alerts = monitor.update(None, .1)
    assert kinds(alerts) == ["observation_lost"] and alerts[0]["outcome"] == "unknown"
    assert monitor.update(snapshot(0), .3) == []
    assert kinds(monitor.update(snapshot(.4, right=.9), .4)) == ["observation_restored"]
    monitor.update(snapshot(.5), .5)
    assert "boundary_crossed" in kinds(monitor.update(snapshot(.6, right=.9), .6))


@pytest.mark.parametrize("change,now", [
    ({"finite": False}, 0), ({"evidence_kind": "hardware"}, 0), ({"time_s": .1}, 0),
    ({"time_s": 0}, .15), ({"tilt_deg": math.nan}, 0), ({"position_m": [0,0,math.inf]}, 0),
    ({"table_margin_m": .5}, 0), ({"collision_aabb_m": {"min": [0,0,0], "max": [0,0,0]}}, 0),
    ({"table_bounds_m": None}, 0), ({"time_s": True}, 0), ({}, math.nan), ({}, -1),
])
def test_bad_or_stale_evidence_never_becomes_a_safe_outcome(change, now):
    state = snapshot()
    state.update(change)
    alerts = DeskMonitor().update(state, now)
    assert kinds(alerts) == ["observation_lost"]
    assert alerts[0]["outcome"] == "unknown"
    assert not alerts[0]["physical_stop_confirmed"]


def test_reordered_clock_is_unknown():
    monitor = DeskMonitor()
    monitor.update(snapshot(1), 1)
    assert kinds(monitor.update(snapshot(.9), .9)) == ["observation_lost"]
    assert kinds(monitor.update(snapshot(1.1), 1.1)) == ["observation_restored"]


def test_missing_collision_geometry_is_not_replaced_with_base_distance():
    state = snapshot()
    del state["collision_aabb_m"]
    assert kinds(DeskMonitor().update(state, 0)) == ["observation_lost"]


def test_outbox_defaults_to_local_not_configured_and_never_opens_network(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.build_opener", lambda *_: pytest.fail("Unexpected network access"))
    with EvidenceStore(tmp_path / "notifications.duckdb") as store:
        alert = DeskMonitor().update(None, 0)[0]
        receipt = NotificationOutbox(store, "r").submit(alert, sim_time_s=0)
        assert receipt["status"] == "not_configured" and not receipt["phone_delivery_confirmed"]
        assert store.events()[0]["payload"] == receipt


def test_opt_in_webhook_records_receipt_but_never_claims_phone_delivery(tmp_path, monkeypatch):
    calls = []
    class Response:
        status = 202
        def __enter__(self): return self
        def __exit__(self, *_): pass
    class Transport:
        def open(self, request, timeout):
            calls.append((request.full_url, timeout))
            return Response()
    monkeypatch.setattr("urllib.request.build_opener", lambda *_: Transport())
    url = "https://notifications.example/receiver?token=private"
    with EvidenceStore(tmp_path / "webhook.duckdb") as store:
        alert = DeskMonitor().update(None, 0)[0]
        receipt = NotificationOutbox(store, "r", enabled=True, webhook_url=url).submit(alert, sim_time_s=0)
        assert receipt["status"] == "webhook_accepted" and not receipt["phone_delivery_confirmed"]
        assert calls == [(url, 3.)]
        assert [e["payload"]["status"] for e in store.events()] == ["pending", "webhook_accepted"]
        assert "private" not in str(store.events())


def test_webhook_failures_are_local_and_do_not_expose_destination(tmp_path, monkeypatch):
    class Broken:
        def open(self, *_args, **_kwargs):
            raise OSError("private destination and token")
    monkeypatch.setattr("urllib.request.build_opener", lambda *_: Broken())
    with EvidenceStore(tmp_path / "failed.duckdb") as store:
        receipt = NotificationOutbox(store, "r", enabled=True, webhook_url="https://example.com/secret").submit(
            DeskMonitor().update(None, 0)[0], sim_time_s=0)
        assert receipt["status"] == "failed"
        assert "secret" not in str(store.events()) and "private" not in str(store.events())


@pytest.mark.parametrize("url", [None, "http://example.com", "https://user:secret@example.com", "https://example.com/#token"])
def test_webhook_requires_explicit_https_destination(url):
    with pytest.raises(ValueError):
        NotificationOutbox(None, "r", enabled=True, webhook_url=url)
