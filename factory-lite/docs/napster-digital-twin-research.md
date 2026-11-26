# Napster Digital Twin & Omniagent — Vendor Research (Stage 4 body-double input)

**Task:** `LITE-NAPSTER-RESEARCH-01`
**Base:** `79747d9d0f092e7304315a5e32a10c837ed0ff9a` (`dev-v3`)
**Owner of this document:** Napster Digital Twin / Omniagent specialist (documentation only)
**All vendor facts retrieved:** **2026-11-26** from `developers.napster.com`. Pricing, limits, SDK versions and org-gated features are temporally unstable; every such item is dated in place.
**Status of evidence:** documentation review only. No account mutation, no media upload, no companion/agent/key creation, no live or paid call, no credential read. Nothing here is a certification of live behaviour.

Legend: **[Doc]** = stated in official Napster documentation; **[Inferred]** = reasoned from documented behaviour, not stated by Napster; **[Unverified]** = needs confirmation from Napster or the account owner.

---

## 1. What the product actually is (and is not)

The surface at `developers.napster.com` is the **Omniagent / Companion** product — real-time video avatars with voice, tools, knowledge and memory. It is **not** the legacy music-metadata API at `developer.napster.com` that `factory-lite/docs/napster-feasibility.md` originally studied. That older document is retained as history but does not describe this product.

Two resources are distinct and must not be conflated **[Doc]**:

| Resource | Answers | Holds |
| --- | --- | --- |
| **Companion** (`/public/companions`, `/public/digital-twins`) | *Who is this?* | Face, name, persona `description` (becomes the system prompt), avatar generation, cloned voice |
| **Omniagent** (`/public/agents`) | *What can it do, and how does it run?* | Companion link, voice, language, tools, knowledge, FAQs, provider settings, mode, channels |

A companion is reusable across several agents; the generated avatar is created once on the companion. Digital twins are companions of `personaType=digitalTwin` created through a separate, consent-gated endpoint.

---

## 2. Account prerequisites

