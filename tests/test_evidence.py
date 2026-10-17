import concurrent.futures
import math

import duckdb
import pytest

from clawmetry_jumper.evidence import EvidenceStore, MAX_PAYLOAD_BYTES


def test_decision_receipts_survive_restart_and_remain_separate(tmp_path):
    path = tmp_path / "evidence.duckdb"
    with EvidenceStore(path) as store:
        ids = [store.append("desk-1", time, kind, payload) for time, kind, payload in [
            (0, "request", {"request_id": "jump-1", "action": "jump"}),
            (0, "decision", {"request_id": "jump-1", "allowed": False}),
            (0.1, "observation", {"height_m": 0.3}),
            (0.2, "outcome", {"status": "unknown", "reason": "observation lost"}),
        ]]
        assert ids == sorted(set(ids))
        expected = store.events()
    with EvidenceStore(path, read_only=True) as reader:
        assert reader.events() == expected
        assert [row["kind"] for row in expected] == ["request", "decision", "observation", "outcome"]
        assert reader.runs() == [{"run_id": "desk-1", "event_count": 4,
                                  "started_sim_time_s": 0.0, "latest_sim_time_s": 0.2,
                                  "last_event_id": ids[-1]}]
        with pytest.raises(PermissionError):
            reader.append("desk-1", 1, "controller", {"accepted": True})
    with EvidenceStore(path) as writer:
        assert writer.append("desk-1", 1, "reminder", {"message": "Take a short break"}) > ids[-1]


def test_latest_window_is_bounded_filtered_and_in_capture_order(tmp_path):
    with EvidenceStore(tmp_path / "events.duckdb") as store:
        for i in range(8):
            store.append("first" if i % 2 == 0 else "second", i, "observation", {"sample": i})
        assert [e["payload"]["sample"] for e in store.events(limit=3)] == [5, 6, 7]
        assert [e["payload"]["sample"] for e in store.events("first", 2)] == [4, 6]
        assert store.events("missing") == []
        assert [run["run_id"] for run in store.runs()] == ["second", "first"]


def test_shared_simulator_and_server_threads_do_not_race(tmp_path):
    with EvidenceStore(tmp_path / "threads.duckdb") as store:
        def capture(worker):
            for i in range(12):
                store.append(f"run-{worker}", i / 10, "observation", {"sample": i})
                store.events(limit=2)
                store.runs()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(capture, range(4)))
        events = store.events(limit=100)
        assert len(events) == len({event["event_id"] for event in events}) == 48
        assert len(store.runs()) == 4


@pytest.mark.parametrize("run_id,time,kind,payload", [
    ("", 0, "request", {}), ("x" * 129, 0, "request", {}),
    ("bad/run", 0, "request", {}), (None, 0, "request", {}),
    ("r", math.nan, "request", {}), ("r", math.inf, "request", {}),
    ("r", -1, "request", {}), ("r", True, "request", {}),
    ("r", "1", "request", {}), ("r", 10**400, "request", {}),
    ("r", 0, "command.execute", {}), ("r", 0, [], {}),
    ("r", 0, "request", []), ("r", 0, "request", {"value": math.nan}),
    ("r", 0, "request", {"value": object()}),
    ("r", 0, "request", {"value": "x" * MAX_PAYLOAD_BYTES}),
])
def test_invalid_evidence_never_reaches_persistence(tmp_path, run_id, time, kind, payload):
    with EvidenceStore(tmp_path / "validation.duckdb") as store:
        with pytest.raises(ValueError):
            store.append(run_id, time, kind, payload)
        assert store.events() == []


@pytest.mark.parametrize("limit", [0, -1, 1001, True, "2", 1.5, None])
def test_invalid_query_limits_are_rejected(tmp_path, limit):
    with EvidenceStore(tmp_path / "limits.duckdb") as store:
        with pytest.raises(ValueError):
            store.events(limit=limit)


def test_close_is_idempotent_and_missing_read_only_file_is_not_created(tmp_path):
    store = EvidenceStore(tmp_path / "closed.duckdb")
    store.close()
    store.close()
    with pytest.raises(RuntimeError, match="closed"):
        store.events()
    path = tmp_path / "never-created.duckdb"
    with pytest.raises(duckdb.Error):
        EvidenceStore(path, read_only=True)
    assert not path.exists()
