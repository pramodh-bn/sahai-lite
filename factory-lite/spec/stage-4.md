# Stage 4: Synthetic body double and product submission

Stage 4 turns the certified Stage 2 rehearsal engine and Stage 3 avatar transport into the intended product: a bounded synthetic body double and a separately configured counterpart conduct a rehearsal, then hand their transcript and decision evidence into practice, feedback, and retry.

The contest build is synthetic-only. It must not require or accept a real person's photo, video, voice sample, biometric template, or public-figure likeness. A stock or generated companion and a standard synthetic voice are sufficient. Behaviour is defined by an approved, versioned persona profile—not inferred from appearance or voice.

The normative design inputs are:

- `factory-lite/docs/body-double-persona-and-consent.md`
- `factory-lite/docs/body-double-orchestration.md`
- `factory-lite/docs/napster-digital-twin-research.md`

## Product requirements

1. **Approved persona profile.** Implement a strict, versioned synthetic-persona schema and compiler covering identity disclosure, personality, communication style, scenario knowledge, negotiation policy, hidden-need reveal rules, delegated authority, prohibited actions, escalation, and retention. Reject unknown fields, biometric data, real-person impersonation, prompt injection, and unapproved or hash-mismatched profiles.
2. **Two distinct roles.** The body double and counterpart have separate profiles, visible knowledge, hidden state, goals, and policies. Neither may see the other's hidden state. The browser receives only the current projection.
3. **Server-authoritative orchestration.** Sah owns turn order, state transitions, policy decisions, hidden-state projection, transcript evidence, and retry. Napster is an optional renderer; it must not be the source of scenario truth. The deterministic offline path is required and sufficient for all acceptance tests other than an explicitly owner-authorized live gate.
4. **Bounded authority.** The synthetic agent may model and rehearse language but cannot bind, sign, pay, contact third parties, join meetings, impersonate a human, or claim the user is present. Disclosure, refusal, and escalation are deterministic gates rather than model discretion.
5. **Evidence fidelity.** Record append-only turn evidence with role, approved profile/instruction hashes, visible-fact projection, policy decision, and quoted user evidence. Do not store audio, biometric data, credentials, raw vendor identifiers, or hidden facts in browser-visible or shared evidence. Feedback may quote only utterances that actually occurred.
6. **Consent and deletion.** Avatar, microphone, and optional transcript retention are separately consented before initialization. Text-only practice remains available when avatar or microphone consent is declined. Withdrawal and End-and-delete stop activity, perform exactly-once cleanup, and leave verifiable deletion evidence without sensitive content.
7. **Responsive embodied UI.** The avatar is contained in a capped responsive region that fits desktop and 375x667 mobile viewports without browser zoom or horizontal scrolling. The full desktop/mobile journey is scenario -> body-double demonstration -> handoff -> practice -> evidence feedback -> retry from pivot. Keyboard operation, microphone denial, slow-network behaviour, honest live/offline labelling, and cleanup are required.
8. **Fidelity and adversarial gates.** Execute the disclosure, authority, safety, hidden-need, prompt-injection, consent, deletion, privacy, fallback, and retry cases defined by the persona design. A disclosure, authority, or safety failure is terminal and cannot be averaged away.

## Architecture decision

Use the recommended external Sah orchestration architecture. Napster conversation mode may be evaluated only as a labelled optional mode. If exact rendered speech is needed later, Puppeteer mode requires separate owner approval and verified account support; it is not required for the offline Stage 4 contract. No Digital Twin creation or biometric upload is part of Stage 4.

## Submission requirements

After the body-double contract is implemented and green, run the cumulative suite from a clean checkout and capture actual demo evidence. Produce a substantive README, a <=3 minute demo script/video if tools are available, a 100-500 word write-up, a real/mock matrix, and a judging-rubric self-check. The owner performs any final submission.

Verifier must translate all product and submission requirements into executable acceptance tests before implementation. Tests must include a red run on the exact base and preserve all certified Stage 1-3 guarantees. Lead reviews the exact immutable test head before Builder receives an implementation assignment. No certification is allowed for missing evidence, mock evidence presented as live, or packaging that omits the persona/orchestration product.
