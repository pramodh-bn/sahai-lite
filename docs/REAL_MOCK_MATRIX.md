# Real / mock matrix

What is genuinely implemented in the application versus what is a deterministic
fixture. The demo path is offline by default and makes no live claim.

| Feature | Real | Mock |
|---|---|---|
| Persona compiler | Strict `sah.persona.v1` validation, canonical hash seal, typed `P-xx` rejections and versioned instruction hash | Persona content in tests is synthetic fixture data |
| Turns | Server-authoritative `sah.turn.v1` sequencing, idempotent replay, single-flight conflict handling and strict alternation | Counterpart text is a deterministic generator, not a language model |
| Consent | Six separate `sah.consent.v1` scopes, typed gates and immediate withdrawal effects | Consent decisions are driven by the operator or the test client |
| Vendor | Config-driven adapter, exactly-once create/delete, retained-handle persistence and restart recovery | Napster companion vendor is a loopback fake server in tests; no real call is made |
| Deletion | Redacted `sah.cleanup.v1` receipt, local data removal and idempotent retries | Vendor teardown is verified against the fake server ledger |
| UI | Responsive desktop/mobile layout, keyboard-only operation, slow-network honesty and cleanup status | Avatar media is never connected in the offline demo; mic permission is denied by design |
| Evidence | Append-only `sah.evidence.v1` log with stable prefixes, per-turn hashes and attempt-bound quotes | Evidence content is produced by the deterministic rehearsal, not real conversations |
| Fidelity | Deterministic `sah.fidelity.v1` report with terminal disclosure, authority and safety gates | The rubric is a fixed offline scoring matrix, not a learned judge |
