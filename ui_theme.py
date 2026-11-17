"""SkyWise UI theme: dark, Air India red / aubergine / gold, Inter typeface."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600&display=swap');

:root {
  --red: #E02645;
  --red-soft: rgba(224, 38, 69, 0.14);
  --gold: #D9BD84;
  --gold-soft: rgba(217, 189, 132, 0.14);
  --bg: #12060C;
  --surface: #1C0A13;
  --surface-2: #26101B;
  --border: rgba(255, 255, 255, 0.08);
  --border-strong: rgba(255, 255, 255, 0.14);
  --text: #F7F2EF;
  --muted: #B3A3AD;
  --green: #4CC38A;
  --amber: #F0B04A;
  --blue: #6AA9FF;
  --radius: 14px;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}
.stApp {
  background:
    radial-gradient(1200px 500px at 85% -10%, rgba(224, 38, 69, 0.16), transparent 60%),
    radial-gradient(900px 500px at -10% 0%, rgba(122, 30, 70, 0.22), transparent 55%),
    var(--bg) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stBottom"], [data-testid="stBottom"] > div { background: transparent !important; }
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 880px !important;
  padding-top: 2.2rem !important;
  padding-bottom: 7rem !important;
}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  background: rgba(20, 7, 13, 0.92) !important;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] h3 {
  font-size: 11px !important; letter-spacing: .12em; text-transform: uppercase;
  color: var(--muted) !important; font-weight: 600 !important; margin: 18px 0 6px !important;
}
.kb-row {
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: 10px; font-size: 13px; color: var(--text);
  background: rgba(255,255,255,0.03); border: 1px solid var(--border); margin-bottom: 6px;
}
.kb-row .n { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 12px; }
.kb-row .tag { font-size: 10px; padding: 1px 6px; border-radius: 99px; background: var(--gold-soft); color: var(--gold); margin-left: 6px; }
.status-line { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted); margin-top: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.on { background: var(--green); box-shadow: 0 0 0 3px rgba(76,195,138,.18); }
.dot.off { background: var(--amber); box-shadow: 0 0 0 3px rgba(240,176,74,.18); }

/* ---------- hero ---------- */
.hero { text-align: center; padding: 6vh 0 18px; }
.eyebrow {
  display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 99px;
  border: 1px solid var(--border-strong); background: rgba(255,255,255,0.03);
  font-size: 12.5px; color: var(--muted);
}
.eyebrow b { color: var(--gold); font-weight: 600; }
.hero h1 {
  font-family: 'Fraunces', Georgia, serif !important; font-weight: 600 !important;
  font-size: clamp(30px, 5vw, 46px) !important; line-height: 1.12 !important;
  margin: 18px 0 10px !important; padding: 0 !important; color: var(--text) !important;
}
.hero h1 span {
  background: linear-gradient(90deg, #FF5A75, var(--gold));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { color: var(--muted); font-size: 15.5px; max-width: 560px; margin: 0 auto; }

/* suggestion cards */
.st-key-suggestions button {
  width: 100%; min-height: 76px; justify-content: flex-start !important; text-align: left !important;
  background: rgba(255,255,255,0.035) !important; border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important; color: var(--text) !important; padding: 14px 16px !important;
  transition: border-color .15s, background .15s, transform .15s;
}
.st-key-suggestions button:hover {
  border-color: rgba(224, 38, 69, 0.55) !important; background: var(--red-soft) !important;
  transform: translateY(-1px);
}
.st-key-suggestions button p { font-size: 14px !important; line-height: 1.4 !important; }
.st-key-suggestions button [data-testid="stIconMaterial"] { color: var(--gold) !important; }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {
  background: transparent !important; padding: 6px 0 !important; gap: 12px !important;
}
[data-testid="stChatMessage"]:has(.user-msg) { flex-direction: row-reverse; }
[data-testid="stChatMessage"]:has(.user-msg) [data-testid="stChatMessageContent"] {
  background: linear-gradient(135deg, rgba(224,38,69,.22), rgba(122,30,70,.28));
  border: 1px solid rgba(224, 38, 69, 0.28);
  border-radius: 18px 18px 4px 18px; padding: 10px 16px; margin-left: auto; max-width: 78%;
  flex: 0 1 auto;
}
[data-testid="stChatMessage"]:has(.bot-msg) [data-testid="stChatMessageContent"] {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 4px 18px 18px 18px; padding: 14px 18px 10px;
}
[data-testid="stChatMessageContent"] p, [data-testid="stChatMessageContent"] li { font-size: 15px; line-height: 1.62; }
.user-msg, .bot-msg { display: none; }

.badge {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;
  padding: 4px 10px; border-radius: 99px; margin-bottom: 8px; border: 1px solid transparent;
}
.badge.grounded { color: var(--green); background: rgba(76,195,138,.12); border-color: rgba(76,195,138,.25); }
.badge.abstained, .badge.uncited { color: var(--amber); background: rgba(240,176,74,.12); border-color: rgba(240,176,74,.25); }
.badge.out_of_scope { color: var(--muted); background: rgba(255,255,255,.06); border-color: var(--border-strong); }
.badge.offline { color: var(--blue); background: rgba(106,169,255,.12); border-color: rgba(106,169,255,.25); }
.badge.error { color: #FF7B8F; background: var(--red-soft); border-color: rgba(224,38,69,.35); }

/* source chips + cards */
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 2px; }
.chip {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text);
  padding: 4px 10px 4px 4px; border-radius: 99px; background: var(--surface-2); border: 1px solid var(--border);
}
.chip .m, .src .m {
  display: inline-grid; place-items: center; min-width: 22px; height: 22px; border-radius: 99px;
  background: var(--red); color: white; font-size: 11px; font-weight: 700;
}
.chip .p { color: var(--muted); }
.src {
  border: 1px solid var(--border); background: rgba(255,255,255,0.025); border-radius: 12px;
  padding: 12px 14px; margin-bottom: 10px;
}
.src-head { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 14px; }
.src-head .pg { margin-left: auto; font-size: 12px; color: var(--gold); background: var(--gold-soft); padding: 2px 8px; border-radius: 99px; white-space: nowrap; }
.src-meta { font-size: 12px; color: var(--muted); margin: 6px 0; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.flag { font-size: 10.5px; font-weight: 600; padding: 1px 7px; border-radius: 99px; }
.flag.hist { color: var(--amber); background: rgba(240,176,74,.12); }
.flag.agent { color: var(--blue); background: rgba(106,169,255,.12); }
.src-text {
  font-size: 13px; color: #DCCFD6; line-height: 1.55;
  display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;
}
.bar { height: 4px; border-radius: 4px; background: rgba(255,255,255,.07); margin-top: 10px; overflow: hidden; }
.bar > i { display: block; height: 100%; background: linear-gradient(90deg, var(--red), var(--gold)); }

/* pipeline trace */
.trace { display: grid; gap: 6px; }
.trace-row { display: grid; grid-template-columns: 22px 1fr auto; gap: 10px; align-items: center; font-size: 13px; }
.trace-row .i { width: 22px; height: 22px; border-radius: 99px; background: var(--surface-2); border: 1px solid var(--border-strong);
  display: grid; place-items: center; font-size: 11px; color: var(--gold); }
.trace-row .d { color: var(--muted); font-size: 12px; }
.trace-row .ms { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 12px; }
.subq { font-size: 13px; color: var(--muted); margin-top: 10px; }
.subq li { margin: 2px 0; }

[data-testid="stExpander"] details {
  border: 1px solid var(--border) !important; border-radius: 12px !important; background: transparent !important;
}
[data-testid="stExpander"] summary p { font-size: 13px !important; color: var(--muted) !important; }

/* chat input */
[data-testid="stChatInput"] {
  border-radius: 16px !important; border: 1px solid var(--border-strong) !important;
  background: var(--surface) !important; box-shadow: 0 10px 40px rgba(0,0,0,.45);
}
[data-testid="stChatInput"]:focus-within { border-color: rgba(224,38,69,.6) !important; }

.footnote { text-align: center; font-size: 12px; color: var(--muted); margin-top: 28px; }
.footnote a { color: var(--gold); text-decoration: none; }

@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding-left: 16px !important; padding-right: 16px !important; }
  [data-testid="stChatMessage"]:has(.user-msg) [data-testid="stChatMessageContent"] { max-width: 92%; }
}
</style>
"""


def get_theme_css() -> str:
    return CSS
