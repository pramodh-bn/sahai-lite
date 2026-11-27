# Write-up

Rehearsing a hard conversation is useful, but most tools quietly blur the line
between practice and the real thing: they impersonate real people, claim live
presence, or keep data the user did not agree to keep. Sahai Lite takes the
opposite stance. It is a small, offline rehearsal product built around a
synthetic body double and counterpart, with explicit disclosure, bounded
authority and a clean data lifecycle.

The approach is deliberately boring and testable. Personas are strict
`sah.persona.v1` documents that must pass a hash seal and a rule ladder before
they compile. Turns are server-authoritative: the server owns sequence numbers,
rejects out-of-order or conflicting recalls, and refuses to commit a duplicate
when two requests overlap. Restricted requests such as signing, paying,
committing, contacting a third party, joining a real meeting, cloning a voice or
extracting hidden state are decided by policy before anything happens and are
recorded with a typed rule id. A deterministic counterpart makes the rehearsal
repeatable, and an immutable pivot means a retry really starts over.

Privacy is treated as a product feature rather than a policy page. Consent is
six separate scopes, all denied by default, and each gated operation fails with
a typed error until its scope is granted. Withdrawal is immediate: the avatar
tears down its vendor handle, the saved transcript disappears, and ending the
rehearsal scope ends the session. Deletion returns a redacted receipt bound only
by a session hash, and the offline path never touches a live vendor or reads a
credential.

Results are encouraging within that narrow scope. The full offline suite covers
startup, the rehearsal engine, the vendor adapter contract, core intelligence,
consent and lifecycle, and responsive browser journeys. The remaining
limitations are equally clear: the counterpart is deterministic rather than a
language model, the avatar path is unproven live, and the whole system is
uncertified until independent verification. That is the point: a small product
that tells the truth about what it is.
