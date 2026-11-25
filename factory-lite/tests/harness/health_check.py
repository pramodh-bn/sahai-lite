"""Independent black-box health/version harness for Sah v3 Lite Stage 1.

Contract (factory-lite/spec/stage-1.md): "independent harness exits nonzero
for broken service and zero for healthy implementation".

  - GET <url> must return HTTP 200 with a JSON body:
        {"status": "ok", "version": "<build sha>"}
  - If --expected-sha is given, "version" must equal it exactly.
  - Any connection failure, timeout, non-200 status, malformed JSON, wrong
    "status" value, or SHA mismatch is treated as a failing (broken or
    unavailable) service.

This script is test tooling independent of the application: it has no
third-party dependencies (stdlib only) and makes no network calls beyond the
single URL it is given.

Exit codes:
  0 - service is healthy and conforms to the contract.
  1 - service is broken, unavailable, or non-conforming.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def check(url, expected_sha, timeout):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            status = resp.status
            body = resp.read()
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        print(f"FAIL: service unavailable: {exc}", file=sys.stderr)
        return 1

    if status != 200:
        print(f"FAIL: unexpected HTTP status {status}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        print(f"FAIL: non-JSON response: {exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict) or payload.get("status") != "ok":
        print(f"FAIL: status field is {payload.get('status') if isinstance(payload, dict) else payload!r}, expected 'ok'", file=sys.stderr)
        return 1

    version = payload.get("version")
    if not version:
        print("FAIL: version field missing or empty", file=sys.stderr)
        return 1

    if expected_sha and version != expected_sha:
        print(f"FAIL: version {version!r} != expected build SHA {expected_sha!r}", file=sys.stderr)
        return 1

    print(f"PASS: {url} healthy, version={version}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Health endpoint URL, e.g. http://127.0.0.1:8000/health")
    parser.add_argument("--expected-sha", default=None, help="Build SHA the version field must match")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args(argv)
    return check(args.url, args.expected_sha, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
