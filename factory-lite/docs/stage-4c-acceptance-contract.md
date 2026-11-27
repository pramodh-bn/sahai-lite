# Stage 4C acceptance contract (responsive UI and packaging)

**Task:** `LITE-S4C-VERIFY-TESTS-01`
**Base:** `e697d35f44293acc176533f9acd18bae01a3c586` (`dev-v3`, 4B merged)
**Author:** Independent Verifier (tests and docs only)
**Status:** deliberate-red contract for Lead review before any Builder 4C assignment.
**Scope:** responsive UI and packaging only — Playwright desktop/mobile
journeys, keyboard-only operation, microphone denial, slow-network honesty,
session cleanup observed at the application boundary, README, demo script,
real/mock matrix, write-up and judging-rubric self-check. No Playwright test
added here touches a live vendor, reads credentials or uses media.

This document fixes the browser hooks and artifact paths asserted by
`factory-lite/tests/test_s4c_*.py`. It adds no application code and edits no
pre-existing test. `test_s4c_contract_selfcheck.py` only rejects skips,
placeholders and an undersized suite; every product claim is proved in a real
browser against the running application.

## 1. Preservation and run command

All 186 certified Stage 1-4B tests and their helpers are unchanged. The
cumulative command is unchanged:

```
py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v
```

The 4C suite must be red on the base (no responsive layout, no cleanup UI, no
packaging artifacts) and green only after Builder implements this contract.

## 2. Journeys, viewports and responsive rules

Two Playwright viewports:

| Name | Size |
|---|---|
| desktop | 1280 x 800 |
| mobile | 375 x 667 |

Both run the same journey: landing -> start demo -> body-double demonstration
-> take my seat -> practice -> one or more utterances -> empty submit ->
evidence feedback -> retry from pivot -> practice (attempt 2) -> end and delete.

Rules that hold at both viewports and at every journey step:

1. The document declares `<meta name="viewport">` with `width=device-width`.
2. No horizontal scrolling: `document.documentElement.scrollWidth` and
   `document.body.scrollWidth` are each `<= window.innerWidth + 1`.
3. The avatar panel and slot are contained: their bounding boxes lie inside
   the viewport horizontally, and the avatar slot height is at most 45% of the
   viewport height (`[data-testid="napster-avatar"]`).
4. Every control used by the journey is visible and inside the viewport at the
   step that needs it: `start-demo`, `take-my-seat`, `practice-input`,
   `send-utterance`, `retry-button`, `end-and-delete`.
5. `data-testid="mode-label"` states the offline/deterministic mode; no element
   claims a live connection while the avatar status is disconnected/fallback.

## 3. New browser hooks

| Hook | Requirement |
|---|---|
| `[data-testid="thinking-indicator"]` | Present in the DOM; visible only while a practice or feedback request is in flight; hidden otherwise. |
| `[data-testid="recording-indicator"]` | Present in the DOM; hidden unless microphone capture is actually active. |
| `[data-testid="end-and-delete"]` | Visible in practice, feedback and after retry; triggers session deletion. |
| `[data-testid="cleanup-status"]` | Visible only after cleanup completes; text states that the session/data was deleted (case-insensitive "delet"). |

Existing Stage 2/3 hooks keep their meaning and must not be removed:
`start-demo`, `take-my-seat`, `practice-input`, `send-utterance`,
`feedback-score`, `retry-button`, `mic-denied-fallback`, `mode-label`,
`napster-status`, `napster-avatar`.

## 4. Keyboard-only operation

The desktop journey is completed with the keyboard alone: `Tab` moves focus,
`Enter` activates the focused control, and `Shift+Tab` is never required to
escape a trap. While a control has keyboard focus it shows a visible focus
indicator: computed `outline-style != "none"` with `outline-width >= 1px`, or a
non-`none` `box-shadow`. Step status text is exposed in the existing
`role="status"` region and updates after each activation.

## 5. Microphone denial

With microphone permission denied (browser context created with no
permissions), the practice screen:

- shows `[data-testid="mic-denied-fallback"]`;
- keeps `[data-testid="recording-indicator"]` hidden;
- keeps text practice fully usable through feedback and retry.

