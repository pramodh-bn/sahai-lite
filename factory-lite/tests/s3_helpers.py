"""Stage 3 black-box test helpers and fake vendor harness.

This module provides test infrastructure for Stage 3 Napster embodied integration:
- FakeNapsterServer: Local HTTP mock server simulating Napster Companion agent connections.
- Observable ledger: tracks connection creation and deletion lifecycle.
- EvidenceSchemaValidator: Validates Stage 3 evidence records and rejects synthetic/leaked data.
- Helper functions to invoke the Stage 3 rehearsal Napster session endpoints.
"""
import http.server
import json
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from s2_helpers import AppProcess, app_base_url, health_url

REPO_ROOT = Path(__file__).resolve().parents[2]

# Prohibited placeholder patterns in evidence per Requirement 8
PLACEHOLDER_PATTERNS = [
    re.compile(r'(?i)(?:^|[^a-zA-Z0-9_])(todo|tbd|fixme|lorem\s+ipsum|placeholder|fixture|dummy|mock_id|sample_id)(?:$|[^a-zA-Z0-9_])'),
    re.compile(r'(?i)(?:^|[^a-zA-Z0-9_])xxx+(?:$|[^a-zA-Z0-9_])'),
]

# Sensitive credential patterns to ensure no leakage
SECRET_SCAN_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{12,}'),
    re.compile(r'(?i)bearer\s+[A-Za-z0-9_\-\.]+'),
    re.compile(r'eyJ[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{15,}'),
]


class FakeNapsterHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b''
        parsed_body = {}
        try:
            if body_bytes:
                parsed_body = json.loads(body_bytes.decode('utf-8'))
        except Exception:
            parsed_body = {'raw': body_bytes.decode('utf-8', errors='replace')}

        req_record = {
            'method': 'POST',
            'path': self.path,
            'headers': dict(self.headers),
            'body': parsed_body,
            'timestamp': time.time(),
        }
        self.server.request_log.append(req_record)

        # Controlled blocking for concurrent single-flight testing
        if self.server.block_event is not None:
            if self.server.request_arrived_event is not None:
                self.server.request_arrived_event.set()
            self.server.block_event.wait(timeout=5)

        client_id = parsed_body.get('externalClientId', '')

        # Check in-flight duplicate rejection simulation
        if self.server.simulate_inflight_conflict and client_id in self.server.active_clients:
            self.send_response(409)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'conflict', 'message': 'Session connection already in flight'}).encode())
            return

        if client_id:
            self.server.active_clients.add(client_id)

        # Pop status from sequence if available
        status_code = 200
        conn_id = 'conn_' + (client_id or 'default')
        response_payload = {
            'token': 'napster_conn_token_' + str(int(time.time() * 1000)),
            'connection': {'id': conn_id},
        }

        if self.server.response_sequence:
            item = self.server.response_sequence.pop(0)
            if isinstance(item, int):
                status_code = item
            elif isinstance(item, tuple):
                status_code, response_payload = item

        if status_code >= 400:
            if client_id and client_id in self.server.active_clients:
                self.server.active_clients.remove(client_id)
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            err_body = response_payload if isinstance(response_payload, dict) else {'error': f'HTTP {status_code}'}
            self.wfile.write(json.dumps(err_body).encode())
            return

        # Record successful creation in observable ledger
        self.server.ledger['created'].append(conn_id)
        self.server.active_allocations.add(conn_id)

        body_out = json.dumps(response_payload).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body_out)))
        self.end_headers()
        self.wfile.write(body_out)

    def do_DELETE(self):
        req_record = {
            'method': 'DELETE',
            'path': self.path,
            'headers': dict(self.headers),
            'timestamp': time.time(),
        }
        self.server.request_log.append(req_record)

        # Extract connection id from path if present: /public/agents/{agent_id}/connections/{connection_id}
        parts = self.path.strip('/').split('/')
        conn_id = parts[-1] if len(parts) >= 4 else 'unknown'

        self.server.ledger['deleted'].append(conn_id)
        if conn_id in self.server.active_allocations:
            self.server.active_allocations.remove(conn_id)
        elif self.server.active_allocations:
            self.server.active_allocations.pop()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'destroyed', 'connection_id': conn_id}).encode())

    def log_message(self, format, *args):
        pass


