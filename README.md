# Sahai Lite — synthetic body-double negotiation rehearsal

Sahai Lite is a small, deliberately bounded rehearsal product: a person practises
a negotiation against a **body double** stand-in and a **counterpart** stand-in,
then reviews evidence-based feedback and retries from a fixed pivot. Everything
runs **offline**: the counterpart is a deterministic synthetic stand-in, with no
model, no vendor call and no paid API in the default path.

## What it is

- **Synthetic, not real.** Both seats are explicitly synthetic. The body double
  and the counterpart are compiled from a strict `sah.persona.v1` profile,
  hash-sealed, and limited to A2 authority. They cannot sign, pay, commit,
  contact third parties, join real meetings or impersonate a real person.
- **Honest disclosure.** The first counterpart turn and every disclosure
  question state that the seat is an AI stand-in.
- **Consent first.** Every session starts with six separately recorded consent
  scopes (`rehearsal`, `avatar`, `mic`, `transcript_save`, `research`,
  `subject_consent`), all denied by default. A scope that is not granted blocks
  its operation with a typed `403`, and withdrawal takes effect immediately.
- **Bounded claims.** The avatar path is opt-in and honestly labelled: without
  configured credentials it shows an offline fallback and never claims a live
  connection. The default demo makes no real or live claim.

## Real vs mock

The application is real code; the counterpart and the vendor are mocks. The
practice conversation, consent gates, evidence log, pivot/retry and deletion are
real application behaviour. The Napster companion session is exercised through
configuration (`NAPSTER_BASE_URL`, `NAPSTER_API_KEY`, `NAPSTER_AGENT_ID`) and a
loopback fake vendor in tests; the app never imports the fixture. See
`docs/REAL_MOCK_MATRIX.md` for the per-feature split.

## Privacy and retention

The default session stores nothing durable: transcripts live in process memory,
saved transcripts are opt-in (`transcript_save`) and retained for 24 hours, and
research export is de-identified and aggregate only. `End session and delete`
calls `DELETE /api/rehearsal/sessions/{id}`, which returns a redacted
`sah.cleanup.v1` receipt bound only by a session hash. No token, API key or user
utterance is written to logs. No credentials are required for the offline demo.

## Run

```bash
python app/main.py
```

Then open <http://localhost:8000/>. The health endpoint is
<http://localhost:8000/health>. Python 3.12 with Flask is required.

## Test

```bash
py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v
```

The suite covers startup, the rehearsal engine, the Napster adapter contract,
Stage 4A core intelligence (persona compiler, projections, authoritative turns,
evidence, fidelity), Stage 4B consent/lifecycle/deletion, and Stage 4C
responsive browser journeys and packaging. Browser tests need Playwright and
Chromium.

## Evidence

Every turn is recorded in an append-only `sah.evidence.v1` log with profile,
instruction and projection hashes; the fidelity report (`sah.fidelity.v1`) keeps
disclosure, authority and safety as terminal, non-compensable gates. Stage 4A,
4B and 4C remain **uncertified** until independent verification passes.