## 6. Slow-network honesty

With the practice request delayed by 800 ms at the browser boundary:

- `[data-testid="thinking-indicator"]` becomes visible while the request is in
  flight and hidden after it settles;
- the send control is disabled while the request is in flight;
- exactly one user turn is committed (the application session transcript has
  one user utterance), so a slow response cannot double-commit.

## 7. Cleanup observability

Activating `[data-testid="end-and-delete"]` must:

1. issue `DELETE /api/rehearsal/sessions/{id}` from the browser;
2. receive a 200/204 (never 5xx);
3. show `[data-testid="cleanup-status"]` with deletion language;
4. leave the session unreadable: `GET /api/rehearsal/sessions/{id}` is 404;
5. remain idempotent: a second activation or retry does not produce a 5xx.

## 8. Packaging artifacts

Exactly these repository paths are required:

| Path | Requirement |
|---|---|
| `README.md` | At least 1500 characters; a `## Run` heading; mentions body double, consent, synthetic, real, mock, offline, evidence and privacy/retention. |
| `docs/DEMO.md` | Numbered demo with at least 6 steps covering scenario, demonstration, practice, feedback, retry and cleanup; states a total duration of at most 3 minutes (or <= 180 seconds). |
| `docs/REAL_MOCK_MATRIX.md` | A Markdown table whose header names Feature, Real and Mock, with at least 8 rows covering persona, turns, consent, vendor, deletion, UI, evidence and fidelity. |
| `docs/RUBRIC_SELFCHECK.md` | At least 8 scored/verdict rows covering fidelity, disclosure, authority, safety, hidden need, evidence, responsive/UX and privacy/consent. |
| `docs/WRITEUP.md` | 100-500 words describing the problem, approach, results and limitations. |

The checks are semantic minima, not exact prose: wording, ordering and extra
sections are free, and no specific sentence is required.

## 9. Safety of the test suite

Every browser test talks only to the localhost application URL from
`app/RUN.md`; the application runs offline with no vendor credentials. No live
or paid call, media capture, microphone grant, credential or deployment is
involved. Slow-network tests delay responses locally in the browser; cleanup
tests assert the existing application-boundary DELETE.

## 10. Deliberate-red evidence

All gate runs were executed by the independent Verifier on
`e697d35f44293acc176533f9acd18bae01a3c586` with a clean tree. The 4C modules
are red because the responsive layout, cleanup UI hooks and packaging
artifacts do not exist yet; no application code was touched.

| Gate | Command | Result | Exit |
|---|---|---|---|
| Exact-base preflight (no 4C files) | `py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v` | `Ran 186 tests`, `OK (skipped=1)`, 1500.7 s | 0 |
| 4C focused suite | `py -3.12 -m unittest discover -s factory-lite/tests -p "test_s4c_*.py" -v` | `Ran 14 tests`, `FAILED (failures=12)`, 0 errors, 21.7 s | 1 |
| Cumulative | `py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v` | `Ran 200 tests`, `FAILED (failures=12, skipped=1)`, 0 errors, 1520.7 s | 1 |

The cumulative failure set is identical to the focused set (12 unique, all in
`test_s4c_req1..req4`); the 186 certified Stage 1-4B tests stay green with
their single pre-existing skip, and the two 4C self-checks pass. Evidence:

- `factory-lite/tests/evidence/lite-s4c-verify-tests-01-base-e697d35-preflight.txt`
- `factory-lite/tests/evidence/lite-s4c-verify-tests-01-focused-red.txt`
- `factory-lite/tests/evidence/lite-s4c-verify-tests-01-focused-red-inventory.txt`
- `factory-lite/tests/evidence/lite-s4c-verify-tests-01-cumulative-red.txt`

Syntax/import gate: `py -3.12 -m py_compile` over `s4c_helpers.py` and the five
`test_s4c_*.py` modules exits 0.

Environment note: Playwright's Python package and Chromium must be installed
(`pip install playwright && playwright install chromium`), and the suite must
run from a normal `C:\...` path with a `python` that has the app dependencies
(Flask) on PATH. `/health` must report the worktree HEAD.
