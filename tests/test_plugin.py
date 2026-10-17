import pytest
from flask import Flask

from clawmetry_jumper.evidence import EvidenceStore
from clawmetry_jumper.plugin import create_blueprint, register_all


def app_with_store(store):
    app = Flask(__name__)
    app.config["JUMPER_EVIDENCE_STORE"] = store
    register_all(app)
    return app


def test_shared_live_store_serves_persisted_receipts_without_action_routes(tmp_path):
    with EvidenceStore(tmp_path / "live.duckdb") as store:
        store.append("hello", 0.1, "request", {"request_id": "greeting-1"})
        app = app_with_store(store)
        register_all(app)
        client = app.test_client()
        store.append("hello", 0.2, "controller", {"request_id": "greeting-1", "accepted": True})
        response = client.get("/api/jumper/evidence?run_id=hello&limit=1")
        assert response.status_code == 200
        result = response.get_json()
        assert result["local_simulation"] and result["read_only_view"]
        assert result["runs"][0]["event_count"] == 2
        assert len(result["events"]) == 1 and result["events"][0]["kind"] == "controller"
        assert response.headers["Cache-Control"] == "no-store"
        assert client.post("/api/jumper/evidence", json={"action": "jump"}).status_code == 405
        assert client.post("/api/jumper/action").status_code == 404
        assert all(not ({"POST", "PUT", "DELETE", "PATCH"} & rule.methods)
                   for rule in app.url_map.iter_rules())


def test_constructor_store_and_completed_read_only_file(tmp_path):
    path = tmp_path / "complete.duckdb"
    with EvidenceStore(path) as store:
        store.append("done", 2, "outcome", {"status": "unknown"})
    app = Flask(__name__)
    app.register_blueprint(create_blueprint(db_path=path))
    client = app.test_client()
    assert client.get("/api/jumper/evidence").get_json()["events"][0]["payload"]["status"] == "unknown"
    # The request must release its read-only connection so the next run can write.
    with EvidenceStore(path) as writer:
        writer.append("next", 0, "reminder", {"message": "Time to move"})
    assert len(client.get("/api/jumper/evidence").get_json()["runs"]) == 2
    app2 = Flask(__name__)
    with EvidenceStore(path) as shared:
        app2.register_blueprint(create_blueprint(shared))
        assert app2.test_client().get("/api/jumper/evidence").status_code == 200


@pytest.mark.parametrize("query", ["limit=0", "limit=1001", "limit=true", "limit=-2", "limit=1.0",
                                    "limit=" + "9" * 5000, "run_id=", "run_id=bad%2Frun"])
def test_query_validation_does_not_need_a_collector(query):
    app = Flask(__name__)
    register_all(app)
    response = app.test_client().get("/api/jumper/evidence?" + query)
    assert response.status_code == 400


def test_unavailable_collector_explains_shared_process_without_leaking_paths(tmp_path):
    app = Flask(__name__)
    register_all(app)
    client = app.test_client()
    assert client.get("/api/jumper/evidence").status_code == 503
    private_path = tmp_path / "private-user-name" / "missing.duckdb"
    app.config["JUMPER_EVIDENCE_DB"] = private_path
    response = client.get("/api/jumper/evidence")
    assert response.status_code == 503
    assert "same process" in response.get_json()["error"]
    assert str(private_path) not in response.get_data(as_text=True)
    assert not private_path.exists()


def test_second_reader_refuses_active_writer_config_and_never_claims_zero_events(tmp_path):
    path = tmp_path / "active.duckdb"
    with EvidenceStore(path) as writer:
        writer.append("live", 0, "observation", {})
        app = Flask(__name__)
        app.config["JUMPER_EVIDENCE_DB"] = path
        register_all(app)
        response = app.test_client().get("/api/jumper/evidence")
        assert response.status_code == 503
        assert "events" not in response.get_json()


@pytest.mark.parametrize("key,value", [("JUMPER_EVIDENCE_STORE", object()), ("JUMPER_EVIDENCE_DB", 123)])
def test_invalid_collector_configuration_returns_actionable_unavailable(key, value):
    app = Flask(__name__)
    app.config[key] = value
    register_all(app)
    response = app.test_client().get("/api/jumper/evidence")
    assert response.status_code == 503
    assert "same process" in response.get_json()["error"]


def test_page_is_local_read_only_and_renders_payload_as_text(tmp_path):
    with EvidenceStore(tmp_path / "page.duckdb") as store:
        store.append("r", 0, "reminder", {"message": "<script>alert(1)</script>"})
        client = app_with_store(store).test_client()
        page = client.get("/jumper")
        assert page.status_code == 200 and page.headers["Cache-Control"] == "no-store"
        html = page.get_data(as_text=True)
        assert "Local simulation" in html
        assert "Physical hardware, water handling and tidying are not validated" in html
        assert "payload.textContent=JSON.stringify(event.payload" in html
        assert "innerHTML" not in html and "<script>alert(1)</script>" not in html
        assert "document.hidden" in html
        assert client.get("/api/jumper/evidence").get_json()["events"][0]["payload"]["message"] == "<script>alert(1)</script>"
