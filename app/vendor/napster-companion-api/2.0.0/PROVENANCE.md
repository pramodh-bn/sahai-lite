# Vendored Napster Web SDK - provenance

`app/vendor/napster-companion-api/2.0.0/bundle.js` is Sah's tracked, **unmodified**
copy of Napster's official standalone browser SDK build. Sah serves it same-origin
at `/vendor/napster-companion-api/2.0.0/bundle.js`, and the page requests it only
after the visitor opts in by pressing **Connect live face**.

| Field | Value |
| --- | --- |
| Package | `@touchcastllc/napster-companion-api` |
| Version | `2.0.0` (exact, not a floating channel) |
| License | MIT (`LICENSE`, copied from the package) |
| Source artifact | `lib/index.standalone.js` inside the npm tarball |
| Size | 178617 bytes |
| SHA-256 | `c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f` |
| npm dist.integrity | `sha512-HPrPjFun5+UQLbSfshSkfCT3WqtKBac9TsKbTxIYQjvB8kKC0+jT0WCYAEL+JzKpZk7ruRVRIXFNMimthfHy5Q==` |
| npm dist.shasum | `31ae7bff7d5f2bfd89587f83e3ee822f0c880860` |
| Global installed | `window.napsterCompanionApiSDK` |
| Docs | https://developers.napster.com/docs/sdks/web-sdk/overview |

## Reproduce / verify

```
npm pack @touchcastllc/napster-companion-api@2.0.0
tar -xzf touchcastllc-napster-companion-api-2.0.0.tgz
sha256sum package/lib/index.standalone.js   # must equal the SHA-256 above
cmp package/lib/index.standalone.js app/vendor/napster-companion-api/2.0.0/bundle.js
```

Sah's offline proof and cumulative tests fail if the tracked
`app/vendor/napster-companion-api/2.0.0/bundle.js` no longer matches the size and
SHA-256 recorded here. `.gitattributes` marks the bundle `-text` so checkout
cannot rewrite line endings and change the hash.

## Historical Koehashi stage-5 reference evidence (not Sah certification)

The following runtime observation was captured in the earlier Koehashi stage-5
work and is carried here only as historical reference. It is **not** evidence
that Sah has validated anything.

In that Koehashi run, Microsoft Edge (headless, WebRTC loopback devices) was used
against the live service with real credentials: the bundle was served same-origin,
`SDK.init` resolved using the token from `POST /face-session`, the session status
reached `readyVideo`, `onAvatarReady` fired, and the SDK mounted live `<video>`/`<audio>`
elements into `#napster-avatar`. Those `readyVideo`/`onAvatarReady`/media results
belong to Koehashi stage 5 and must not be read as Sah acceptance or certification.

## Sah live-gate status

Sah has **not** yet enabled or passed its live gate. The live gate remains
disabled and unexecuted, and Sah Stage 3 remains **UNCERTIFIED**. Sah's own
evidence so far is offline only: the Flask test client against the local fake
vendor, with no live credentials and no vendor or paid calls.

## Network behaviour (documented exception)

After opt-in, the SDK opens a WebRTC signaling websocket to
`wss://avatar-signaling.napster.ai` (endpoint returned inside the connection
token). This is the only external connection and it is **not** made unless the
visitor clicks **Connect live face**. In deterministic mock mode (mock vendors
or a non-https `NAPSTER_BASE_URL`) the button is disabled, so the harness's
same-origin network auditor sees only same-origin requests; its checks are
unchanged. The API key never reaches the browser: only the short-lived token
and connection id are returned by `POST /face-session`.