class FakeNapsterServer:
    def __init__(self):
        self.httpd = http.server.HTTPServer(('127.0.0.1', 0), FakeNapsterHandler)
        self.httpd.request_log = []
        self.httpd.response_sequence = []
        self.httpd.active_clients = set()
        self.httpd.simulate_inflight_conflict = False
        self.httpd.block_event = None
        self.httpd.request_arrived_event = None
        self.httpd.ledger = {'created': [], 'deleted': []}
        self.httpd.active_allocations = set()
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def port(self):
        return self.httpd.server_address[1]

    @property
    def base_url(self):
        return f'http://127.0.0.1:{self.port}'

    def set_response_sequence(self, sequence):
        self.httpd.response_sequence = list(sequence)

    def set_simulate_inflight_conflict(self, enabled=True):
        self.httpd.simulate_inflight_conflict = enabled

    def set_controlled_blocking(self, block_event, request_arrived_event=None):
        self.httpd.block_event = block_event
        self.httpd.request_arrived_event = request_arrived_event

    def get_requests(self):
        return list(self.httpd.request_log)

    def get_ledger(self):
        return {
            'created': list(self.httpd.ledger['created']),
            'deleted': list(self.httpd.ledger['deleted']),
            'active': list(self.httpd.active_allocations),
        }

    def clear_requests(self):
        self.httpd.request_log.clear()
        self.httpd.active_clients.clear()
        self.httpd.ledger = {'created': [], 'deleted': []}
        self.httpd.active_allocations.clear()
        self.httpd.block_event = None
        self.httpd.request_arrived_event = None

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.httpd.shutdown()
        self.httpd.server_close()


def post_napster_session(session_id, channel_type='webrtc', base_app_url=None, simulate_error=None):
    """Call the app's server-side Napster session creation endpoint."""
    base = base_app_url or app_base_url()
    url = f'{base}/api/rehearsal/sessions/{session_id}/napster-session'
    payload_dict = {'channel_type': channel_type}
    if simulate_error:
        payload_dict['simulate_error'] = simulate_error
    payload = json.dumps(payload_dict).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return resp.status, data
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='replace')
        try:
            data = json.loads(raw)
        except Exception:
            data = {'error': raw, 'status_code': exc.code}
        return exc.code, data


def delete_napster_session(session_id, base_app_url=None):
    """Call the app's server-side Napster session teardown endpoint."""
    base = base_app_url or app_base_url()
    url = f'{base}/api/rehearsal/sessions/{session_id}/napster-session'
    req = urllib.request.Request(url, method='DELETE')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return resp.status, data
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='replace')
        try:
            data = json.loads(raw)
        except Exception:
            data = {'error': raw, 'status_code': exc.code}
        return exc.code, data


