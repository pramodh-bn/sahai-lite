# Vendored Napster Web SDK — provenance

`napster-sdk.js` is the **unmodified** standalone build of Napster's official
browser SDK. It is served by this service same-origin at `/lib/napster-sdk.js`
and loaded by the page only after the visitor presses **Connect live face**.

| Field | Value |
| --- | --- |
| Package | `@touchcastllc/napster-companion-api` |
| Version | `2.0.0` (exact, not a floating channel) |
| License | MIT (`napster-companion-api.LICENSE`, copied from the package) |
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
cmp package/lib/index.standalone.js stage-5/lib/napster-sdk.js
```

`harness/test_face_speech.py` fails if the vendored file no longer matches the
SHA-256 and size recorded here.

## Runtime validation (live)

Validated in Microsoft Edge (headless, WebRTC loopback devices) against the live
service with real credentials: the bundle is served same-origin, `SDK.init`
resolves using the token from `POST /face-session`, the session status reaches
`readyVideo`, `onAvatarReady` fires, and the SDK mounts live `<video>`/`<audio>`
elements into `#napster-avatar`.

## Network behaviour (documented exception)

After opt-in, the SDK opens a WebRTC signaling websocket to
`wss://avatar-signaling.napster.ai` (endpoint returned inside the connection
token). This is the only external connection and it is **not** made unless the
visitor clicks **Connect live face**. In deterministic mock mode (mock vendors
or a non-https `NAPSTER_BASE_URL`) the button is disabled, so the harness's
same-origin network auditor sees only same-origin requests; its checks are
unchanged. The API key never reaches the browser: only the short-lived token
and connection id are returned by `POST /face-session`.
