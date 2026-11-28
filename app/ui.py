"""End-user rehearsal UI served at "/". Vanilla JS talking to /api/rehearsal.

OFFLINE MODE: the counterpart is a deterministic stand-in. The Napster avatar is
opt-in only: nothing connects on page load. Without server-side credentials the
avatar shows an honest "offline fallback" label and no live claim is made.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SahaI — Negotiation Practice</title>
<style>
*,*::before,*::after{box-sizing:border-box}
html{min-height:100%;background:#0b1220}
body{margin:0;min-height:100vh;background:#0b1220;color:#f4f7f8;font-family:Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased}
button,textarea,input{font:inherit;cursor:pointer}
button:focus-visible,a:focus-visible,textarea:focus-visible,input:focus-visible{outline:2px solid #44d5bd;outline-offset:3px}
[hidden]{display:none !important}
p{margin:.4rem 0}

/* ---- ambient background ---- */
.app-shell{min-height:100vh;position:relative;overflow:hidden;background:radial-gradient(ellipse at 49% 24%,rgba(20,54,64,.22),transparent 46%),#0b1220}
.ambient{pointer-events:none;position:absolute;border-radius:999px;filter:blur(110px);opacity:.13}
.ambient-one{width:300px;height:300px;background:#16b89d;top:8%;left:-230px}
.ambient-two{width:280px;height:280px;background:#2b6377;bottom:3%;right:-200px}

/* ---- topbar ---- */
.topbar{position:relative;z-index:2;height:76px;max-width:1320px;margin:auto;padding:0 42px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(178,201,214,.09)}
.brand{display:inline-flex;gap:10px;align-items:center;text-decoration:none;color:#f4f7f8;font-size:17px;font-weight:650;letter-spacing:-.04em}
.brand-mark{width:27px;height:27px;border-radius:9px;display:grid;place-items:center;background:#44d5bd;color:#09211e;font-family:Georgia,serif;font-size:20px;font-style:italic}
.topbar-center{color:#92a1b1;font-size:12px;display:flex;align-items:center;gap:9px;letter-spacing:.02em}
.session-dot{width:7px;height:7px;display:inline-block;border-radius:50%;background:#44d5bd;box-shadow:0 0 12px rgba(68,213,189,.55)}

/* avatar mini controls (persistent, always in DOM) */
.avatar-mini{display:flex;align-items:center;gap:8px}
.avatar-mini button{font-size:9px;padding:6px 10px;border-radius:6px;border:1px solid rgba(178,201,214,.2);background:rgba(17,28,45,.8);color:#a3b2bd;transition:border-color .2s}
.avatar-mini button:hover{border-color:rgba(68,213,189,.4);color:#44d5bd}
.avatar-status-badge{font-size:9px;color:#82919f;letter-spacing:.05em}

/* ---- main content ---- */
.main-content{position:relative;z-index:1;width:min(1120px,calc(100% - 64px));min-height:calc(100vh - 126px);margin:0 auto;display:flex;flex-direction:column;justify-content:center;padding:48px 0 54px}
.screen-enter{animation:fade-up .42s ease both}
@keyframes fade-up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* ---- offline / mode banner ---- */
.mode-banner{font-size:9px;color:#82919f;letter-spacing:.05em;margin-bottom:16px;display:flex;align-items:center;gap:7px}
.mode-dot{width:5px;height:5px;border-radius:50%;background:#82919f;display:inline-block}

/* ---- lobby ---- */
.lobby{max-width:660px;width:100%;margin:0 auto;text-align:center}
.eyebrow{color:#73cbbd;font-size:9px;letter-spacing:.2em;font-weight:700;display:flex;justify-content:center;align-items:center;gap:10px;text-transform:uppercase}
.eyebrow-line{display:inline-block;width:21px;height:1px;background:#44d5bd}
.lobby h1{margin:18px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:clamp(39px,5.2vw,57px);font-weight:400;line-height:1.05;letter-spacing:-.055em}
.lobby h1 span{color:#73d8c7;font-style:italic}
.lobby-copy{max-width:470px;margin:19px auto 29px;font-size:13px;line-height:1.8;color:#9baab8}
.people-row{max-width:500px;margin:0 auto;position:relative;display:grid;grid-template-columns:1fr 1fr;gap:16px;text-align:left}
.person-card{border:1px solid rgba(177,199,210,.14);border-radius:15px;padding:9px;background:linear-gradient(145deg,rgba(25,39,57,.9),rgba(15,26,42,.91));box-shadow:0 18px 50px rgba(0,0,0,.18)}
.avatar-frame{position:relative;overflow:hidden;border-radius:10px;aspect-ratio:1.28/1;background:linear-gradient(145deg,rgba(45,80,100,.4),rgba(20,35,55,.8))}
.avatar-frame::after{content:'';position:absolute;inset:35% 0 0;background:linear-gradient(transparent,rgba(8,15,25,.65));pointer-events:none}
.avatar-initials{position:absolute;inset:0;display:grid;place-items:center;font-family:Georgia,serif;font-size:clamp(32px,6vw,52px);color:rgba(68,213,189,.4)}
.avatar-live{position:absolute;z-index:1;left:10px;bottom:10px;display:inline-flex;align-items:center;gap:6px;color:#d2dadf;font-size:7px;font-weight:700;letter-spacing:.12em}
.avatar-live span{width:5px;height:5px;border-radius:50%;background:#44d5bd}
.person-info{padding:12px 7px 7px;display:flex;align-items:center;justify-content:space-between}
.person-info h2{margin:0;font-size:13px;font-weight:600}
.person-info p{margin:4px 0 0;color:#91a0ae;font-size:10px}
.person-number{color:#526272;font-family:Georgia,serif;font-size:18px}
.versus-mark{position:absolute;z-index:2;top:38%;left:50%;transform:translate(-50%,-50%);width:31px;height:31px;display:grid;place-items:center;border-radius:50%;background:#0e1928;border:1px solid #34474e;color:#7ed8ca;font-family:Georgia,serif;font-style:italic}
.primary-button{min-height:44px;border:0;border-radius:9px;padding:0 18px;display:inline-flex;align-items:center;justify-content:center;gap:10px;background:#44d5bd;color:#08201e;font-size:11px;font-weight:700;transition:background .2s,transform .2s}
.primary-button:hover{background:#65e4d0;transform:translateY(-1px)}
.lobby-cta{min-width:190px;margin-top:22px}
.reassurance{margin-top:16px;color:#82919f;font-size:9px;letter-spacing:.015em}
.reassurance-dot{display:inline-block;width:5px;height:5px;background:#44d5bd;border-radius:50%;margin:0 6px 1px 0}

/* ---- demo screen ---- */
.demo-screen,.practice-screen,.review-screen,.summary-screen{width:100%}
.screen-heading{display:flex;justify-content:space-between;align-items:end;margin-bottom:27px}
.screen-heading .eyebrow{justify-content:flex-start}
.screen-heading h1{font-family:Georgia,serif;font-size:38px;font-weight:400;margin:12px 0 0;letter-spacing:-.04em}
.screen-heading h1 span{color:#73d8c7;font-style:italic}
.round-chip{border:1px solid rgba(178,201,214,.16);border-radius:30px;color:#a3b2bd;padding:9px 12px;display:inline-flex;align-items:center;gap:8px;font-size:8px;letter-spacing:.12em}
.round-chip span{width:6px;height:6px;border-radius:50%;background:#44d5bd;box-shadow:0 0 8px rgba(68,213,189,.4)}
.demo-grid{display:grid;grid-template-columns:1fr 1.16fr 1fr;gap:16px;align-items:stretch}
.demo-person{padding:10px;border-radius:15px;border:1px solid rgba(178,201,214,.14);background:rgba(17,28,45,.78)}
.demo-person .avatar-frame{aspect-ratio:.88/1}
.demo-person-label,.participant-title{display:flex;align-items:center;gap:9px;padding:12px 4px 3px}
.demo-person-label strong,.participant-title strong{display:block;font-size:11px;font-weight:600}
.demo-person-label small,.participant-title small{display:block;margin-top:3px;color:#8e9daa;font-size:9px}
.speaker-mark{width:24px;height:24px;flex:0 0 24px;display:grid;place-items:center;border-radius:8px;font-size:9px;font-weight:700}
.alex-mark{background:rgba(68,213,189,.13);color:#70decd}
.dana-mark{background:rgba(157,133,226,.15);color:#c4b4f0}
.you-mark{background:rgba(225,174,98,.15);color:#edc07f}
.transcript-panel{min-height:300px;display:flex;flex-direction:column;border-radius:15px;border:1px solid rgba(178,201,214,.14);background:rgba(14,24,39,.88);overflow:hidden}
.transcript-head{padding:15px 17px;display:flex;justify-content:space-between;color:#93a2b0;font-size:8px;letter-spacing:.12em;border-bottom:1px solid rgba(178,201,214,.1)}
.demo-messages{flex:1;padding:17px 14px 12px;overflow-y:auto;max-height:360px}
.message-row{display:flex;gap:8px;align-items:flex-start;margin-bottom:15px}
.message-right{flex-direction:row-reverse}
.message-content{max-width:88%}
.message-name{color:#8fa0ad;font-size:8px;display:block;margin:2px 0 6px}
.message-right .message-name{text-align:right}
.bubble{padding:10px 12px;border-radius:2px 10px 10px 10px;color:#d3dce1;font-size:10px;line-height:1.65}
.bubble-alex{background:rgba(55,126,116,.18);border:1px solid rgba(68,213,189,.15)}
.bubble-dana{background:#192638;border:1px solid rgba(178,201,214,.1);border-radius:10px 2px 10px 10px}
.demo-bottom{display:flex;justify-content:space-between;align-items:center;margin-top:22px}
.text-button{border:0;color:#99a7b3;background:none;font-size:10px;display:inline-flex;align-items:center;gap:8px;padding:8px 0;cursor:pointer}
.finish-button{border:1px solid rgba(178,201,214,.16);color:#a4b0bb;background:transparent;border-radius:8px;display:inline-flex;align-items:center;gap:8px;padding:9px 12px;font-size:9px;cursor:pointer}

/* ---- practice screen (3-column) ---- */
.practice-heading{margin-bottom:20px}
.practice-grid{display:grid;grid-template-columns:1fr 1.18fr 1fr;gap:13px;align-items:stretch}
.practice-card{border:1px solid rgba(178,201,214,.14);border-radius:14px;background:rgba(17,28,45,.82);padding:12px;min-width:0}
.practice-card-top{display:flex;align-items:center;justify-content:space-between;min-height:34px}
.practice-card-top .participant-title{padding:0}
.speaking-tag{color:#80d6c7;font-size:7px;letter-spacing:.1em;display:flex;gap:6px;align-items:center}
.speaking-tag span{width:5px;height:5px;border-radius:50%;background:#44d5bd;box-shadow:0 0 8px rgba(68,213,189,.5)}
.reference-tag{color:#81909c;border:1px solid rgba(178,201,214,.14);border-radius:5px;padding:5px 6px;font-size:6px;letter-spacing:.1em}
.practice-avatar{margin-top:12px}
.avatar-compact{aspect-ratio:1.42/1}
.caption-box{margin-top:11px;padding:10px 11px;border-radius:8px;background:rgba(8,17,29,.55);border:1px solid rgba(178,201,214,.08)}
.caption-label{color:#7ad5c6;font-size:7px;letter-spacing:.13em;font-weight:700}
.caption-box p,.reference-caption p{color:#c0cbd2;font-size:9px;line-height:1.6;margin:6px 0 0}
.camera-toggle{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(178,201,214,.14);border-radius:6px;background:#132033;color:#9eacb7;padding:6px 8px;font-size:8px;cursor:pointer}
.camera-active{color:#72d7c7;border-color:rgba(68,213,189,.4)}
.camera-stage{position:relative;height:163px;margin-top:12px;border-radius:9px;background:radial-gradient(ellipse at 50% 40%,rgba(45,82,86,.36),transparent 55%),linear-gradient(145deg,#172739,#111c2c);border:1px solid rgba(178,201,214,.09);display:grid;place-items:center;overflow:hidden}
.camera-placeholder{display:flex;flex-direction:column;align-items:center;gap:7px;color:#bdc9cf;font-size:10px}
.camera-placeholder small{color:#82919f;font-size:8px}
.camera-orbit{position:relative;width:54px;height:54px;display:grid;place-items:center;margin-bottom:4px;border:1px solid rgba(68,213,189,.3);border-radius:50%}
.camera-initial{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:rgba(68,213,189,.14);color:#80dfd0;font-family:Georgia,serif;font-size:16px}
.camera-pulse{position:absolute;width:6px;height:6px;border-radius:50%;background:#44d5bd;right:1px;top:3px;box-shadow:0 0 0 3px rgba(68,213,189,.13)}
.camera-video{position:absolute;width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
.camera-label{position:absolute;bottom:8px;left:9px;color:#f1f4f3;font-size:7px;letter-spacing:.1em;display:flex;align-items:center;gap:6px}
.camera-label span{width:5px;height:5px;border-radius:50%;background:#44d5bd}
.camera-error{position:absolute;inset:auto 8px 8px;border-radius:6px;padding:6px;background:rgba(8,15,25,.86);color:#f2c4a2;font-size:8px;text-align:center}
.reply-form{margin-top:12px}
.reply-form label{display:block;color:#c4cdd2;font-size:9px;margin-bottom:7px}
.reply-form input{display:block;width:100%;border:1px solid rgba(178,201,214,.15);border-radius:8px;padding:9px 10px;color:#e9eeee;background:rgba(8,16,27,.58);font-size:9px;line-height:1.5}
.reply-form input::placeholder{color:#677887}
.reply-actions{display:flex;justify-content:space-between;align-items:center;margin-top:8px}
.reply-actions > span{color:#788995;font-size:7px}
.send-button{display:inline-flex;align-items:center;gap:7px;border:0;border-radius:6px;padding:7px 10px;background:#44d5bd;color:#09211f;font-size:8px;font-weight:700;cursor:pointer}
.send-button:disabled{opacity:.42;cursor:not-allowed}
.reference-card{opacity:.72}
.reference-avatar .avatar-frame{filter:saturate(.64)}
.reference-caption{margin-top:11px;padding:10px 11px;border-radius:8px;border:1px dashed rgba(178,201,214,.16);background:rgba(8,17,29,.44)}
.reference-caption .caption-label{color:#9cabc2}
.reference-caption p{font-family:Georgia,serif;font-style:italic}

/* napster-avatar slot within practice */
#napster-avatar{width:100%;border-radius:8px;overflow:hidden;min-height:100px;background:rgba(8,16,27,.4)}
#napster-avatar video,#napster-avatar audio{max-width:100%;display:block}
#avatar-label{color:#9baab8;font-size:9px;text-align:center;padding:12px 8px;margin:0}

/* ---- whisper panel ---- */
.whisper-panel{position:relative;max-width:620px;margin:15px auto 0;width:100%;display:grid;grid-template-columns:35px 1fr auto;gap:10px;align-items:center;padding:12px 14px;background:linear-gradient(110deg,rgba(64,54,34,.88),rgba(43,38,31,.94));border:1px solid rgba(229,183,104,.27);border-radius:12px;box-shadow:0 9px 35px rgba(0,0,0,.18)}
.whisper-icon{width:32px;height:32px;border-radius:10px;background:rgba(234,190,111,.14);color:#efc87f;display:grid;place-items:center;font-size:18px}
.whisper-copy > span{color:#d7b974;font-size:7px;letter-spacing:.13em;font-weight:700;display:block}
.whisper-copy p{margin:4px 0 0;color:#f1e4c7;font-size:9px;line-height:1.5}
.whisper-dismiss{position:absolute;right:7px;top:6px;border:0;padding:4px;background:transparent;color:#c7af81;font-size:14px;cursor:pointer}
.whisper-actions{grid-column:2/4;display:flex;gap:8px;align-items:center}
.use-tip,.send-own{display:inline-flex;align-items:center;gap:5px;border-radius:6px;padding:6px 9px;font-size:8px;cursor:pointer}
.use-tip{border:0;background:#e7bd70;color:#2b2418;font-weight:700}
.send-own{color:#decea9;border:1px solid rgba(229,183,104,.25);background:transparent}
.practice-bottom{display:flex;justify-content:space-between;color:#7c8a96;font-size:8px;margin-top:12px}

/* ---- thinking indicator ---- */
.thinking-row{text-align:center;padding:8px 0;color:#9baab8;font-size:9px;font-style:italic}

/* ---- feedback / review screen ---- */
.score-card{display:flex;align-items:center;gap:10px;padding:9px 13px;border:1px solid rgba(178,201,214,.14);border-radius:12px;background:rgba(17,28,45,.75)}
.score-ring{width:42px;height:42px;display:flex;align-items:baseline;justify-content:center;padding-top:10px;border-radius:50%;border:2px solid #44d5bd;box-shadow:inset 0 0 12px rgba(68,213,189,.08)}
.score-ring strong{font-family:Georgia,serif;font-size:15px;font-weight:400}
.score-ring small{font-size:7px;color:#82919f}
.score-card > div:last-child span,.score-card > div:last-child strong{display:block}
.score-card > div:last-child span{color:#82919f;font-size:7px;letter-spacing:.13em}
.score-card > div:last-child strong{color:#e4e9eb;font-size:10px;margin-top:3px}
.review-layout{display:grid;grid-template-columns:1.5fr .8fr;gap:16px}
.review-transcript,.insight-card{border:1px solid rgba(178,201,214,.14);border-radius:13px;background:rgba(17,28,45,.75);padding:16px}
.section-label{display:flex;justify-content:space-between;color:#a9b5bd;font-size:8px;letter-spacing:.13em;font-weight:700}
.section-label > span{color:#758492;font-weight:500}
.review-turn{padding:14px 0;border-bottom:1px solid rgba(178,201,214,.1)}
.review-turn:last-child{border-bottom:0;padding-bottom:2px}
.review-turn-meta{display:flex;align-items:center;gap:8px}
.review-turn-meta strong{font-size:9px}
.turn-number{color:#81909d;font-size:7px;letter-spacing:.1em}
.review-turn > p{color:#c0cbd1;font-size:10px;line-height:1.65;margin:10px 0 0 32px}
.insight-card{background:linear-gradient(145deg,rgba(25,45,54,.75),rgba(17,28,45,.8))}
.insight-icon{width:31px;height:31px;display:grid;place-items:center;color:#67d7c5;background:rgba(68,213,189,.12);border-radius:9px;margin-bottom:16px;font-size:16px}
.insight-card h3{color:#e2e9e9;font-family:Georgia,serif;font-size:19px;line-height:1.3;font-weight:400;margin:11px 0 8px}
.insight-card > p{color:#91a1ad;font-size:9px;line-height:1.7;margin:0 0 18px}

/* ---- summary screen ---- */
.summary-screen{max-width:740px;margin:auto}
.summary-intro{text-align:center}
.summary-spark{margin:0 auto 13px;display:grid;place-items:center;width:43px;height:43px;border-radius:14px;background:rgba(68,213,189,.11);color:#75dccb;font-size:22px}
.summary-intro h1{font-family:Georgia,serif;font-size:42px;font-weight:400;margin:13px 0 0;letter-spacing:-.04em}
.summary-intro h1 span{color:#73d8c7;font-style:italic}
.summary-intro > p{color:#91a1ad;font-size:10px;margin:13px 0 22px}
.stats-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.stat-card{padding:13px 14px;border:1px solid rgba(178,201,214,.14);border-radius:11px;background:rgba(17,28,45,.74)}
.stat-card > span{color:#82919e;font-size:7px;letter-spacing:.12em;display:block}
.stat-card > strong{display:block;color:#e9efef;font-family:Georgia,serif;font-size:26px;font-weight:400;margin:6px 0 2px}
.stat-card > strong i{color:#69d8c7;font-style:normal;font-size:15px}
.stat-card > small{color:#82919e;font-size:8px}
.corrections{margin-top:23px;border:1px solid rgba(178,201,214,.14);border-radius:12px;background:rgba(17,28,45,.72);padding:14px 16px 4px}
.correction-row{padding:15px 0;border-bottom:1px solid rgba(178,201,214,.1)}
.correction-row:last-child{border-bottom:0}
.correction-row h3{margin:5px 0 4px;font-size:10px;font-weight:600;color:#dfe7e8}
.correction-row p{margin:0;color:#91a0ac;font-size:8px;line-height:1.6}
.summary-actions{display:flex;justify-content:center;gap:10px;margin-top:18px}
.secondary-button{color:#c9d2d5;background:#172437;border:1px solid rgba(178,201,214,.14);min-height:40px;border-radius:9px;padding:0 18px;display:inline-flex;align-items:center;gap:10px;font-size:9px}
.secondary-button:hover{background:#203146}

/* ---- footer ---- */
.app-footer{height:50px;max-width:1320px;margin:auto;padding:0 42px;position:relative;z-index:1;border-top:1px solid rgba(178,201,214,.09);display:flex;align-items:center;justify-content:space-between;color:#6f7d8b;font-size:8px;letter-spacing:.14em}
.footer-divider{color:#44d5bd;padding:0 4px}

/* ---- responsive ---- */
@media(max-width:760px){
  .topbar{height:64px;padding:0 20px}
  .main-content{width:min(100% - 36px,560px);padding:34px 0 38px}
  .app-footer{padding:0 20px;height:46px}
  .lobby h1{font-size:46px}
  .demo-grid{grid-template-columns:1fr 1fr}
  .transcript-panel{grid-column:1/-1;grid-row:2;min-height:280px}
  .practice-grid{grid-template-columns:1fr;gap:11px}
  .camera-stage{height:210px}
  .review-layout{grid-template-columns:1fr}
  .whisper-panel{position:fixed;z-index:5;bottom:15px;left:50%;transform:translateX(-50%);width:calc(100% - 24px);max-width:540px;margin:0;grid-template-columns:35px 1fr;padding:14px;box-shadow:0 16px 60px rgba(0,0,0,.5)}
  .whisper-actions{grid-column:2}
}
@media(max-width:420px){
  .topbar{padding:0 16px}
  .main-content{width:calc(100% - 30px);padding-top:28px}
  .lobby h1{font-size:41px}
  .people-row{gap:10px}
  .stats-row{gap:6px}
  .summary-actions{flex-direction:column-reverse}
  .summary-actions button{width:100%}
}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto !important;animation-duration:.01ms !important;transition-duration:.01ms !important}}
</style>
</head>
<body class="app-shell" id="home">
<div class="ambient ambient-one"></div>
<div class="ambient ambient-two"></div>

<!-- Topbar (always visible) -->
<header class="topbar">
  <a class="brand" href="#home" aria-label="SahaI home">
    <span class="brand-mark">s</span><span>SahaI</span>
  </a>
  <div class="topbar-center">
    <span class="session-dot"></span> Negotiation practice
  </div>
  <!-- Persistent Napster avatar controls (kept for existing test compat) -->
  <div class="avatar-mini" id="avatar-panel-header">
    <button data-testid="napster-connect" id="napster-connect">Connect Dana</button>
    <button data-testid="napster-disconnect" id="napster-disconnect" hidden>Disconnect</button>
    <span class="avatar-status-badge">
      Avatar: <span data-testid="napster-status" id="napster-status" data-sdk-status="unavailable" data-avatar-ready="false">offline</span>
    </span>
  </div>
</header>

<!-- Persistent napster SDK mount point (always in DOM, visible in header panel) -->
<div id="napster-avatar-wrapper" style="position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden">
  <div data-testid="napster-avatar" id="napster-avatar">
    <p id="avatar-label">Stand-in avatar: no live connection.</p>
  </div>
</div>

<main class="main-content">

<!-- ========= LOBBY ========= -->
<section id="landing" class="lobby screen-enter">
  <p data-testid="mode-label" class="mode-banner">
    <span class="mode-dot"></span> OFFLINE MODE &mdash; deterministic stand-in. No live or paid calls.
  </p>
  <div class="eyebrow"><span class="eyebrow-line"></span> THE CONVERSATION, BEFORE THE CONVERSATION</div>
  <h1>Find your voice.<br><span>Own the moment.</span></h1>
  <p class="lobby-copy">Watch Alex navigate a salary negotiation, then step in and make it yours.</p>
  <div class="people-row">
    <article class="person-card">
      <div class="avatar-frame"><span class="avatar-initials">A</span><span class="avatar-live"><span></span> CANDIDATE</span></div>
      <div class="person-info"><div><h2>Alex</h2><p>Your body-double</p></div><span class="person-number">01</span></div>
    </article>
    <div class="versus-mark">&amp;</div>
    <article class="person-card">
      <div class="avatar-frame" style="background:linear-gradient(145deg,rgba(80,55,120,.4),rgba(30,20,55,.8))"><span class="avatar-initials" style="color:rgba(180,160,230,.4)">D</span><span class="avatar-live"><span></span> HIRING MANAGER</span></div>
      <div class="person-info"><div><h2>Dana</h2><p>Hiring manager</p></div><span class="person-number">02</span></div>
    </article>
  </div>
  <button data-testid="start-demo" id="start-demo" class="primary-button lobby-cta">Watch the demo &#8594;</button>
  <div class="reassurance"><span class="reassurance-dot"></span> Private practice &middot; No pressure &middot; Just progress</div>
</section>

<!-- ========= DEMO ========= -->
<section id="demo" class="demo-screen screen-enter" hidden>
  <div class="screen-heading">
    <div>
      <div class="eyebrow"><span class="eyebrow-line"></span> ROUND 01 <span style="color:#455563">/</span> WATCH MODE</div>
      <h1>See how Alex <span>handles it.</span></h1>
    </div>
    <div class="round-chip"><span></span> DEMO IN PROGRESS</div>
  </div>
  <div class="demo-grid">
    <div class="demo-person">
      <div class="avatar-frame" style="aspect-ratio:.88/1"><span class="avatar-initials">A</span><span class="avatar-live"><span></span> CANDIDATE</span></div>
      <div class="demo-person-label"><span class="speaker-mark alex-mark">A</span><div><strong>Alex</strong><small>Candidate</small></div></div>
    </div>
    <div class="transcript-panel">
      <div class="transcript-head"><span>THE CONVERSATION</span></div>
      <div class="demo-messages" id="demo-transcript"></div>
    </div>
    <div class="demo-person">
      <div class="avatar-frame" style="aspect-ratio:.88/1;background:linear-gradient(145deg,rgba(80,55,120,.4),rgba(30,20,55,.8))"><span class="avatar-initials" style="color:rgba(180,160,230,.4)">D</span><span class="avatar-live"><span></span> HIRING MANAGER</span></div>
      <div class="demo-person-label"><span class="speaker-mark dana-mark">D</span><div><strong>Dana</strong><small>Hiring manager</small></div></div>
    </div>
  </div>
  <div class="demo-bottom">
    <button class="text-button" id="back-to-lobby">&#8592; Back</button>
    <button data-testid="take-my-seat" id="take-my-seat" class="primary-button">Take Alex&rsquo;s seat &#8594;</button>
  </div>
</section>

<!-- ========= PRACTICE (3-column) ========= -->
<section id="practice" class="practice-screen screen-enter" hidden>
  <div class="screen-heading practice-heading">
    <div>
      <div class="eyebrow"><span class="eyebrow-line"></span> YOUR TURN <span style="color:#455563">/</span> ROUND 01</div>
      <h1>You&rsquo;re up, <span>Alex.</span></h1>
    </div>
    <button class="finish-button" id="finish-practice">End practice &times;</button>
  </div>
  <div class="practice-grid">

    <!-- Left: Dana's avatar -->
    <article data-testid="dana-avatar" class="practice-card" id="dana-col">
      <div class="practice-card-top">
        <div class="participant-title"><span class="speaker-mark dana-mark">D</span><div><strong>Dana</strong><small>Hiring manager</small></div></div>
        <span class="speaking-tag"><span></span> LISTENING</span>
      </div>
      <div class="practice-avatar">
        <div class="avatar-frame avatar-compact" style="background:linear-gradient(145deg,rgba(80,55,120,.4),rgba(30,20,55,.8))">
          <span class="avatar-initials" style="color:rgba(180,160,230,.4)">D</span>
          <span class="avatar-live"><span></span> DANA</span>
          <!-- napster-avatar will be moved here when practice starts -->
        </div>
      </div>
      <div class="caption-box">
        <span class="caption-label">DANA SAYS</span>
        <p id="dana-caption">We&rsquo;re excited to offer you $142,000 base, plus a 10% annual bonus.</p>
      </div>
    </article>

    <!-- Centre: User webcam + input -->
    <article data-testid="user-webcam" class="practice-card" id="user-col">
      <div class="practice-card-top">
        <div class="participant-title"><span class="speaker-mark you-mark">Y</span><div><strong>You</strong><small>Candidate</small></div></div>
        <button class="camera-toggle" id="camera-toggle" aria-label="Toggle camera">&#9654; Camera off</button>
      </div>
      <div class="camera-stage" id="camera-stage">
        <div class="camera-placeholder" id="camera-placeholder">
          <div class="camera-orbit"><span class="camera-initial">Y</span><span class="camera-pulse"></span></div>
          <span>Your space, your pace.</span>
          <small>Camera is optional</small>
        </div>
        <video id="webcam-video" class="camera-video" autoplay muted playsinline hidden></video>
        <span class="camera-label" id="camera-live-label" hidden><span></span> YOU</span>
      </div>
      <p data-testid="mic-denied-fallback" id="mic-denied-fallback" hidden style="color:#f2c4a2;font-size:9px;margin-top:8px">
        Microphone unavailable &mdash; text practice is still available.
      </p>
      <p data-testid="recording-indicator" id="recording-indicator" hidden style="color:#44d5bd;font-size:9px;margin-top:8px">
        &#9679; Recording
      </p>
      <div class="reply-form">
        <label for="practice-input">What would you say to Dana?</label>
        <input data-testid="practice-input" id="practice-input" type="text" autocomplete="off" placeholder="Take a breath. Start wherever feels right&hellip;">
        <div class="reply-actions">
          <span>&#128274; Your words stay yours</span>
          <button data-testid="send-utterance" id="send-utterance" class="send-button">Send &#8594;</button>
        </div>
      </div>
      <div id="transcript" aria-live="polite" style="margin-top:10px;font-size:9px;max-height:120px;overflow-y:auto"></div>
    </article>

    <!-- Right: Alex body-double -->
    <article data-testid="alex-avatar" class="practice-card reference-card" id="alex-col">
      <div class="practice-card-top">
        <div class="participant-title"><span class="speaker-mark alex-mark">A</span><div><strong>Alex</strong><small>Your reference</small></div></div>
        <span class="reference-tag">REFERENCE</span>
      </div>
      <div class="practice-avatar reference-avatar">
        <div class="avatar-frame avatar-compact"><span class="avatar-initials">A</span><span class="avatar-live"><span></span> ALEX</span></div>
      </div>
      <div class="reference-caption">
        <span class="caption-label">ALEX MIGHT SAY</span>
        <p id="alex-caption">&ldquo;Thank you. Could you share how you arrived at that base range?&rdquo;</p>
      </div>
    </article>

  </div><!-- /practice-grid -->

  <!-- Coach whisper panel -->
  <aside id="whisper-panel" class="whisper-panel" hidden aria-live="polite">
    <div class="whisper-icon">&#10024;</div>
    <div class="whisper-copy">
      <span>YOUR COACH, QUIETLY</span>
      <p id="whisper-text"></p>
    </div>
    <button class="whisper-dismiss" id="whisper-dismiss" aria-label="Dismiss coaching tip">&times;</button>
    <div class="whisper-actions">
      <button class="use-tip" id="whisper-use">&#10003; Use this</button>
      <button class="send-own" id="whisper-send-mine">Send mine</button>
    </div>
  </aside>

  <div class="practice-bottom">
    <span><span class="session-dot"></span> Practice is private</span>
    <span id="turn-count">0 responses</span>
  </div>

</section>

<!-- ========= FEEDBACK ========= -->
<section id="feedback" class="review-screen screen-enter" hidden>
  <div class="screen-heading">
    <div>
      <div class="eyebrow"><span class="eyebrow-line"></span> SESSION COMPLETE</div>
      <h1>A moment to <span>reflect.</span></h1>
    </div>
    <div class="score-card">
      <div class="score-ring"><strong id="score-num">—</strong><small>/100</small></div>
      <div><span>NEGOTIATION</span><strong>Confidence</strong></div>
    </div>
  </div>
  <p data-testid="feedback-score" id="feedback-score" style="color:#9baab8;font-size:9px;margin-bottom:12px"></p>
  <div class="review-layout">
    <div class="review-transcript">
      <div class="section-label">YOUR CONVERSATION</div>
      <ul id="evidence" style="padding-left:1rem;margin-top:12px;font-size:10px;color:#c0cbd1;line-height:1.7"></ul>
    </div>
    <aside class="insight-card">
      <div class="insight-icon">&#10024;</div>
      <div class="section-label">A THOUGHT TO TAKE WITH YOU</div>
      <h3>You made room for a real conversation.</h3>
      <p>Curiosity is a powerful opening move. Next time, try pairing it with a clear, confident anchor.</p>
    </aside>
  </div>
  <div class="demo-bottom" style="margin-top:16px">
    <button data-testid="retry-button" id="retry-button" class="text-button">&#8592; Retry</button>
    <button id="go-summary" class="primary-button">See coach summary &#8594;</button>
  </div>
</section>

<!-- ========= SUMMARY ========= -->
<section id="summary" class="summary-screen screen-enter" hidden>
  <div class="summary-intro">
    <div class="summary-spark">&#10024;</div>
    <div class="eyebrow"><span class="eyebrow-line"></span> YOUR COACH SUMMARY</div>
    <h1>Little shifts.<br><span>Big difference.</span></h1>
    <p>Every practice is a step toward the conversation you want to have.</p>
  </div>
  <div class="stats-row">
    <div class="stat-card"><span>WHISPERS SHOWN</span><strong id="stat-shown">—</strong><small>Gentle nudges</small></div>
    <div class="stat-card"><span>ACCEPTED</span><strong id="stat-accepted">—</strong><small>Ideas you made yours</small></div>
    <div class="stat-card"><span>ACCEPTANCE RATE</span><strong id="stat-rate">—<i>%</i></strong><small>There&rsquo;s no wrong number</small></div>
  </div>
  <div class="corrections" id="corrections-list">
    <div class="section-label">KEY CORRECTIONS</div>
  </div>
  <div class="summary-actions">
    <button data-testid="retry-button" id="retry-button-summary" class="secondary-button">&#8635; Retry</button>
    <button id="start-over" class="primary-button">Start over &#8594;</button>
  </div>
</section>

<!-- Persistent bottom bar (always in DOM) -->
<div style="text-align:center;padding:8px 0">
  <p data-testid="thinking-indicator" id="thinking-indicator" hidden class="thinking-row">Dana is thinking&hellip;</p>
  <p id="status" role="status" style="font-size:9px;color:#82919f;min-height:1.2em"></p>
</div>

</main>

<div style="max-width:1120px;margin:0 auto;padding:0 32px">
  <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid rgba(178,201,214,.09);padding:12px 0;font-size:8px;color:#6f7d8b;letter-spacing:.12em">
    <span>SAHAI <span class="footer-divider">&middot;</span> A PRACTICE SPACE</span>
    <div>
      <button data-testid="end-and-delete" id="end-and-delete" style="font-size:8px;padding:5px 9px;border-radius:5px;border:1px solid rgba(178,201,214,.14);background:transparent;color:#82919f;cursor:pointer">End &amp; delete session</button>
      <span data-testid="cleanup-status" id="cleanup-status" hidden style="font-size:8px;color:#9baab8;margin-left:8px"></span>
    </div>
  </div>
</div>

<script>
"use strict";
let sid = null;
let avatarConnectionId = null;
let avatarInstance = null;
let avatarStream = null;
let cameraStream = null;
let cameraOn = false;
let whisperPending = null;    // {text, suggestion} waiting for user action
let prevAccepted = false;     // was the last whisper suggestion accepted?
let turnCount = 0;
const $ = (id) => document.getElementById(id);

// ---- screen management ----
const SCREENS = ["landing", "demo", "practice", "feedback", "summary"];
function show(name) {
  SCREENS.forEach((s) => { $(s).hidden = (s !== name); });
  $("actions-bar").hidden = !(name === "practice" || name === "feedback" || name === "summary");
}

function setStatus(text) { $("status").textContent = text; }
function setThinking(on) { $("thinking-indicator").hidden = !on; }
function setTurnCount(n) { turnCount = n; $("turn-count").textContent = n + " response" + (n === 1 ? "" : "s"); }

// ---- avatar helpers ----
function setAvatarStatus(text, sdkStatus, avatarReady) {
  const el = $("napster-status");
  el.textContent = text;
  el.setAttribute("data-sdk-status", sdkStatus);
  el.setAttribute("data-avatar-ready", avatarReady ? "true" : "false");
  $("napster-disconnect").hidden = (text === "disconnected" || text === "offline");
}
function setAvatarLabel(text) {
  const lbl = $("avatar-label");
  if (lbl) lbl.textContent = text;
}

// ---- API ----
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
    }).finally(() => { sessionPromise = null; });
  }
  return sessionPromise;
}

// ---- SDK ----
const SDK_URL = "/vendor/napster-companion-api/2.0.0/bundle.js";
const SDK_SHA256 = "c1b2db52267af46e172e4c5fbb0c46b67f57729bc841b26ac4e112a14ddd025f";
const SDK_GLOBAL = "napsterCompanionApiSDK";

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
      s.src = url; s.onload = ok;
      s.onerror = () => fail(new Error("SDK script failed to load"));
      document.head.appendChild(s);
    });
  } finally { URL.revokeObjectURL(url); }
  if (!window[SDK_GLOBAL]) throw new Error("SDK global missing");
  return window[SDK_GLOBAL];
}

function fallbackLabel(reason) {
  return "Stand-in avatar (offline fallback): " + reason + ". No live avatar is connected.";
}

async function getAvatarToken() {
  const conn = await api("POST", "/sessions/" + sid + "/napster-session", { channel_type: "webrtc", avatar: "dana" });
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
    avatarInstance = await SDK.init(getAvatarToken, {
      layout: { type: "inline", mountContainer: $("napster-avatar") },
      style: { view: "rectangle", accentColor: "#44d5bd" },
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
        if (window.__napsterSdkStatus !== "readyVideo") { window.__napsterSdkStatus = s; }
        const statusEl = $("napster-status");
        if (window.__napsterSdkStatus !== "readyVideo") { statusEl.setAttribute("data-sdk-status", s); }
        if (s && s !== "readyVideo" && s !== "readyAudio") { setAvatarStatus("connecting", s, false); }
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
    if (sid !== null) await api("DELETE", "/sessions/" + sid + "/napster-session");
  } catch (e) {
    setStatus("Cleanup failed: " + e.message + ". Retry disconnect.");
    return;
  }
  try { if (avatarInstance && typeof avatarInstance.destroy === "function") avatarInstance.destroy(); } catch (e) {}
  avatarInstance = null;
  const slot = $("napster-avatar");
  slot.querySelectorAll("video,audio").forEach((el) => {
    const s = el.srcObject;
    if (s && s.getTracks) s.getTracks().forEach((t) => t.stop());
    el.srcObject = null;
  });
  if (avatarStream) { avatarStream.getTracks().forEach((t) => t.stop()); avatarStream = null; }
  slot.innerHTML = "";
  const lbl = document.createElement("p");
  lbl.id = "avatar-label";
  lbl.textContent = "Stand-in avatar: no live connection.";
  slot.appendChild(lbl);
  avatarConnectionId = null;
  window.__napsterSdkStatus = "unavailable";
  window.__napsterAvatarReady = false;
  setAvatarStatus("disconnected", "unavailable", false);
});

// ---- Demo flow ----
const DEMO_SCRIPT = [
  { who: "Dana", text: "We’re excited to offer you $142,000 base, plus a 10% annual bonus." },
  { who: "Alex", text: "Thank you — I’m really energised about the team. Could you share how you arrived at that base range?" },
  { who: "Dana", text: "We benchmarked against the market and your experience. Is there a number you had in mind?" },
  { who: "Alex", text: "Based on the scope and my experience leading similar launches, I was hoping for closer to $160k. How much flexibility is there?" },
];

function renderDemoTranscript(upTo) {
  const box = $("demo-transcript");
  box.innerHTML = "";
  DEMO_SCRIPT.slice(0, upTo).forEach((m) => {
    const row = document.createElement("div");
    row.className = "message-row" + (m.who === "Dana" ? " message-right" : "");
    const mark = document.createElement("span");
    mark.className = "speaker-mark " + (m.who === "Alex" ? "alex-mark" : "dana-mark");
    mark.textContent = m.who[0];
    const content = document.createElement("div");
    content.className = "message-content";
    const name = document.createElement("span");
    name.className = "message-name";
    name.textContent = m.who;
    const bubble = document.createElement("div");
    bubble.className = "bubble " + (m.who === "Alex" ? "bubble-alex" : "bubble-dana");
    bubble.textContent = m.text;
    content.appendChild(name);
    content.appendChild(bubble);
    row.appendChild(mark);
    row.appendChild(content);
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
  });
}

$("start-demo").addEventListener("click", async () => {
  try {
    await ensureSession();
    renderDemoTranscript(1);
    show("demo");
    let idx = 2;
    const tick = setInterval(() => {
      renderDemoTranscript(idx);
      idx++;
      if (idx > DEMO_SCRIPT.length) clearInterval(tick);
    }, 1800);
    setStatus("Watching the demonstration…");
  } catch (e) { setStatus("Error: " + e.message); }
});

$("back-to-lobby").addEventListener("click", () => show("landing"));

// ---- Move napster-avatar into dana column when entering practice ----
function attachAvatarToDanaColumn() {
  const wrapper = $("napster-avatar-wrapper");
  const danaCol = $("dana-col");
  const avatarEl = $("napster-avatar");
  if (avatarEl && danaCol && wrapper) {
    // Move SDK mount into the practice dana column
    danaCol.appendChild(avatarEl);
    wrapper.style.display = "none";
  }
}

function detachAvatarFromDanaColumn() {
  const wrapper = $("napster-avatar-wrapper");
  const avatarEl = $("napster-avatar");
  if (avatarEl && wrapper) {
    wrapper.appendChild(avatarEl);
    wrapper.style.display = "";
  }
}

// ---- Microphone check ----
async function checkMicrophone() {
  const notice = $("mic-denied-fallback");
  notice.hidden = true;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { notice.hidden = false; return; }
  try {
    const stream = await Promise.race([
      navigator.mediaDevices.getUserMedia({ audio: true }),
      new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 3000)),
    ]);
    stream.getTracks().forEach((t) => t.stop());
    notice.hidden = true;
  } catch (e) { notice.hidden = false; }
}

// ---- Camera toggle ----
$("camera-toggle").addEventListener("click", async () => {
  const btn = $("camera-toggle");
  if (cameraOn) {
    if (cameraStream) { cameraStream.getTracks().forEach((t) => t.stop()); cameraStream = null; }
    $("webcam-video").hidden = true;
    $("camera-placeholder").hidden = false;
    $("camera-live-label").hidden = true;
    btn.textContent = "▶ Camera off";
    btn.classList.remove("camera-active");
    cameraOn = false;
    // notify backend of denial
    if (sid) api("POST", "/sessions/" + sid + "/webcam-token", { camera: "denied", microphone: "granted" }).catch(() => {});
    return;
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    const v = $("webcam-video");
    v.srcObject = cameraStream;
    v.hidden = false;
    $("camera-placeholder").hidden = true;
    $("camera-live-label").hidden = false;
    btn.textContent = "⏹ Camera on";
    btn.classList.add("camera-active");
    cameraOn = true;
    // notify backend
    if (sid) api("POST", "/sessions/" + sid + "/webcam-token", { camera: "granted", microphone: "granted" }).catch(() => {});
  } catch (e) {
    const errEl = document.createElement("div");
    errEl.className = "camera-error";
    errEl.textContent = "Camera unavailable — allow camera access to see yourself.";
    $("camera-stage").appendChild(errEl);
    // notify backend of denial
    if (sid) api("POST", "/sessions/" + sid + "/webcam-token", { camera: "denied", microphone: "denied" }).catch(() => {});
  }
});

$("take-my-seat").addEventListener("click", async () => {
  try {
    await api("POST", "/sessions/" + sid + "/advance", { to: "take_my_seat" });
    await api("POST", "/sessions/" + sid + "/advance", { to: "practice" });
    $("practice-input").value = "";
    renderTranscript([]);
    setTurnCount(0);
    attachAvatarToDanaColumn();
    show("practice");
    setStatus("Demonstration complete. Practice is ready. Probe for what Dana needs.");
    checkMicrophone();
  } catch (e) { setStatus("Error: " + e.message); }
});

$("finish-practice").addEventListener("click", () => {
  if ($("practice-input").value.trim() === "") {
    requestFeedback();
  } else {
    $("practice-input").value = "";
    requestFeedback();
  }
});

// ---- Transcript ----
function renderTranscript(list) {
  const box = $("transcript");
  box.textContent = "";
  list.forEach((entry) => {
    const p = document.createElement("p");
    p.style.cssText = "margin:.3rem 0;padding:4px 8px;border-radius:5px;background:" + (entry.speaker === "user" ? "rgba(68,213,189,.08)" : "rgba(80,55,120,.12)");
    p.textContent = (entry.speaker === "user" ? "You: " : "Dana: ") + entry.utterance;
    box.appendChild(p);
    box.scrollTop = box.scrollHeight;
  });
}

// ---- Coach whisper ----
async function fetchWhisper(utterance) {
  if (!sid) return null;
  try {
    const data = await api("POST", "/sessions/" + sid + "/coach-whisper", {
      utterance: utterance,
      accepted: prevAccepted,
    });
    if (data && data.suggestion) return data.suggestion;
  } catch (e) {
    // 503 = not configured, 404 = unknown session — both are silent
  }
  return null;
}

function showWhisper(suggestion, originalText) {
  whisperPending = { suggestion, originalText };
  $("whisper-text").textContent = suggestion;
  $("whisper-panel").hidden = false;
}

function hideWhisper() {
  whisperPending = null;
  $("whisper-panel").hidden = true;
}

$("whisper-dismiss").addEventListener("click", () => {
  hideWhisper();
  prevAccepted = false;
});

$("whisper-use").addEventListener("click", () => {
  if (!whisperPending) return;
  const text = whisperPending.suggestion;
  hideWhisper();
  prevAccepted = true;
  doSendUtterance(text);
});

$("whisper-send-mine").addEventListener("click", () => {
  if (!whisperPending) return;
  const text = whisperPending.originalText;
  hideWhisper();
  prevAccepted = false;
  doSendUtterance(text);
});

// ---- Send utterance ----
$("send-utterance").addEventListener("click", async () => {
  const text = $("practice-input").value.trim();
  if (text === "") { await requestFeedback(); return; }

  // Show whisper if coach is available, then let the user decide
  $("send-utterance").disabled = true;
  setThinking(true);
  const suggestion = await fetchWhisper(text);
  setThinking(false);
  $("send-utterance").disabled = false;

  if (suggestion && suggestion !== text) {
    // Let user decide: use suggestion or send their own
    $("practice-input").value = "";
    showWhisper(suggestion, text);
    return;
  }
  // No whisper (not configured or same text) — send directly
  await doSendUtterance(text);
});

async function doSendUtterance(text) {
  $("send-utterance").disabled = true;
  $("practice-input").value = "";
  setThinking(true);
  try {
    const reply = await api("POST", "/sessions/" + sid + "/practice", { utterance: text });
    const snap = await api("GET", "/sessions/" + sid);
    renderTranscript(snap.transcript);
    setTurnCount(snap.transcript.filter((t) => t.speaker === "user").length);
    // Update Dana caption with her latest line
    const danaLines = snap.transcript.filter((t) => t.speaker !== "user");
    if (danaLines.length > 0) {
      $("dana-caption").textContent = danaLines[danaLines.length - 1].utterance;
    }
    setStatus(reply.hidden_need_revealed ? "Dana has revealed a constraint." : "Keep probing.");
  } catch (e) { setStatus("Error: " + e.message); }
  finally { setThinking(false); $("send-utterance").disabled = false; }
}

// ---- Feedback ----
async function requestFeedback() {
  $("send-utterance").disabled = true;
  setThinking(true);
  try {
    const fb = await api("POST", "/sessions/" + sid + "/feedback", {});
    const score = fb.evidence_score;
    $("feedback-score").textContent = "Evidence score: " + score + "/100";
    $("score-num").textContent = score;
    const ul = $("evidence");
    ul.innerHTML = "";
    fb.evidence.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = "“" + item.utterance + "”: " + item.note;
      ul.appendChild(li);
    });
    detachAvatarFromDanaColumn();
    show("feedback");
    setStatus("Feedback shown. Retry to practice again from the same starting point.");
  } catch (e) { setStatus("Error: " + e.message); }
  finally { setThinking(false); $("send-utterance").disabled = false; }
}

// ---- Coach summary ----
async function loadCoachSummary() {
  if (!sid) return;
  try {
    const data = await api("GET", "/sessions/" + sid + "/coach-summary");
    $("stat-shown").textContent = data.turns_shown;
    $("stat-accepted").textContent = data.turns_accepted;
    const rate = data.turns_shown > 0 ? Math.round((data.turns_accepted / data.turns_shown) * 100) : 0;
    $("stat-rate").innerHTML = rate + "<i>%</i>";
    const list = $("corrections-list");
    list.innerHTML = '<div class="section-label">KEY CORRECTIONS <span>' + (data.corrections || []).length + ' NOTES</span></div>';
    (data.corrections || []).forEach((c) => {
      const row = document.createElement("div");
      row.className = "correction-row";
      row.innerHTML = '<h3>Turn ' + c.turn + '</h3><p>' + (c.note || "") + '</p>';
      list.appendChild(row);
    });
  } catch (e) {
    // Summary endpoint not yet implemented — show placeholder
    $("stat-shown").textContent = "—";
    $("stat-accepted").textContent = "—";
    $("stat-rate").innerHTML = "—<i>%</i>";
  }
}

$("go-summary").addEventListener("click", async () => {
  await loadCoachSummary();
  show("summary");
});

$("retry-button").addEventListener("click", async () => {
  try {
    await api("POST", "/sessions/" + sid + "/retry", {});
    $("practice-input").value = "";
    renderTranscript([]);
    setTurnCount(0);
    prevAccepted = false;
    hideWhisper();
    attachAvatarToDanaColumn();
    show("practice");
    setStatus("New attempt from the pivot. Discovery starts again.");
  } catch (e) { setStatus("Error: " + e.message); }
});

$("retry-button-summary") && $("retry-button-summary").addEventListener("click", async () => {
  try {
    await api("POST", "/sessions/" + sid + "/retry", {});
    $("practice-input").value = "";
    renderTranscript([]);
    setTurnCount(0);
    prevAccepted = false;
    hideWhisper();
    attachAvatarToDanaColumn();
    show("practice");
    setStatus("New attempt from the pivot.");
  } catch (e) { setStatus("Error: " + e.message); }
});

$("start-over").addEventListener("click", () => { show("landing"); });

// ---- End and delete ----
$("end-and-delete").addEventListener("click", async () => {
  const btn = $("end-and-delete");
  const cleanup = $("cleanup-status");
  btn.disabled = true;
  setThinking(true);
  try {
    if (sid === null) throw new Error("no session to delete");
    const receipt = await api("DELETE", "/sessions/" + sid);
    cleanup.textContent = "Session deleted. Vendor: " +
      (receipt.vendor_session_destroyed ? "none left live" : "retained for retry") +
      ". Attempts: " + (receipt.attempts || 1) + ".";
    cleanup.hidden = false;
    // Stop camera if on
    if (cameraStream) { cameraStream.getTracks().forEach((t) => t.stop()); cameraStream = null; cameraOn = false; }
    detachAvatarFromDanaColumn();
    setStatus("Session deleted. This rehearsal’s local data is gone.");
  } catch (e) { setStatus("Cleanup error: " + e.message); }
  finally { setThinking(false); btn.disabled = false; }
});
</script>

<!-- Hidden actions bar (kept for test compat — always in DOM, hidden by default) -->
<div id="actions-bar" hidden></div>

</body>
</html>
"""
