"""End-user rehearsal UI served at "/". Vanilla JS talking to /api/rehearsal.

OFFLINE MODE: the counterpart is a deterministic stand-in. The Napster avatar is
opt-in only: nothing connects on page load. Without server-side credentials the
avatar shows an honest "offline fallback" label and no live claim is made.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Negotiation rehearsal (offline)</title>
</head>
<body>
<h1>Negotiation rehearsal: Alex and Dana</h1>
<p data-testid="mode-label"><strong>OFFLINE MODE</strong>: deterministic stand-in counterpart. No live or paid calls.</p>

<section id="avatar-panel" aria-label="Embodied avatar (opt-in)">
  <p>
    <button data-testid="napster-connect" id="napster-connect">Connect live avatar (opt-in)</button>
    <button data-testid="napster-disconnect" id="napster-disconnect" hidden>Disconnect avatar</button>
  </p>
  <p>Avatar status: <span data-testid="napster-status" id="napster-status" data-sdk-status="unavailable" data-avatar-ready="false">disconnected</span></p>
  <div data-testid="napster-avatar" id="napster-avatar">
    <p id="avatar-label">Stand-in avatar: no live connection.</p>
  </div>
</section>

<section id="landing">
  <p>Watch a stand-in demonstrate the negotiation, then take your seat and practice.</p>
  <button data-testid="start-demo" id="start-demo">Start demo</button>
</section>

<section id="demo" hidden>
  <h2>Stand-in demonstration</h2>
  <p>The stand-in opens with a neutral question and holds back its constraints until probed.</p>
  <button data-testid="take-my-seat" id="take-my-seat">Take my seat</button>
</section>

<section id="practice" hidden>
  <h2>Practice: you are Alex</h2>
  <p data-testid="mic-denied-fallback" id="mic-denied-fallback" hidden>
    Microphone is unavailable (denied or missing). Text practice is still available below.
  </p>
  <div id="transcript" aria-live="polite"></div>
  <label>Your message to Dana
    <input data-testid="practice-input" id="practice-input" type="text" autocomplete="off">
  </label>
  <button data-testid="send-utterance" id="send-utterance">Send</button>
  <p>Send an empty message to finish this attempt and see feedback.</p>
</section>

<section id="feedback" hidden>
  <h2>Evidence-based feedback</h2>
  <p data-testid="feedback-score" id="feedback-score"></p>
  <ul id="evidence"></ul>
  <button data-testid="retry-button" id="retry-button">Retry</button>
</section>

<p id="status" role="status"></p>

<script>
let sid = null;
let avatarConnectionId = null;
let avatarInstance = null;
let avatarStream = null;
const $ = (id) => document.getElementById(id);

// Frozen Web SDK provenance (factory-lite/docs/stage-3-napster-contract.md section 9).
const SDK_URL = "/vendor/napster-companion-api/2.0.0/bundle.js";
const SDK_SHA256 = "c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f";
const SDK_GLOBAL = "napsterCompanionApiSDK";

function show(name) {
  for (const s of ["landing", "demo", "practice", "feedback"]) {
    $(s).hidden = (s !== name);
  }
}

function setStatus(text) {
  $("status").textContent = text;
}

function setAvatarStatus(text, sdkStatus, avatarReady) {
  const el = $("napster-status");
  el.textContent = text;
  el.setAttribute("data-sdk-status", sdkStatus);
  el.setAttribute("data-avatar-ready", avatarReady ? "true" : "false");
  $("napster-disconnect").hidden = (text === "disconnected");
}

function setAvatarLabel(text) {
  $("avatar-label").textContent = text;
}

async function api(method, path, body) {
  const opts = { method: method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch("/api/rehearsal" + path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || ("HTTP " + res.status));
    err.status = res.status;
    throw err;
  }
  return data;
}

let sessionPromise = null;
async function ensureSession() {
  if (sid !== null) return sid;
  if (sessionPromise === null) {
    sessionPromise = api("POST", "/sessions", {}).then((created) => {
      sid = created.session_id;
      return sid;
    }).finally(() => {
      sessionPromise = null;
    });
  }
  return sessionPromise;
}

// Loads the frozen SDK only after its bytes match the pinned SHA-256.
async function loadSdk() {
  if (window[SDK_GLOBAL]) return window[SDK_GLOBAL];
  const res = await fetch(SDK_URL, { cache: "no-store" });
  if (!res.ok) throw new Error("SDK bundle not available (HTTP " + res.status + ")");
  const bytes = await res.arrayBuffer();
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  const hex = Array.from(digest, (b) => b.toString(16).padStart(2, "0")).join("");
  if (hex !== SDK_SHA256) throw new Error("SDK integrity check failed");
  const url = URL.createObjectURL(new Blob([bytes], { type: "text/javascript" }));
  try {
    await new Promise((ok, fail) => {
      const s = document.createElement("script");
      s.src = url;
      s.onload = ok;
      s.onerror = () => fail(new Error("SDK script failed to load"));
      document.head.appendChild(s);
    });
  } finally {
    URL.revokeObjectURL(url);
  }
  if (!window[SDK_GLOBAL]) throw new Error("SDK global missing");
  return window[SDK_GLOBAL];
}

function fallbackLabel(reason) {
  return "Stand-in avatar (offline fallback): " + reason + ". No live avatar is connected.";
}

// The SDK mints its own token when the microphone settles, so the token
// endpoint is called here on demand rather than pre-fetching on page load.
async function getAvatarToken() {
  const conn = await api("POST", "/sessions/" + sid + "/napster-session", { channel_type: "webrtc" });
  avatarConnectionId = conn.connection_id;
  return conn.token;
}

$("napster-connect").addEventListener("click", async () => {
  setAvatarStatus("connecting", "connecting", false);
  setAvatarLabel("Connecting live avatar...");
  try {
    await ensureSession();
    const SDK = await loadSdk();
    if (typeof SDK.init !== "function") throw new Error("SDK exposes no init()");
    // The SDK mounts its own <video>/<audio> into the avatar slot. Live status
    // is only claimed when the frozen onAvatarReady(true) callback fires.
    avatarInstance = await SDK.init(getAvatarToken, {
      layout: { type: "inline", mountContainer: $("napster-avatar") },
      style: { view: "rectangle", accentColor: "#0091ff" },
      onAvatarReady: (isReady) => {
        window.__napsterAvatarReady = isReady;
        const statusEl = $("napster-status");
        statusEl.setAttribute("data-avatar-ready", isReady === true ? "true" : "false");
        if (isReady === true) {
          window.__napsterSdkStatus = "readyVideo";
          statusEl.setAttribute("data-sdk-status", "readyVideo");
          setAvatarStatus("connected", "readyVideo", true);
          setAvatarLabel("Live Napster avatar connected.");
        } else {
          setAvatarStatus("disconnected", "unavailable", false);
        }
      },
      onSessionStatusChange: (status) => {
        const s = String(status && status.status ? status.status : status);
        if (window.__napsterSdkStatus !== "readyVideo") {
          window.__napsterSdkStatus = s;
        }
        const statusEl = $("napster-status");
        if (window.__napsterSdkStatus !== "readyVideo") {
          statusEl.setAttribute("data-sdk-status", s);
        }
        if (s && s !== "readyVideo" && s !== "readyAudio") {
          setAvatarStatus("connecting", s, false);
        }
      },
      onError: (err) => {
        setAvatarStatus("offline fallback", "unavailable", false);
        setAvatarLabel(fallbackLabel(String(err && err.message ? err.message : err)));
      },
    });
  } catch (e) {
    setAvatarStatus("offline fallback", "unavailable", false);
    setAvatarLabel(fallbackLabel(e.message));
  }
});

$("napster-disconnect").addEventListener("click", async () => {
  try {
    if (sid !== null) {
      await api("DELETE", "/sessions/" + sid + "/napster-session");
    }
  } catch (e) {
    // The server retains the vendor handle so disconnect can be retried.
    setStatus("Cleanup failed: " + e.message + ". Retry disconnect.");
    return;
  }
  try {
    if (avatarInstance && typeof avatarInstance.destroy === "function") {
      avatarInstance.destroy();
    }
  } catch (e) {
    // Fall through to explicit local cleanup.
  }
  avatarInstance = null;
  const slot = $("napster-avatar");
  slot.querySelectorAll("video,audio").forEach((el) => {
    const s = el.srcObject;
    if (s && s.getTracks) s.getTracks().forEach((t) => t.stop());
    el.srcObject = null;
  });
  if (avatarStream) {
    avatarStream.getTracks().forEach((t) => t.stop());
    avatarStream = null;
  }
  slot.textContent = "";
  const label = document.createElement("p");
  label.id = "avatar-label";
  label.textContent = "Stand-in avatar: no live connection.";
  slot.appendChild(label);
  avatarConnectionId = null;
  window.__napsterSdkStatus = "unavailable";
  window.__napsterAvatarReady = false;
  setAvatarStatus("disconnected", "unavailable", false);
});

$("start-demo").addEventListener("click", async () => {
  try {
    await ensureSession();
    show("demo");
    setStatus("Offline demonstration started.");
  } catch (e) {
    setStatus("Error: " + e.message);
  }
});

async function checkMicrophone() {
  const notice = $("mic-denied-fallback");
  notice.hidden = false;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
  try {
    const stream = await Promise.race([
      navigator.mediaDevices.getUserMedia({ audio: true }),
      new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 3000)),
    ]);
    stream.getTracks().forEach((t) => t.stop());
    notice.hidden = true;
  } catch (e) {
    notice.hidden = false;
  }
}

$("take-my-seat").addEventListener("click", async () => {
  try {
    await api("POST", "/sessions/" + sid + "/advance", { to: "take_my_seat" });
    await api("POST", "/sessions/" + sid + "/advance", { to: "practice" });
    $("practice-input").value = "";
    renderTranscript([]);
    show("practice");
    setStatus("Demonstration complete. Practice is ready. You are in the seat: probe for what Dana needs.");
    checkMicrophone();
  } catch (e) {
    setStatus("Error: " + e.message);
  }
});

function renderTranscript(list) {
  const box = $("transcript");
  box.textContent = "";
  list.forEach((entry) => {
    const p = document.createElement("p");
    p.textContent = (entry.speaker === "user" ? "You: " : "Dana: ") + entry.utterance;
    box.appendChild(p);
  });
}

async function requestFeedback() {
  const fb = await api("POST", "/sessions/" + sid + "/feedback", {});
  $("feedback-score").textContent = "Evidence score: " + fb.evidence_score + "/100";
  const ul = $("evidence");
  ul.textContent = "";
  fb.evidence.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = "\\"" + item.utterance + "\\": " + item.note;
    ul.appendChild(li);
  });
  show("feedback");
  setStatus("Feedback shown. Retry to practice again from the same starting point.");
}

$("send-utterance").addEventListener("click", async () => {
  const btn = $("send-utterance");
  const text = $("practice-input").value.trim();
  btn.disabled = true;
  try {
    if (text === "") {
      await requestFeedback();
    } else {
      const reply = await api("POST", "/sessions/" + sid + "/practice", { utterance: text });
      $("practice-input").value = "";
      const snap = await api("GET", "/sessions/" + sid);
      renderTranscript(snap.transcript);
      setStatus(reply.hidden_need_revealed
        ? "Dana has revealed a constraint in this attempt."
        : "Keep probing.");
    }
  } catch (e) {
    setStatus("Error: " + e.message);
  } finally {
    btn.disabled = false;
  }
});

$("retry-button").addEventListener("click", async () => {
  try {
    await api("POST", "/sessions/" + sid + "/retry", {});
    $("practice-input").value = "";
    renderTranscript([]);
    show("practice");
    setStatus("New attempt from the pivot. Discovery starts again.");
  } catch (e) {
    setStatus("Error: " + e.message);
  }
});
</script>
</body>
</html>
"""