def validate_stage3_evidence(evidence):
    """Validate Stage 3 evidence structure strictly per Requirement 8.

    Returns a list of error strings. Empty list indicates completely valid evidence.
    """
    errors = []
    if not isinstance(evidence, dict):
        return ['Evidence must be a dictionary']

    # 1. Non-null UTC ISO timestamps
    start_utc = evidence.get('start_time_utc')
    end_utc = evidence.get('end_time_utc')
    if not start_utc or not isinstance(start_utc, str):
        errors.append('start_time_utc must be a non-null ISO-8601 UTC string')
    if not end_utc or not isinstance(end_utc, str):
        errors.append('end_time_utc must be a non-null ISO-8601 UTC string')

    dt_start, dt_end = None, None
    if start_utc and end_utc:
        try:
            dt_start = datetime.fromisoformat(start_utc.replace('Z', '+00:00'))
            dt_end = datetime.fromisoformat(end_utc.replace('Z', '+00:00'))
            if dt_start.tzinfo is None:
                errors.append('start_time_utc must include UTC timezone offset or Z')
            if dt_end.tzinfo is None:
                errors.append('end_time_utc must include UTC timezone offset or Z')
            if dt_end < dt_start:
                errors.append('end_time_utc must not precede start_time_utc')

            # Check synthetic / epoch timestamps
            if dt_start.year < 2024 or dt_end.year < 2024:
                errors.append('Synthetic historical timestamps prior to 2024 are rejected')

            # Check future timestamp (allow at most 120s clock skew)
            now_utc = datetime.now(timezone.utc)
            if (dt_start - now_utc).total_seconds() > 120 or (dt_end - now_utc).total_seconds() > 120:
                errors.append('Synthetic future timestamps are rejected')
        except Exception as exc:
            errors.append(f'Invalid timestamp formatting: {exc}')

    # 2. Probe correlation hash (64 hex characters)
    corr_hash = evidence.get('probe_correlation_hash')
    if not corr_hash or not isinstance(corr_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', corr_hash):
        errors.append('probe_correlation_hash must be a 64-char lowercase hexadecimal SHA-256 string')

    # 3. Documented HTTP probe
    probe = evidence.get('http_probe')
    if not isinstance(probe, dict):
        errors.append('http_probe must be a dict')
    else:
        for fld in ('host', 'path', 'method', 'status_code'):
            if fld not in probe:
                errors.append(f'http_probe missing required field: {fld}')
        host = str(probe.get('host', ''))
        # Must match official current host, historical live alias, or loopback
        if not (host in ('companion-api.napster.com', 'napster-api.napster.com') or host.startswith('127.0.0.1') or host.startswith('localhost')):
            errors.append(f'Unrecognized http_probe host: {host}; must be companion-api.napster.com or napster-api.napster.com')
        if probe.get('method') not in ('POST', 'GET', 'DELETE'):
            errors.append(f'Unrecognized http_probe method: {probe.get("method")}')

    # 4. Ready proof
    ready_proof = evidence.get('ready_proof')
    if not isinstance(ready_proof, dict):
        errors.append('ready_proof must be a dict')
    else:
        if ready_proof.get('event') != 'onAvatarReady' or ready_proof.get('avatar_ready') is not True:
            errors.append('ready_proof must confirm event=onAvatarReady and avatar_ready=True')
        if ready_proof.get('status') != 'readyVideo':
            errors.append('ready_proof status must be readyVideo')

    # 5. Media proof
    media_proof = evidence.get('media_proof')
    if not isinstance(media_proof, dict):
        errors.append('media_proof must be a dict')
    else:
        for fld in ('video_mounted', 'audio_mounted', 'video_track_live', 'audio_track_live'):
            if media_proof.get(fld) is not True:
                errors.append(f'media_proof requires {fld}=True')

    # 6. Cleanup proof
    cleanup_proof = evidence.get('cleanup_proof')
    if not isinstance(cleanup_proof, dict):
        errors.append('cleanup_proof must be a dict')
    else:
        if cleanup_proof.get('session_destroyed') is not True or cleanup_proof.get('resources_released') is not True:
            errors.append('cleanup_proof requires session_destroyed=True and resources_released=True')

    # 7. Redacted flag must be explicitly True
    if evidence.get('redacted') is not True:
        errors.append('redacted must be explicitly True')

    # 8. Rejection of raw secrets, keys, placeholders, personal content
    json_str = json.dumps(evidence)
    for pat in SECRET_SCAN_PATTERNS:
        if pat.search(json_str):
            errors.append(f'Raw secret/token pattern detected in evidence: {pat.pattern}')

    for pat in PLACEHOLDER_PATTERNS:
        if pat.search(json_str):
            errors.append('Placeholder markers detected in evidence')

    # Check for unredacted raw IDs or personal content indicators
    if 'transcript' in evidence or 'utterance' in evidence or 'user_input' in evidence:
        errors.append('Personal rehearsal transcript or user utterances must not be stored in vendor evidence')

    return errors


def is_stage3_certified(evidence=None, mode='offline'):
    """Return (is_certified: bool, reason: str).

    Offline or mock runs are explicitly insufficient for Stage 3 certification per Requirement 9.
    """
    if mode != 'live':
        return False, 'Mock/offline runs are explicitly insufficient for Stage 3 certification per Requirement 9.'
    if not evidence:
        return False, 'Missing live evidence payload.'
    val_errors = validate_stage3_evidence(evidence)
    if val_errors:
        return False, f'Evidence validation failed: {val_errors}'
    return True, 'Stage 3 verified and certified.'
