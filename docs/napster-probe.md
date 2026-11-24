# API Scout — verify these capabilities first

1. List exact current Napster endpoints and SDK version from official docs.
2. Create a mock/staging agent without a real photo or cloned voice. Verify connection creation, lifecycle and cleanup. Record time-to-first-frame, rate limits, error shapes.
3. Verify what inputs can *control* utterances in a **live WebRTC** avatar. Distinguish prompt guidance from guaranteed spoken-text rendering.
4. Verify whether the documented video-recording text-render API is asynchronous and can be used in a prerecorded stand-in demo. Do not treat it as evidence for interactive response.
5. Verify creation/permission for personalized avatar and voice, required source assets, processing delay and license/consent constraints.
6. Verify whether a session may be transferred from autonomous model to real human and back, or whether two sessions must be used.
7. Verify transcript, turn, interruption, disconnect, cleanup, quota, 409 and 429 behavior. Never fan out test sessions against rate limits.
8. Attach sanitized facts to `artifacts/stages/stage-04/capability-matrix.md`: doc URL, exact SDK/API version, test date, observed result and live versus simulated status. Mark missing keys `BLOCKED`, not PASS.

Known reference: Napster FAQ says connection creation endpoints share a limit of **1 request per second per API key** as of 2026-11-24. Confirm live account constraints and any further restrictions before load testing. Reference https://developers.napster.com/docs/faq and https://developers.napster.com/docs/video-recordings.
