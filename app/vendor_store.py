"""Persistent retained-vendor-handle store for Stage 4B lifecycle.

Only the minimum needed for teardown is written: connection id, base URL and
agent id. No token, API key or user content is ever persisted.

``SAH_STATE_DIR`` (optional) names the directory; when unset the store is
process-memory only.
"""
import json
import os
import tempfile
import threading

_lock = threading.Lock()
_handles = {}
_ALLOWED_FIELDS = ("connection_id", "base_url", "agent_id")


def _state_dir():
    return os.environ.get("SAH_STATE_DIR", "").strip()


def _path(session_id):
    base = _state_dir()
    if not base:
        return None
    return os.path.join(base, "vendor-%s.json" % session_id)


def _sanitise(handle):
    return {key: handle[key] for key in _ALLOWED_FIELDS if key in handle}


def save(session_id, handle):
    stored = _sanitise(handle)
    with _lock:
        _handles[session_id] = stored
        path = _path(session_id)
        if path is None:
            return
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".vendor-", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(stored, fh, sort_keys=True)
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def load(session_id):
    with _lock:
        if session_id in _handles:
            return dict(_handles[session_id])
        path = _path(session_id)
        if path is None or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or not data.get("connection_id"):
            return None
        stored = _sanitise(data)
        _handles[session_id] = stored
        return dict(stored)


def clear(session_id):
    with _lock:
        _handles.pop(session_id, None)
        path = _path(session_id)
        if path is not None:
            try:
                os.unlink(path)
            except OSError:
                pass
