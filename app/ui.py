"""End-user rehearsal UI served at "/". Vanilla JS talking to /api/rehearsal.
OFFLINE MODE: the counterpart is a deterministic stand-in; nothing here makes
live or paid calls.
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
const $ = (id) => document.getElementById(id);

function show(name) {
  for (const s of ["landing", "demo", "practice", "feedback"]) {
    $(s).hidden = (s !== name);
  }
}

function setStatus(text) {
  $("status").textContent = text;
}

async function api(method, path, body) {
  const opts = { method: method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch("/api/rehearsal" + path, opts);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || ("HTTP " + res.status));
  }
  return data;
}

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

$("start-demo").addEventListener("click", async () => {
  try {
    const created = await api("POST", "/sessions", {});
    sid = created.session_id;
    show("demo");
    setStatus("Offline demonstration started.");
  } catch (e) {
    setStatus("Error: " + e.message);
  }
});

$("take-my-seat").addEventListener("click", async () => {
  try {
    await api("POST", "/sessions/" + sid + "/advance", { to: "take_my_seat" });
    await api("POST", "/sessions/" + sid + "/advance", { to: "practice" });
    $("practice-input").value = "";
    renderTranscript([]);
    show("practice");
    setStatus("You are in the seat. Probe for what Dana needs.");
  } catch (e) {
    setStatus("Error: " + e.message);
  }
});

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
