"""In-process HTTP handler calls only: no socket, server or browser is started."""
import io
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import action_studio_server as server
import studio_transition_fit_read_cache as provider
from verified_read_cache import EvidenceChangedError


def handler(path, host='127.0.0.1:8768'):
    h = server.Handler.__new__(server.Handler)
    h.path = path; h.headers = {'Host': host}
    h.server = SimpleNamespace(allowed_hosts={'127.0.0.1:8768', 'localhost:8768'})
    h.responses = []; h.statuses = []; h.output_headers = {}; h.wfile = io.BytesIO()
    h.respond = lambda code, value: h.responses.append((code, value))
    h.send_response = lambda code: h.statuses.append(code)
    h.send_header = lambda name, value: h.output_headers.update({name: value})
    h.end_headers = lambda: None
    return h


def test_review_calls_adapter_and_preserves_typed_negative_result(monkeypatch):
    calls = []; value = {'status': 'complete', 'quality_approved': False,
                        'checks': {'native_contact_audit': False}, 'original_selected': True}
    def cached(job): calls.append(job); return value
    monkeypatch.setattr(provider, 'manifest', cached)
    h = handler('/api/native-transition-fit-review?id=job'); h.do_GET()
    assert h.responses == [(200, value)] and calls == ['job']
    assert h.responses[0][1]['quality_approved'] is False


@pytest.mark.parametrize('host', ['other.example:8768', 'localhost:9999', None])
def test_review_retains_loopback_host_gate_before_adapter(monkeypatch, host):
    def forbidden(_): raise AssertionError('Host rejection called the verifier')
    monkeypatch.setattr(provider, 'manifest', forbidden)
    h = handler('/api/native-transition-fit-review?id=job', host); h.do_GET()
    assert h.responses == [(403, {'error': 'Loopback host required'})]


@pytest.mark.parametrize('query', ['', '?extra=x', '?id=', '?id=job&id=other',
    '?id=job&extra=', '?id=job&id=', '?id=job&extra=x'])
def test_exact_review_selection_rejects_empty_duplicate_and_extra_fields(monkeypatch, query):
    def forbidden(_): raise AssertionError('Malformed selection called the verifier')
    monkeypatch.setattr(provider, 'manifest', forbidden)
    h = handler('/api/native-transition-fit-review' + query); h.do_GET()
    assert h.responses[0][0] == 400
    assert h.responses[0][1]['error'] == 'Exact bridge correction selection required'


@pytest.mark.parametrize('failure,code', [(EvidenceChangedError('changed'), 409),
    (ValueError('invalid'), 400), (TypeError('invalid'), 400),
    (KeyError('missing'), 400), (OSError('missing'), 400)])
def test_review_errors_return_typed_json_without_an_approval(monkeypatch, failure, code):
    def rejected(_): raise failure
    monkeypatch.setattr(provider, 'manifest', rejected)
    h = handler('/api/native-transition-fit-review?id=job'); h.do_GET()
    assert h.responses == [(code, {'error': str(failure)})]


def test_bridge_download_dispatches_to_cached_resolver(monkeypatch, tmp_path):
    artifact = tmp_path / 'actor.glb'; artifact.write_bytes(b'fixture-only bytes')
    calls = []
    def cached(relative): calls.append(relative); return artifact
    monkeypatch.setattr(provider, 'served_file', cached)
    path = '/files/native-transition-fit-jobs/job/candidate/actors/0.glb'
    h = handler(path); h.do_GET()
    assert calls == ['native-transition-fit-jobs/job/candidate/actors/0.glb']
    assert h.statuses == [200] and h.wfile.getvalue() == artifact.read_bytes()
    assert h.output_headers['Cache-Control'] == 'no-store'
    assert h.output_headers['X-Content-Type-Options'] == 'nosniff'
    assert h.output_headers['Content-Length'] == str(artifact.stat().st_size)


@pytest.mark.parametrize('failure,code', [(EvidenceChangedError('changed'), 409),
    (ValueError('unpublished'), 400), (OSError('missing'), 400)])
def test_bridge_download_failures_never_stream_payload(monkeypatch, failure, code):
    def rejected(_): raise failure
    monkeypatch.setattr(provider, 'served_file', rejected)
    h = handler('/files/native-transition-fit-jobs/job/candidate/actors/0.glb'); h.do_GET()
    assert h.responses == [(code, {'error': str(failure)})]
    assert not h.statuses and h.wfile.getvalue() == b''


def test_non_bridge_file_serving_remains_unchanged(monkeypatch, tmp_path):
    asset = tmp_path / 'ordinary.txt'; asset.write_bytes(b'ordinary existing file')
    monkeypatch.setattr(server, 'allowed_file', lambda _: asset)
    h = handler('/ordinary.txt'); h.do_GET()
    assert h.statuses == [200] and h.wfile.getvalue() == asset.read_bytes()
    assert h.output_headers['Content-Type'] == 'text/plain'


def test_missing_non_bridge_file_still_returns_404(monkeypatch):
    monkeypatch.setattr(server, 'allowed_file', lambda _: None)
    h = handler('/missing.txt'); h.do_GET()
    assert h.responses == [(404, {'error': 'File not found'})]
