# UI acceptance — actual human-like validation

Use Playwright Chromium plus screenshots and trace captures; test *rendered experience*, not merely presence of a button. The UI Tester must be a distinct BAND seat.

## Journeys
- First visit, scenario selection, consent and fallback when camera/mic blocked
- Watch stand-in performs; captions synchronized; distinguish LIVE from MOCK
- Tap Take My Seat; speak or type; ensure counterpart responds only to user turn
- Receive clear feedback with transcript evidence and hidden need revealed at appropriate point
- Mirror Moment shows model/user turns; Retry from Pivot preserves prior turns and branches subsequent state
- Refresh/resume, disconnect/reconnect, 409/429, slow avatar render, budget exhausted, vendor key absent
- Delete uploaded photo/voice and session; no deleted media accessible after operation

## Viewports and interactions
Desktop 1440x900, tablet 768x1024, mobile 390x844; keyboard-only navigation, focus order, labels, reduced-motion, high zoom; test microphone denial on Chromium and manual smoke on Firefox if available.

## Artifacts
Save `playwright-report/`, screenshots and trace zip to an artifact store and only small sanitized summary/links into Git. No real faces/voices in CI. A screenshot must be produced by a real browser and inspected, not generated from a design prompt. Use `data-testid` stable selectors plus visible text assertions; include a human-readable defect list with expected vs actual.

## Approval
UI Tester cannot mark visually accepted from DOM assertions alone. Confirm screenshots and interaction recordings, no clipped text, no infinite spinners, usable errors. A complete UI journey is required before a stage tag.