| # | Prerequisite | Detail | Source |
| --- | --- | --- | --- |
| P1 | Napster account + organization + project | Sign up at `napster.com/developer`; dashboard at `napster-api.napster.com/admin`. API keys are **scoped to a project**; agents belong to the organization. | [Overview](https://developers.napster.com/docs), [Create a key](https://developers.napster.com/docs/guides/create-api-key) |
| P2 | Credits or Azure Marketplace billing | New accounts start with **$6 free credits (~100 minutes)** as of 2026-11-26. Without credits, session creation and all companion/twin/recording writes return `403 InactiveSubscription`; reads and agent/tool/knowledge management keep working. | [Limits](https://developers.napster.com/docs/introduction/limits) |
| P3 | **Organization admin** for Digital Twin consent | Consent is organization-wide and one-time, granted in the dashboard (`Companions → New Digital Twin → Consent Required → Agree & Enable Digital Twins`). Until then `POST /public/digital-twins` returns `403 DigitalTwinConsentRequired`. Members cannot grant it. | [Enable Digital Twins](https://developers.napster.com/docs/guides/digital-twin-consent) |
| P4 | **v2 avatar model enablement** (org-level, support ticket) | v2 must be enabled per organization; otherwise `400 CompanionV2NotEnabled`. Request via `help.napster.com` with the organization ID (dashboard → Settings). v2 carries **no extra charge** (2026-11-26). | [Avatar Models](https://developers.napster.com/docs/building-your-omniagent/avatar-models) |
| P5 | An API key on the right **architecture** | `Realtime` (Azure OpenAI default, or OpenAI), `Cascade` (separate ASR/LLM/TTS), or `Other` (Microsoft Foundry). **Puppeteer mode requires a Cascade key.** | [Create a key](https://developers.napster.com/docs/guides/create-api-key), [Puppeteer mode](https://developers.napster.com/docs/guides/puppeteer-mode) |
| P6 | Public HTTPS media URLs | Both `voiceUrl`/`pictureUrl`/`videoUrl` and knowledge-file `url` are fetched **by Napster from a publicly reachable HTTPS URL**; there is no documented direct binary upload for twin media. | [Digital Twins](https://developers.napster.com/docs/building-your-omniagent/digital-twins), [Knowledge files](https://developers.napster.com/docs/building-your-omniagent/knowledge/files) |
| P7 | Optional org-gated providers | HUMAIN (Cascade stages, Arabic-first) and Microsoft Foundry are **not enabled by default**; both need a support request. | [Create a key](https://developers.napster.com/docs/guides/create-api-key) |

**Consequence for Sah:** consent + v2 enablement are the two long-lead, human-only items. Neither can be performed by an agent and neither is automatable through the API.

---

## 3. Exact setup sequence (dashboard and API)

### 3.1 Dashboard / human steps (one-time)

1. Sign in to `napster-api.napster.com/admin`, select **organization** and **project** in the top navigation.
2. Settings → copy the **organization ID** (needed for any support request).
3. As an **admin**: `Companions → New Digital Twin` → accept the **Consent Required** dialog → **Agree & Enable Digital Twins**. The flow does not have to be completed; agreeing is enough. (P3)
4. If v2 quality is wanted: open a support request at `help.napster.com` quoting the organization ID and asking for **v2 avatar model** enablement. Wait for confirmation. (P4)
5. `Keys → + Create API key`: name, project (pre-filled), architecture + provider(s), optional "use my own credentials". The **Pricing panel shows the per-minute rate** for the selection. Copy the key once; store it server-side in `.env` as `NAPSTER_API_KEY`. (P5)

### 3.2 API steps (idempotent order)

1. **(Optional) Browse stock companions** — `GET /public/companions/napster-stock?pageSize=10`. Catalog companions need no generation wait.
2. **Create knowledge / FAQ / tools** (independent of the twin, can run in parallel):
   - `POST /public/knowledge-bases` `{name, provider:"azureOpenAI"}` → then `POST /public/knowledge-bases/{kbId}/files` `{url}` per document.
   - `POST /public/faqs` `{name}` → `POST /public/faqs/{faqId}/items` `{question, answer}`.
   - `POST /public/functions` `{data:{name,description,parameters}, url, flow:"explicit"|"implicit"}`.
3. **Create the digital twin** — `POST /public/digital-twins` (fields in §4). Returns a **companion `id`** immediately; the avatar generates in the background.
4. **Wait for readiness** — poll `GET /public/companions/{id}` until `status == "readyToUse"`, or subscribe to companion webhooks. Do not attach before that.
5. **Create the agent** — `POST /public/agents` with `companionId`, `name`, `providerSettings`, and optionally `voiceId` (**omit `voiceId` for a twin**), `language`, `functions`, `knowledgeBaseId`, `faqCollections`, `mode`, `tags`, `disableIdleTimeout`, `useWebSearch`.
6. **Optional channel config** — `PUT /public/agents/{agentId}/channels/webrtc` for `videoPolicy`, `useGreenVideo`, `initialSpeech`, per-channel `providerSettings`/`functions`/knowledge overrides.
7. **Backend token endpoint** — server-side `POST /public/agents/{agentId}/connections` `{channelType:"webrtc", externalClientId?, externalClientProfile?, initialSpeech?}` → return **only** `token` (and store `connection.id`). Never call this from the browser.
8. **Browser** — Web SDK `init(getToken, config)`; `getToken` is invoked by the SDK **after microphone permission settles**; act only in `onAvatarReady(true)`.
9. **Teardown** — `instance.destroy()` (SDK: closes WebRTC, removes widget, releases mic) **and** server-side `DELETE /public/connections/{connectionId}` (authoritative session end; shows as `closed`, `closeReason:"connection_aborted"`).

---

## 4. Required fields

### 4.1 `POST /public/digital-twins` **[Doc]**

| Field | Req. | Notes |
| --- | --- | --- |
| `firstName`, `lastName` | Yes | Real-person identity; all four identity fields are **required for twins** (optional for custom companions). |
| `description` | Yes | Role, personality, communication style; foundation of the system prompt. |
| `gender` | Yes | `male` \| `female` \| `nonBinary`. |
| `ethnicity` | Yes | Value from `GET /public/companions/ethnicities` (lowercase; some contain spaces). Bad value → `400 CompanionCreationFailed`. |
| `externalClientId` | Yes | Your stable ID for the **person**; correlation key for sessions/analytics. |
| `voiceUrl` | v1 required; v2 optional | Public HTTPS recording. **mp3, wav, m4a, flac, ogg, webm, mp4; ≤10 MB; 60 s minimum, 300 s maximum.** |
| `pictureUrl` | v1 required; v2 alternative | Public HTTPS still. Best: 16:9, facing camera, waist-up, well-lit. |
| `videoUrl` | v2 preferred | **MP4 (H.264/HEVC) with audio, ≥90 s**, publicly reachable; first frame must show exactly one face. |
| `version` | No | `"v1"` (default) or `"v2"`; v2 needs org enablement. |
| `tags` | No | String→string labels. |

Documented v2 video error codes: `VideoUnsupportedFormat`, `VideoMissingAudio`, `VideoTooShort`, `ImageValidationNoFaceDetected`, `ImageValidationMultipleFaceDetected`, `VideoValidationFailed`. Custom companions additionally reject `ImageValidationPublicFigureDetected`; **twins skip the public-figure check**.

v2 generation **can take up to several hours** (2026-11-26). v1 is fast.

### 4.2 `POST /public/agents` **[Doc]**

| Field | Req. | Notes |
| --- | --- | --- |
| `companionId` | Yes | Twin or companion ID. |
| `name` | Yes | Label only. |
| `providerSettings` | Yes | Object; `{}` accepted — API fills defaults. |
| `voiceId` | Conditional | **Required for catalog/custom companions; omit for a twin** (cloned voice). Twin not yet `readyToUse` → treated as a normal companion → `VoiceIdRequired` / `ClonedVoiceNotAvailable`. |
| `language` | No | ISO code. Set → agent **never switches language**; omitted → English but may follow the user. |
| `functions`, `knowledgeBaseId`, `faqCollections` | No | `faqCollections` accepts **at most one** ID. |
| `mode` | No | `conversation` (default) \| `puppeteer`. |
| `tags`, `disableIdleTimeout`, `useWebSearch` | No | Web search now **off by default**. |

Updatable later with `PATCH /public/agents/{agentId}` (partial update; only supplied fields change). `PATCH` is also the documented way to flip `mode`, except for agents that already have SIP/VoIP channels.

### 4.3 `POST /public/agents/{agentId}/connections` **[Doc]**

Request: `channelType` (required; `webrtc`/`websocket`/`sip`/`voip`), `externalClientId` (optional; enables memory), `externalClientProfile` (optional free-form user context), `initialSpeech` (optional per-session opening instruction), `tags`, per-session `mode` on the per-session endpoints.
Response: `{ "token": "...", "connection": { "id": "..." } }` — **token is short-lived (seconds)** and single-use; it is the only thing the browser needs.

---

## 5. Capability / limitation matrix

| Capability | Status | Detail (2026-11-26) |
| --- | --- | --- |
| Real-time 2D video avatar with lip sync | **[Doc]** | v1 and v2; v2 adds natural expressions and better facial hair. |
| Voice cloning from reference audio | **[Doc]** | Digital twin only; 60–300 s sample. No public "voice clone any voice" API beyond the twin endpoint. |
| Custom persona / system prompt | **[Doc]** | Companion `description` is the base; agent `providerSettings.instructions` overrides it for one agent. |
| Knowledge grounding | **[Doc]** | One collection per session; **30 files max**; `.doc`10 MB, `.docx`/`.pdf` 50 MB, `.txt`/`.md`/`.png`/`.jpeg` 10 MB. Answers only from retrieved content when the question is document-scoped. |
| FAQs | **[Doc]** | 50 pairs/collection, **1 collection per agent**. |
| Tools | **[Doc]** | Two flows: `implicit` (call delivered to the browser/client) and `explicit` (call forwarded to your HTTP or WebSocket endpoint). Unlimited tools per agent. |
| MCP servers / connectors | **[Doc]** | Supported on Realtime keys; **not supported on Cascade** (`400 UnsupportedProvider`). OpenAI-provider keys are required for MCP **connectors**. |
| Cross-session memory | **[Doc]** | Enabled only by passing `externalClientId`; scoped to **companion + externalClientId**; regex `^[A-Za-z0-9_-]{1,32}$`. |
| Text-only chat | **[Doc]** | WebSocket channel with `modality:"text"` — not WebRTC. |
| Conversation mode | **[Doc]** | Listens, answers, can call tools, can be interrupted. |
| Puppeteer mode | **[Doc]** | Speaks only client-sent `talk` lines; **no ASR, no LLM, no barge-in**; Cascade key only; no SIP/VoIP. |
| Transcript | **[Doc]** | Conversation-mode sessions store full transcript (`GET /public/sessions/{id}`). **Puppeteer sessions store no transcript.** |
| Session cost reporting | **[Doc]** | `cost` populated on close. |
| Backend session end | **[Doc]** | `DELETE /public/connections/{connectionId}` → `connection_aborted`; WebRTC/WebSocket/Kiosk only; SIP/VoIP returns `ConnectionAbortNotSupported`. |
| Meeting participation (Zoom/Teams/Meet bot) | **[Doc: absent]** | No join/relay capability is documented anywhere in this product. The SIP/VoIP channels are telephony, not meeting attendance. Treat "attend a real meeting" as unsupported. |
| Real-person voice cloning without consent | **[Doc: gated]** | Consent is a one-time **organization-admin** switch, not a per-person attestation. There is no documented per-subject consent artifact. |
| Retention duration for transcripts/memory | **[Unverified]** | Not documented in the pages reviewed. Only explicit deletion is documented. |
| Concurrent v2 generations / job queue | **[Unverified]** | Only "up to several hours" is documented. |

---

## 6. Conversation vs puppeteer, Cascade vs Realtime

### 6.1 Mode **[Doc]**

| | `conversation` | `puppeteer` |
| --- | --- | --- |
| Who decides lines | The model | Your client, via `talk` |
| ASR / LLM | Yes | **None** |
| Interruption | User can barge in | Only your `cancel` / `stopAvatarTalking()` |
| Key requirement | Realtime **or** Cascade | **Cascade only** (`400 UnsupportedSessionMode` otherwise) |
| Phone channels | Yes | **No** (`400 TelephonyChannelNotAllowed`) |
| Transcript stored | Yes | **No** |
| Mic permission | Required | **Still required** — the SDK asks before connecting; if the visitor blocks it, **the session does not start** |
| Idle behaviour | 3 min silence closes (agent-level) | 3 min without a `talk` line closes; SDK inactivity timer does **not** count puppet lines |
| Talk events | — | `talk_state_changed`: `preparing`→`started`→`ended`/`canceled`; `sentence_index` always `null` |

Puppeteer is the only documented way to make an avatar say **exactly** a scripted line. Conversation mode always allows model paraphrase, so puppeteer is the correct primitive for a "body double reads the approved line" product.

### 6.2 Architecture **[Doc]**

| | Realtime (Azure OpenAI / OpenAI) | Cascade (ASR + LLM + TTS) |
| --- | --- | --- |
| Model shape | One speech-to-speech model | Three separately chosen providers |
| Tools / knowledge / FAQs / twins | Yes | Yes |
| MCP | Yes (Realtime) | **No** |
| `temperature`, `noiseReduction` | Applied | **Ignored** |
| Mid-session `set_settings` | Full | Only `instructions` and tools |
| `speech_started` / interruption signal | Real-time | Arrives **after** transcription; cannot be used to detect interruption |
| Puppeteer | **No** | **Yes** |
| Managed price (2026-11-26) | $0.0583/min managed, $0.01/min BYO credentials | Shown in the dashboard Pricing panel; not stated in prose → **[Unverified]** exact figure |

**Decision consequence:** one key cannot be both Realtime-with-MCP and puppeteer-capable. A single **Cascade** key covers conversation *and* puppeteer but gives up MCP and live turn-detection settings. Two keys in two projects is the alternative, at the cost of duplicating agent config.

---

## 7. WebRTC / Web SDK setup facts

- **SDK:** npm `@touchcastllc/napster-companion-api` (MIT). Standalone build `lib/index.standalone.js` exposes `window.napsterCompanionApiSDK`. Docs describe the **2.0** line (Web SDK 2.0 released 2026-10-30); Sah pins **2.0.0** with SHA-256 `c1b2db52…` — consistent with the documented 2.x API used here **[Doc + repo provenance]**.
- `init(getToken, config)` — `getToken` **must be a function**, not a token string (`TOKEN_ERROR`). The SDK calls it **after the microphone settles**, because tokens expire within seconds. **[Doc]**
- `init` resolves when the widget mounts, **before** the session is live. Commands sent before `onAvatarReady(true)` are dropped. **[Doc]**
- Mount into your own element: `layout:{type:"inline", mountContainer:"#avatar-container"}`. Views: `round`, `rectangle`, `silhouette`. **[Doc]**
- Readiness: `onAvatarReady(true)` fires once per session when the conversation is live; **`readyVideo`** from `onSessionStatusChange` is the signal that video specifically is up (relevant under `videoPolicy:"deferred"`). **[Doc]**
- `videoPolicy`: `required` (default; audio+video together) or `deferred` (audio first, video later; **`ready` fires twice**). Set on the WebRTC channel config; per-session endpoints accept it directly. Latch readiness or your start logic runs twice. **[Doc]**
- Green screen: `useGreenVideo:true` on the channel **and** `style.view:"silhouette"` in the SDK; mismatched halves break the visuals. **[Doc]**
- Teardown: `instance.destroy()` closes WebRTC, removes the widget, releases mic/screen/camera. Without it, tracks stay open. **[Doc]**
- Launcher mode: `button.enabled` returns a **controller** (`start`/`end`/`getInstance`/`destroy`) instead of an instance; `ALREADY_INITIALIZED` if `init` is called twice. **[Doc]**
- Inactivity: SDK default **60 s + 30 s "Still there?" countdown**, separate from the agent's **3-minute** server idle timeout. **[Doc]**
- Signalling: per the repo's provenance note, the SDK opens `wss://avatar-signaling.napster.ai` after opt-in; this endpoint is **not** named in the docs pages reviewed → **[Unverified]**, but it is the only external connection Sah permits.

---

## 8. Cost and quota facts (2026-11-26, documented)

**Pricing**
- Realtime, Napster-managed infrastructure: **$0.0583/min**.
- Realtime, own Azure OpenAI credentials: **$0.01/min** ($0.60/h).
- FAQ prose rounds managed to "approximately $0.058/min ($3.50/h)".
- Billing is **only while the agent is running**; per-session `cost` (USD) available on close.
- $6 free credits ≈ 100 minutes of conversation.
- v2 avatars: no extra charge. Digital twin generation itself: no separate price documented → **[Unverified]** whether generation minutes are billable.
- Cascade per-minute rate is only shown in the dashboard Pricing panel → **[Unverified]**.

**Quotas**
| Resource | Limit | Error |
| --- | --- | --- |
| Connection endpoints (POST agent connections, POST /public/connections, POST /public/ws-connections, DELETE /public/connections/{id}) | **1 request/second per API key**, shared | `429 RequestRateLimitExceeded` + `Retry-After` |
| Concurrent sessions | **5 per transport** (WebRTC/WebSocket/VoIP/SIP), 20 total per org | `409 ConcurrentSessionLimitReached` |
| Agents per organization | **100** | `409 AgentLimitExceeded` |
| Knowledge files per collection | **30** | `400 KnowledgeBaseFileLimitReached` |
| FAQ pairs per collection | **50** | `400 FaqLimitExceeded` |
| FAQ collections per agent | **1** | `400` validation |
| Twin voice sample | 60–300 s, ≤10 MB | creation `400` |
| Twin reference video | MP4, audio, ≥90 s, one face in first frame | `Video*` codes |
| Session idle | 3 min silence (agent) | `closeReason:"idle_timeout"` |

Idle sessions **count** toward concurrency until closed. Credits run out mid-session → session closes with `closeReason:"no_credits_left"`.

---

## 9. Privacy, consent and lifecycle risks

1. **Consent is organizational, not personal.** One admin checkbox enables twins for every project. There is no documented per-subject consent record, revocation, or proof-of-consent field. For a body-double product this is the single largest governance gap and must be covered by Sah's own consent artifact. **[Doc + gap]**
2. **Deleting a session does not reliably delete memory.** Napster states that only the memory from the user's **last** session is removed; earlier facts can persist and be recalled for the same `externalClientId`. **[Doc]** → Sah must not rely on `DELETE /public/sessions/{id}` as an erasure mechanism.
3. **Memory key is a person identifier.** `externalClientId` is a stable person key scoped to companion+client. Reusing one ID across rehearsals would accumulate personal rehearsal data. **[Doc + Inferred]**
4. **Transcripts are stored server-side in conversation mode** with role/text/timestamps, plus tool-call arguments and outputs (`GET /public/sessions/{id}/items`). Puppeteer sessions store **no transcript** but still store session timing and cost. **[Doc]**
5. **Biometric-adjacent media leaves Sah.** Twin creation requires a **publicly reachable** voice sample and/or reference video URL. A public URL is effectively an unauthenticated bearer link for biometric media. **[Doc]** → use short-lived signed URLs, delete the object immediately after creation, and never commit media.
6. **Napster-side data access.** With customer-hosted LLM, inference stays in the customer cloud, but Napster still stores agent configuration/prompts and performs video rendering. With Napster-hosted, Napster manages model infrastructure. Published posture: SOC 2 Type II (NDA), GDPR/CCPA, AES + TLS 1.2+, annual pen tests, tenant isolation, **no training on customer data**. **[Doc]**
7. **Retention windows are undocumented.** No transcript/memory/config retention period was found. **[Unverified]** — blocks any "delete within N days" promise.
8. **Synthetic-identity disclosure already exists but must not be relied on alone.** The Web SDK disclaimer is on by default with "This is an AI avatar. Check important info."; it is configurable/disableable. **[Doc]** Sah should set explicit twin-disclosure copy rather than depend on the default.
9. **Recording is a separate, billable write path.** Pre-recorded videos (`/public/companions/{id}/recordings`) are persistent artifacts and are blocked when credits are exhausted. If Sah never records, keep it that way. **[Doc]**
10. **Rate-limit coupling of create and delete.** Because `POST …/connections` and `DELETE /public/connections/{id}` share a 1 rps budget, an aggressive cleanup retry can itself trigger `429`. **[Doc + Inferred]**

---

## 10. Architecture compatibility with certified Stage 3

Stage 3 is certified at `82e9406` (tag `lite-stage-3-passed`). The adapter in `app/napster.py` and the vendored 2.0.0 SDK were checked against current docs.

| Stage 3 assumption | Current documentation | Verdict |
| --- | --- | --- |
| Create: `POST {base}/public/agents/{agentId}/connections`, `X-Api-Key`, body `{channelType:"webrtc", externalClientId}` | Same endpoint, header and body documented | **Compatible** |
| Response `{token, connection:{id}}` | Same shape documented | **Compatible** |
| Cleanup: `DELETE {base}/public/connections/{connectionId}` | Documented; 200, ends session as `connection_aborted` | **Compatible** (the older `HANDOFF.md` line showing `DELETE /public/agents/{agentId}/connections/{connectionId}` is **stale/wrong** — `factory-lite/HANDOFF.md:36`. `app/napster.py:102-114` already uses the correct route.) |
| Retry only on `409`/`429`, one retry, cooldown, single-flight | Both statuses documented with the exact meanings Sah assumes (`409` concurrency, `429` rate limit + `Retry-After`) | **Compatible**; docs add: prefer `Retry-After` over a hardcoded delay (Sah uses a fixed 0.5 s retry + 10 s cooldown — acceptable but not `Retry-After`-aware) |
| Browser consumes a short-lived token; key never in browser | Documented explicitly ("Never call the Napster API from the browser") | **Compatible** |
| Certification requires `readyVideo` **and** `onAvatarReady(true)` **and** mounted live `<video>`/`<audio>` | Docs confirm both signals and that `onAvatarReady` fires once when live; `readyVideo` comes from `onSessionStatusChange` | **Compatible** |
| `providerSettings.instructions` sent **on the connection body** (per `HANDOFF.md:34`) | Current docs list `instructions` as **agent-level** `providerSettings`; connection-level opening is `initialSpeech` | **Contract drift — do not rely on it.** Set instructions on the agent (`POST`/`PATCH /public/agents`) and use `initialSpeech` per session. **[Unverified]** whether an unknown connection field is ignored or rejected. |
| Token minted after mic permission | Documented: `getToken` runs once the mic settles; blocked mic → no `getToken` | **Compatible** with Sah's on-demand `getAvatarToken` |
| Denied mic → text practice still works | Docs: SDK waits / shows "Check again"; session doesn't start | **Compatible only if Sah never treats avatar failure as fatal** — Stage 3 already falls back to text |
| 30 s live probe budget | Agent idle timeout is 3 min; SDK inactivity 60 s+30 s | **Compatible** |
| One browser-owned session, no preallocation | Docs confirm `getToken`-driven creation per session | **Compatible** |

**Unsupported by the vendor (must stay out of scope):** meeting join/attendance/relay, SIP-based meeting dial-in as a body double, real-person voice cloning outside the consent-gated twin flow, and MCP tools on a Cascade key.

---

## 11. Recommended Sah integration (Stage 4 body-double)

1. **Two personas, two modes, one key where possible.**
   - *Stand-in demo / scripted body double* → **puppeteer** on a **Cascade** key. Sah's orchestrator decides every line; the twin speaks it verbatim, which is exactly the "approved wording" guarantee Stage 4 needs.
   - *Practice where the twin must listen and respond* → **conversation** mode. If a single Cascade key must serve both, accept: no MCP, `temperature`/`noiseReduction` ignored, no reliable barge-in detection. If MCP is required, use a second Realtime key/project.
2. **Never let the model speak unapproved commitments.** For puppeteer, keep `talk` text server-authored, queue on `talk_state_changed: ended|canceled`, and treat `cancel` as the only stop.
3. **Keep the Stage 3 adapter as the only credential boundary.** Server mints tokens; browser receives `token` only. Extend `app/napster.py` with (a) `initialSpeech` pass-through, (b) agent-level `instructions` management, (c) `Retry-After`-aware backoff — all as *proposals*, not changes in this task.
4. **Do not enable memory for rehearsals.** Omit `externalClientId` on connection creation, or use a per-session random 32-char `[A-Za-z0-9_-]` pseudonym that is never reused. Session deletion does not guarantee memory erasure.
5. **Consent before any twin exists.** Owner/admin completes org consent; Sah captures its own per-participant consent + synthetic-identity disclosure, shows it before the avatar mounts, and records only the consent decision (not biometric data).
6. **Media hygiene.** Signed short-lived URLs for `voiceUrl`/`videoUrl`; delete the source object after `readyToUse`; store only the returned `companionId` (pseudonymised in logs). No biometric media in the repo or evidence.
7. **Readiness gate.** Poll `status == "readyToUse"` (or webhook) before agent creation; surface `VoiceIdRequired`/`ClonedVoiceNotAvailable` as "twin still generating", not as a generic failure.
8. **Cleanup contract.** Always `instance.destroy()` **and** `DELETE /public/connections/{id}`; keep the 10 s cooldown; never retry `DELETE` inside the same second as the `POST` because the 1 rps budget is shared.
9. **Evidence.** Record `onAvatarReady(true)` **and** `readyVideo` from `onSessionStatusChange`, plus mounted `<video>`/`<audio>` track state — matching the Stage 3 evidence schema. A 200 token is never evidence.
10. **Disclosure and non-participation.** Keep the twin visibly labelled synthetic; no meeting joins, no telephony body-double, no recording unless separately consented and budgeted.

---

## 12. Uncertainties requiring owner or provider confirmation

| # | Question | Why it matters | Owner or Napster |
| --- | --- | --- | --- |
| U1 | Is Digital Twin **consent** sufficient for a synthetic body double of a *third party* (the person being doubled), or does Napster require a separate attestation? | Cannot ship a twin without a defensible consent story | **Both** |
| U2 | Has v2 been enabled for the Sah organization, and is the org ID recorded? | Blocks v2 twins; affects hours-long generation | **Owner** |
| U3 | Exact **Cascade** per-minute price and whether twin *generation* (vs conversation) is billable | Budget approval and demo cost ceiling | **Owner/Napster** |
| U4 | Transcript/memory **retention periods** and whether memory can be purged per `externalClientId` | GDPR/CCPA erasure commitments | **Napster** |
| U5 | Are unknown connection-body fields (e.g. `providerSettings`) ignored or rejected? | Determines whether the stale Stage 3 handoff field is harmless | **Napster** |
| U6 | Does a twin `readyToUse` gate apply to **agent creation** only, or also to first connection? | Retry/UX design | **Napster** |
| U7 | Does the Web SDK require camera permission in addition to microphone for `rectangle`/`silhouette` views? | Denied-permission fallback design | **Napster** |
| U8 | Signalling host `wss://avatar-signaling.napster.ai` — still current for SDK 2.0.0? | Network allow-list and Stage 3 evidence | **Napster** |
| U9 | Concurrency: does a failed/abandoned POST count toward the 5-per-transport limit before `connection_timeout`? | Burst rehearsal design | **Napster** |
| U10 | Can a **puppeteer** session be certified with the mic permission granted but no audio track? (Docs say mic permission is required even though nothing listens.) | Headless live evidence feasibility | **Napster** |

---

## 13. Sources (all retrieved 2026-11-26)

| Topic | URL |
| --- | --- |
| Product overview, capabilities, compliance | https://developers.napster.com/docs |
| Quickstart / build order | https://developers.napster.com/docs/introduction/quickstart |
| Authentication | https://developers.napster.com/docs/introduction/authentication |
| Limits, credits, concurrency | https://developers.napster.com/docs/introduction/limits |
| Create API key, architectures, pricing panel | https://developers.napster.com/docs/guides/create-api-key |
| Digital Twin consent (admin, org-wide) | https://developers.napster.com/docs/guides/digital-twin-consent |
| Digital Twins: fields, media requirements, languages, readiness | https://developers.napster.com/docs/building-your-omniagent/digital-twins |
| Avatar models v1/v2, video requirements | https://developers.napster.com/docs/building-your-omniagent/avatar-models |
| Companion creation, `readyToUse`, listing | https://developers.napster.com/docs/building-your-omniagent/companion |
| Agent configuration, mode, provider settings, Cascade | https://developers.napster.com/docs/building-your-omniagent/configuration |
| Agent update/delete | https://developers.napster.com/docs/building-your-omniagent/managing |
| Tools: implicit vs explicit | https://developers.napster.com/docs/building-your-omniagent/tools/using-tools |
| Knowledge files, formats, limits | https://developers.napster.com/docs/building-your-omniagent/knowledge/files |
| Puppeteer mode, `talk`, limits, errors | https://developers.napster.com/docs/guides/puppeteer-mode |
| WebRTC channel, video policy, green screen | https://developers.napster.com/docs/deploying-your-omniagent/channels/webrtc |
| Memory, `externalClientId`, `initialSpeech`, backend end | https://developers.napster.com/docs/deploying-your-omniagent/session-configuration |
| Web SDK initialization, `getToken`, teardown | https://developers.napster.com/docs/sdks/web-sdk/initialization |
| Sessions, transcripts, close reasons, deletion limits | https://developers.napster.com/docs/monitoring-your-omniagent/sessions |
| FAQ: pricing, data access, disclaimer, timeouts | https://developers.napster.com/docs/faq |
| Endpoint index (for `/public/*` paths) | https://developers.napster.com/docs/api-reference |

**Repo references checked:** `app/napster.py`, `app/ui.py`, `app/vendor/napster-companion-api/2.0.0/PROVENANCE.md`, `factory-lite/docs/stage-3-napster-contract.md`, `factory-lite/HANDOFF.md`, `factory-lite/spec/stage-3.md`, `factory-lite/spec/stage-4.md`.

---

*Documentation-only research. No credentials were read, no Napster account state was changed, no media was uploaded, and no live or paid call was made.*
