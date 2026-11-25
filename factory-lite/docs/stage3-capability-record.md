# Stage 3 Napster capability/unknowns/account-capability record

Documentation-only record, researched before any Stage 3 implementation,
per `factory-lite/spec/stage-3.md` ("Verify current vendor docs and actual
account capability before coding"). **No vendor API calls, no credentials,
no cost, no signup were used to produce this record** -- every claim below
is either a direct citation of a page Napster publishes, or explicitly
marked as unverified pending a live account check. This record itself does
not certify Stage 3; see `factory-lite/tests/CONTRACT.md` ("mock/static
insufficient for certification").

## Capabilities (documented by Napster, as of this research)

- **Companion / avatar**: the "Companion" resource defines "the visual
  identity and personality of your agent -- how it looks and behaves."
  Napster provides "a catalog of pre-built companions with ready-made
  avatars, voices, and personalities" (v1), and a v2 path that generates an
  avatar from a still image (`pictureUrl`) or from a reference video (an
  MP4 with audio, >=90 seconds long) -- a reference video "still produces
  the best lip sync and expressions." v2 "must be enabled for your
  organization first"; otherwise creation fails with `CompanionV2NotEnabled`.
  (developers.napster.com/docs/building-your-omniagent/companion;
  developers.napster.com/docs/whats-new/platform-api/july-13-2026)
- **Pre-recorded video/audio**: `POST /public/companions/{companionId}/recordings`
  renders "a lip-synced, voiced video" of the avatar speaking given text and
  a `voiceId` (example: `"provider": "openAi", "voiceId": "alloy"`), async.
  A later update adds rendering from supplied audio instead of text
  (`audioUrl` up to 50 MB, or a direct file upload up to 2 MB), plus
  `companion.created/updated/deleted` webhooks for companions a project
  owns (not the Napster stock catalog).
  (developers.napster.com/docs/whats-new/platform-api/july-13-2026 and
  .../september-29-2026)
- **Kiosk/Station channel**: a physical "Napster Station" device "pairs a
  small screen showing the agent's avatar" with a large screen running a
  custom experience -- requires owning that hardware.
  (developers.napster.com/docs/whats-new/platform-api/july-13-2026)
- **Voice**: v2 "digital twins can take voice from the video" ("the voice
  is now cloned from the video's own audio track"); a separate `voiceUrl`
  is also supported. `initialSpeech` is "an instruction the agent follows
  in its own voice, not a verbatim line to read." WebSocket `modality`
  accepts `audio` (default) or `text`; text mode has "no audio streaming."
  Voice stage runs through Azure OpenAI/OpenAI by default, or through
  HUMAIN ("an Arabic-first provider" for speech recognition, language
  model, and voice) if access is requested and granted.
  (developers.napster.com/docs/whats-new/platform-api/june-26-2026,
  .../september-29-2026, .../october-30-2026)
- **Handoff -- documented only for SIP telephony**: "Human handoff on SIP
  telephony can now send callers to different extensions" (up to 10
  routes, `transferExtension` required when enabled); the agent "confirms
  the caller wants transfer," "tells them it's transferring them," and
  asks them to wait; a `session.humanHandoff.started` webhook fires
  (reason, extension, conversation so far); the caller's phone number
  becomes an `externalClientId` so a later call resumes the same agent
  conversation.
  (developers.napster.com/docs/whats-new/platform-api/september-29-2026
  and .../october-30-2026)
- **Auth**: API key in the `X-Api-Key` header, scoped to an organization
  and a project; key "architectures" are "Realtime, Cascade, or Other";
  sign up at napster.com/developer, or via the Azure Portal if billing
  through Azure. (developers.napster.com/docs/introduction/authentication)
- **Account-capability gates are explicit, named errors** -- not something
  to assume: `CompanionV2NotEnabled`, `ProviderNotEnabled` (API key's
  provider not enabled for your org, 400), `RecordingsApiNotEnabled`,
  `DigitalTwinConsentRequired` (the latter two now 403, previously 400),
  `InactiveSubscription` (403 when credits run out -- the key itself
  "stays valid," but starting sessions or creating/changing companions,
  digital twins, recordings, or SIP connections is blocked; reading data
  and managing agents/tools/knowledge/FAQs keeps working).
  (developers.napster.com/docs/introduction/authentication and
  .../introduction/limits; .../whats-new/platform-api/october-30-2026)
- **Limits** (documented numbers): connection-opening endpoints
  (`POST /public/agents/{id}/connections`, `POST /public/connections`,
  `POST /public/ws-connections`, `DELETE /public/connections/{id}`) are
  rate-limited to 1 request/second per API key; concurrency is 5
  simultaneous sessions per transport (WebRTC, WebSocket, VoIP, SIP -- 20
  total per organization), exceeding it returns `409
  ConcurrentSessionLimitReached`; 100 agents/org; 1 FAQ collection/agent
  (30 files/knowledge collection, 50 Q&A pairs/FAQ collection); at
  telephony capacity "the system plays a pre-recorded audio message" then
  drops the call. (developers.napster.com/docs/introduction/limits)

## Unknowns (not stated on the pages read)

- **No documented meeting-join, meeting-relay, or meeting-control
  capability of any kind.** The words "Zoom," "Teams," "Meet," and
  "meeting" do not appear on any Companion, Authentication, Limits, or
  2026 changelog page read for this record. Handoff is documented only as
  a SIP-telephony call transfer between extensions -- not as joining or
  controlling a third-party video meeting.
- No standalone text-to-speech endpoint is documented separately from the
  companion-recording and realtime-session voice features above.
- No numeric pricing, credit cost, or per-minute/per-session rate is
  documented on these pages; a `cost` field is mentioned elsewhere as "the
  billed cost of the session in USD" with no rate given.
- No free or trial tier is documented on these pages (the words "free"
  and "trial" do not appear).
- No WebRTC signaling protocol detail beyond the endpoint list and
  concurrency limit above is documented on the pages read (the Companion
  page links to a WebRTC channel-deployment page that was not read for
  this record).
- Exactly how account credits are consumed (e.g. per minute of avatar or
  voice use) is not described -- only that running out blocks session
  starts and resource mutation.

## Account capability -- UNVERIFIED, requires a live check

Account capability status: **unverified**. Whether **this project's own
Napster account/organization** actually has:
an API key, which architecture it uses (Realtime/Cascade/Other), whether
`CompanionV2` is enabled for it, whether it has non-zero credits, and
which providers (e.g. HUMAIN) are enabled for it -- **is not determined by
this record and cannot be determined from documentation alone.** This
requires the authorized live probe gated in
`factory-lite/tests/test_s3_live_napster.py`, which has not been run (see
that file and CONTRACT.md). Stage 3 is **not certified** until that probe
runs successfully with owner-authorized credentials and produces redacted
evidence.

## Unrelated prior-engagement context (not this project, not an official
source -- cited separately so it is never mistaken for documentation)

A different, unrelated project involving the same vendor (recalled from
this agent's own memory of past sessions, not from any page fetched for
this record) reported, informally: a hosted "Napster Omniagent" voice +
video-face service billed at $0.0583/minute requiring a server-side
`X-Api-Key`; a browser SDK that opens an external WebRTC signaling
connection to `wss://avatar-signaling.napster.ai` only after an explicit
user click to opt in to a live face; and a caution that Napster's API can
reject requests sent with a default/unmodified HTTP client User-Agent
(e.g. Python's default), so a non-default User-Agent should be set on any
future live request. These are **not treated as capabilities of this
record** -- they are unverified secondhand recollection about a different
engagement, included only so Builder/Lead are aware of them as things to
re-verify independently (e.g. against the WebRTC channel-deployment page)
rather than being surprised by them later.

## Evidence sources (official documentation fetched for this record)

- https://developers.napster.com/docs/whats-new
- https://developers.napster.com/docs/whats-new/platform-api/september-29-2026
- https://developers.napster.com/docs/whats-new/platform-api/october-30-2026
- https://developers.napster.com/docs/whats-new/platform-api/july-13-2026
- https://developers.napster.com/docs/whats-new/platform-api/june-26-2026
- https://developers.napster.com/docs/whats-new/platform-api/may-7-2026
- https://developers.napster.com/docs/introduction/authentication
- https://developers.napster.com/docs/introduction/limits
- https://developers.napster.com/docs/building-your-omniagent/companion
- https://docs.napster.ai/docs was attempted and failed ("too many
  redirects"); not used as a source.

No live API calls, logins, or signups were made to produce this record.
No credentials were used. No cost was incurred.
