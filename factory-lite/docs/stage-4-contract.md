# Stage 4 Acceptance Contract & Technical Specification

## 1. Overview

This document translates `factory-lite/spec/stage-4.md` and `factory-lite/STATUS.md` into the executable black-box acceptance contract for Stage 4 (Product and Submission) in Sahai Lite.

Stage 4 extends the offline rehearsal state machine and embodied Napster avatar into a complete, accessible, ethical, and submission-ready body-double product:
1. **User Journeys**: Desktop and mobile responsive Playwright journeys (landing scenario -> stand-in demo -> handoff (`take-my-seat`) -> practice -> evidence feedback -> retry from pivot).
2. **Accessibility**: Complete keyboard-only navigation (`Tab`, `Enter`, `Space`) and graceful microphone denial fallback (`[data-testid="mic-denied-fallback"]`).
3. **Resilience**: Slow-network flight safety and race-free state transitions.
4. **Lifecycle & Teardown**: Exactly-once session cleanup and full session deletion endpoint (`DELETE /api/rehearsal/sessions/{id}`).
5. **Ethics & Consent**: Affirmative consent for avatar likeness and voice synthesis (`[data-testid="avatar-consent-checkbox"]`) and prominent synthetic-identity disclosure (`[data-testid="synthetic-disclosure"]`).
6. **Hard Prohibitions**: Zero real meeting participation (no SIP, telephony, Zoom/Teams/Meet bot joins), zero real-person voice cloning, zero credential/token leakage in application logs or payloads.
7. **Submission Deliverables**: Root `README.md`, demo script bounded to `<= 180 seconds` (3 minutes), hackathon writeup bounded to `<= 500 words`, comprehensive Real/Mock matrix, and judging-rubric self-check.

---

## 2. Fixed Conventions for Builder

To enable independent Builder implementation against this contract, the following conventions, endpoints, and DOM test IDs are established:

### 2.1 DOM Test IDs & UI Controls
| Test ID / Selector | Expected Element & Behavior |
| --- | --- |
| `[data-testid="start-demo"]` | Button on landing section to transition to `demo` state |
| `[data-testid="take-my-seat"]` | Button on demo section to hand off to user and transition to `practice` state |
| `[data-testid="practice-input"]` | Text input for user utterance in practice state |
| `[data-testid="send-utterance"]` | Button to submit practice utterance |
| `[data-testid="mic-denied-fallback"]` | Visual indicator element informing user that text practice is active due to mic denial/unavailability |
| `[data-testid="feedback-score"]` | Element displaying scored feedback |
| `[data-testid="retry-button"]` | Button on feedback section to restore practice pivot for a new attempt |
| `[data-testid="avatar-consent-checkbox"]` | Checkbox for affirmative consent to avatar likeness and voice synthesis |
| `[data-testid="napster-connect"]` | Button to connect avatar; disabled until `avatar-consent-checkbox` is checked |
| `[data-testid="napster-disconnect"]` | Button to disconnect live avatar |
| `[data-testid="synthetic-disclosure"]` | Prominently visible element affirming that counterpart is a synthetic AI rehearsal stand-in |

### 2.2 HTTP API Endpoints
| Method | Path | Expected Status & Schema |
| --- | --- | --- |
| `POST` | `/api/rehearsal/sessions` | HTTP 201 JSON `{"session_id": str, "flow_state": "created", ...}` |
| `POST` | `/api/rehearsal/sessions/{id}/advance` | HTTP 200 JSON advancing scenario state |
| `POST` | `/api/rehearsal/sessions/{id}/practice` | HTTP 200 JSON returning counterpart response and updating attempt |
| `POST` | `/api/rehearsal/sessions/{id}/feedback` | HTTP 200 JSON returning scoring rubric |
| `POST` | `/api/rehearsal/sessions/{id}/retry` | HTTP 200 JSON restoring practice pivot |
| `DELETE` | `/api/rehearsal/sessions/{id}/napster-session` | HTTP 200 JSON destroying avatar connection |
| `DELETE` | `/api/rehearsal/sessions/{id}` | HTTP 200 JSON `{"status": "deleted", "session_id": str}` deleting entire session |

### 2.3 Mobile & Responsive Conventions
- HTML head must include: `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Interactive touch targets (`start-demo`, `take-my-seat`, `send-utterance`, `retry-button`) must have minimum height of 36px (target 40-44px).

### 2.4 Submission Deliverables Requirements
- `README.md`: Repo root, containing non-empty sections for Overview, Architecture, Run, and Safety.
- Demo Script (`docs/demo-script.md` or `README.md`): Duration budget strictly `<= 180 seconds` (3 minutes).
- Hackathon Writeup (`docs/writeup.md` or `README.md`): Word count strictly between 100 and 500 words.
- Real/Mock Matrix (`docs/real-mock-matrix.md` or `README.md`): Must document Mock vs Live behavior across Stages 1, 2, 3, and 4.
- Judging Rubric Self-Check (`docs/judging-rubric.md` or `README.md`): Must address Innovation, Technical Implementation, UX, Embodied Experience, and Safety/Ethics.

---

## 3. Pre-Implementation Red-Run Verification

Before any Builder implementation commences, this acceptance contract is executed against exact base SHA `79747d9d0f092e7304315a5e32a10c837ed0ff9a`.
The test run proves red status due to unimplemented Stage 4 features, and the output is recorded in `factory-lite/tests/evidence/base-79747d9-red-run.txt`.
