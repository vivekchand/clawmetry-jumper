from clawmetry_jumper.guard import Request, Task, TaskGate


def fresh(**extra):
    return dict(time_s=5., table_margin_m=.3, finite=True, **extra)


def test_scope_and_real_skill_are_both_required():
    gate = TaskGate(Task("sip", frozenset({"wave", "carry"}), frozenset({"glass"})), controls_enabled=True)
    assert gate.decide(Request("1", "sip", "wave"), fresh(), now_s=5).send_to_controller
    assert gate.decide(Request("2", "sip", "jump"), fresh(), now_s=5).status == "denied"
    assert gate.decide(Request("3", "sip", "carry", "phone"), fresh(), now_s=5).status == "denied"
    assert gate.decide(Request("4", "sip", "carry", "glass"), fresh(), now_s=5).status == "unavailable"


def test_default_observes_and_never_claims_physical_stop():
    d = TaskGate(Task("sip", frozenset({"wave"}))).decide(Request("a", "sip", "wave"), fresh(), now_s=5)
    assert d.status == "observed" and not d.send_to_controller and not d.physical_stop_confirmed


def test_duplicate_and_task_substitution_cannot_execute():
    g = TaskGate(Task("sip", frozenset({"wave"})), controls_enabled=True)
    r = Request("a", "sip", "wave")
    assert g.decide(r, fresh(), now_s=5).send_to_controller
    assert not g.decide(r, fresh(), now_s=5).send_to_controller
    assert g.decide(Request("b", "tidy", "wave"), fresh(), now_s=5).status == "denied"


def test_blind_or_nonfinite_or_future_state_never_authorizes():
    g = TaskGate(Task("sip", frozenset({"wave"})), controls_enabled=True)
    for i, obs in enumerate([{}, {"time_s": 4, "finite": True, "table_margin_m": .3},
                             {"time_s": 6, "finite": True, "table_margin_m": .3},
                             {"time_s": 5, "finite": True, "table_margin_m": float("nan")} ]):
        assert g.decide(Request(str(i), "sip", "wave"), obs, now_s=5).status == "unknown"


def test_full_body_edge_margin_blocks_even_when_base_is_inside():
    g = TaskGate(Task("sip", frozenset({"wave"})), controls_enabled=True)
    d = g.decide(Request("a", "sip", "wave"), dict(time_s=5, finite=True, table_margin_m=.05), now_s=5)
    assert d.status == "denied" and not d.send_to_controller


def test_endpoint_outside_inset_is_rejected_and_trajectory_not_invented():
    g = TaskGate(Task("sip", frozenset({"wave", "walk"})), controls_enabled=True)
    assert g.decide(Request("a", "sip", "wave", target_xy=(.85, 0)), fresh(), now_s=5).status == "denied"
    assert g.decide(Request("b", "sip", "walk", target_xy=(0, 0)), fresh(), now_s=5).status == "unavailable"


def test_boolean_state_or_malformed_identifiers_cannot_execute():
    g = TaskGate(Task("sip", frozenset({"wave"})), controls_enabled=True)
    for i, bad in enumerate([{"time_s": True, "table_margin_m": True, "finite": True},
                             {"time_s": "5", "table_margin_m": .3, "finite": True}]):
        assert not g.decide(Request(str(i), "sip", "wave"), bad, now_s=5).send_to_controller
    assert not g.decide(Request("z", "sip", ["wave"]), fresh(), now_s=5).send_to_controller
