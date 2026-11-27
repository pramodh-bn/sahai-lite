# Demo script (under 3 minutes)

**Total demo time: 2 minutes (120 seconds).** Offline only: no live vendor, no
credentials, no microphone grant.

1. **Scenario** — open <http://localhost:8000/>. The mode label states the
   offline, deterministic synthetic mode. Point out that no avatar connects on
   page load and that the mode label makes no live claim.
2. **Demonstration** — press **Start demo**. A synthetic body double opens the
   demonstration and the take-my-seat handoff appears. The counterpart holds its
   constraints back until probed.
3. **Take my seat** — press **Take my seat**. The practice screen opens with the
   microphone fallback notice, because no microphone permission is granted, and
   the text input remains fully usable.
4. **Practice** — type a question about the budget and press **Send**. The
   thinking indicator appears while the turn is in flight; the counterpart
   reveals the hidden need only after a qualifying probe.
5. **Evidence feedback** — send one more line, then send an empty message. The
   evidence score and per-utterance notes appear, and every turn is recorded in
   the append-only evidence log.
6. **Retry from the pivot** — press **Retry**. Attempt 2 starts from the same
   immutable pivot, the transcript resets and discovery must happen again.
7. **Cleanup** — press **End session and delete data**. The browser issues
   `DELETE /api/rehearsal/sessions/{id}`, the cleanup status reports that the
   session and data were deleted, and a reload of that session now returns 404.
8. **Transparency** — mention the disclosure: every counterpart turn is stamped
   synthetic, authority stays A2, and sign/pay/commit requests are refused with a
   typed rule id rather than performed.

Keep the walkthrough tight; the numbered steps above are the whole demo.
