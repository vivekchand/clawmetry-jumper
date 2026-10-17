"""Optional paid tooling must not retry ambiguous submissions or expose keys."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def helper():
    path = Path(__file__).resolve().parents[1] / 'scripts/neural_narration.py'
    spec = importlib.util.spec_from_file_location('neural_narration_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def receipt_path(helper, payload, tmp_path):
    digest = hashlib.sha256(json.dumps([helper.MODEL, payload], sort_keys=True).encode()).hexdigest()
    return tmp_path / (digest + '.json')


def test_missing_credentials_do_not_create_paid_intent(helper, tmp_path, monkeypatch):
    monkeypatch.delenv('FAL_KEY', raising=False)
    monkeypatch.delenv('FAL_CREDENTIALS_FILE', raising=False)
    with pytest.raises(RuntimeError, match='no system voice fallback'):
        helper.queued_result({'text': 'Authored words'}, tmp_path)
    assert not list(tmp_path.iterdir())


def test_queue_credential_is_never_sent_to_a_redirect_or_foreign_host(helper):
    for url in ['http://queue.fal.run/test', 'https://queue.fal.run.evil.test/a',
                'https://queue.fal.run:443/a', 'https://example.test/a']:
        with pytest.raises(RuntimeError, match='unexpected queue host') as exc:
            helper.queue_request(url, 'never-log-this-key')
        assert 'never-log-this-key' not in str(exc.value)
    assert helper.NoRedirect().redirect_request(None, None, None, None, None, None) is None


def test_cached_result_needs_no_credential_or_network(helper, tmp_path, monkeypatch):
    payload = {'text': 'Authored words'}
    helper.save(receipt_path(helper, payload, tmp_path),
                {'model': helper.MODEL, 'input': payload, 'result': {'audio': {'url': 'https://example.test/audio.mp3'}}})
    monkeypatch.setattr(helper, 'credential', lambda: pytest.fail('Cached result read credentials'))
    monkeypatch.setattr(helper, 'queue_request', lambda *_a: pytest.fail('Cached result queried provider'))
    assert helper.queued_result(payload, tmp_path)['audio']['url'].endswith('.mp3')


def test_uncertain_submission_is_persisted_and_never_automatically_retried(helper, tmp_path, monkeypatch):
    monkeypatch.setenv('FAL_KEY', 'private-test-key')
    calls = []
    def unavailable(*args):
        calls.append(args)
        raise OSError('transport interrupted')
    monkeypatch.setattr(helper, 'queue_request', unavailable)
    payload = {'text': 'Authored words'}
    with pytest.raises(OSError):
        helper.queued_result(payload, tmp_path)
    with pytest.raises(RuntimeError, match='ambiguous'):
        helper.queued_result(payload, tmp_path)
    assert len(calls) == 1
    receipt = receipt_path(helper, payload, tmp_path).read_text()
    assert 'private-test-key' not in receipt
