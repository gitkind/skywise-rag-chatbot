"""
SkyWise: Air India policy assistant (Streamlit UI).

Run:  streamlit run app.py
"""

from __future__ import annotations

import html
import re
import time
from collections import Counter

import streamlit as st

import config
from ui_theme import get_theme_css

st.set_page_config(
    page_title="SkyWise · Air India policy assistant",
    page_icon=":material/flight_takeoff:",
    layout="centered",
    initial_sidebar_state="auto",  # open on desktop, collapsed on phones
)
st.markdown(get_theme_css(), unsafe_allow_html=True)

LOGO = config.ROOT / "assets" / "skywise_logo_dark.png"
if LOGO.exists():
    st.logo(str(LOGO), size="large")

SUGGESTIONS = [
    (":material/event_busy:", "What happens if Air India cancels my flight?"),
    (":material/pets:", "What are the size and weight limits for a pet in the cabin?"),
    (":material/currency_exchange:", "What's the difference between a voluntary and an involuntary refund?"),
    (":material/hotel:", "When does Air India provide a hotel during a long delay?"),
]

STATUS_LABELS = {
    "grounded": ("grounded", "Grounded in {n} source{s}"),
    "abstained": ("abstained", "Not established by the policy documents"),
    "out_of_scope": ("out_of_scope", "Outside the policy documents"),
    "uncited": ("uncited", "No citations. Please verify"),
    "offline": ("offline", "Offline · retrieval only"),
    "error": ("error", "Something went wrong"),
}


# ------------------------------------------------------------------
# Backend (loaded once per server process)
# ------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def load_backend():
    from guardrails import get_cross_encoder
    from hybrid_retrieval import get_corpus, warm_up

    warm_up()
    get_cross_encoder()
    metas = get_corpus()["metadatas"]
    counts = Counter((m.get("document_title", "?"), m.get("audience", "")) for m in metas)
    docs = sorted(({"title": t, "audience": a, "chunks": n} for (t, a), n in counts.items()),
                  key=lambda d: -d["chunks"])
    return {"docs": docs, "chunks": len(metas)}


with st.spinner("Loading policy library and models (first start only)..."):
    try:
        kb = load_backend()
        backend_error = None
    except Exception as exc:  # e.g. vector store missing
        kb, backend_error = {"docs": [], "chunks": 0}, str(exc)

import backend_service as backend  # noqa: E402  (after cache warm-up)

# ------------------------------------------------------------------
# State
# ------------------------------------------------------------------

ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("pending", None)


def ask(question: str):
    ss.pending = question


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------

with st.sidebar:
    if st.button("New conversation", icon=":material/add:", use_container_width=True, type="primary"):
        ss.messages, ss.pending = [], None
        st.rerun()

    st.markdown("### Retrieval")
    strategy = st.segmented_control(
        "Strategy", options=list(backend.STRATEGIES), default="hybrid",
        format_func=lambda k: {"hybrid": "Hybrid", "vector": "Vector"}[k],
        help="Hybrid fuses semantic search with BM25 keyword search (Reciprocal Rank Fusion). "
             "Vector is the baseline for comparison.",
    ) or "hybrid"
    decompose = st.toggle("Query decomposition", value=True,
                          help="Splits multi-part or comparison questions into sub-questions, retrieves "
                               "evidence for each, and rewrites follow-ups using the conversation.")
    include_agent = st.toggle("Include agent & partner policies", value=False,
                              help="Also search the General Booking, Schedule Change & IRROPS and ADM "
                                   "policies, which are written for travel agents.")
    top_k = st.slider("Sources per answer", 3, 8, 5)

    st.markdown("### Knowledge base")
    for d in kb["docs"]:
        if not include_agent and "passenger-facing" not in d["audience"].lower():
            continue
        title = html.escape(d["title"].replace("Air India ", ""))
        tag = "" if "passenger-facing" in d["audience"].lower() else "<span class='tag'>agent</span>"
        st.markdown(f"<div class='kb-row'><span>{title}{tag}</span><span class='n'>{d['chunks']}</span></div>",
                    unsafe_allow_html=True)

    st.markdown("### Model")
    online = backend.is_openai_configured()
    st.markdown(
        f"<div class='status-line'><span class='dot {'on' if online else 'off'}'></span>"
        f"{html.escape(config.LLM_MODEL) if online else 'No API key: retrieval only'}</div>",
        unsafe_allow_html=True)


# ------------------------------------------------------------------
# Rendering helpers
# ------------------------------------------------------------------

def md_safe(text: str) -> str:
    """Escape $ (LaTeX in Streamlit) and turn [S1] markers into badges."""
    text = text.replace("$", "\\$")
    return re.sub(r"\[S(\d{1,2})\]", r" :red-badge[S\1]", text)


def status_badge(result: dict) -> str:
    cls, label = STATUS_LABELS.get(result.get("status", "error"), STATUS_LABELS["error"])
    n = len(result.get("citations", []))
    return f"<div class='badge {cls}'>● {html.escape(label.format(n=n, s='' if n == 1 else 's'))}</div>"


def render_sources(result: dict):
    cites = result.get("citations", [])
    if not cites:
        return
    chips = "".join(
        f"<span class='chip'><span class='m'>{c['marker'][1:]}</span>"
        f"{html.escape(c['title'].replace('Air India ', ''))} <span class='p'>{html.escape(c['pages'])}</span></span>"
        for c in cites)
    st.markdown(f"<div class='chips'>{chips}</div>", unsafe_allow_html=True)

    with st.expander(f"View {len(cites)} source passage{'s' if len(cites) != 1 else ''}", icon=":material/menu_book:"):
        for c in cites:
            flags = ""
            if c.get("is_historical"):
                flags += "<span class='flag hist'>Historical</span>"
            if c.get("audience") and "passenger-facing" not in c["audience"].lower():
                flags += "<span class='flag agent'>Agent-facing</span>"
            bar = ""
            if c.get("relevance") is not None:
                bar = f"<div class='bar'><i style='width:{max(4, round(c['relevance'] * 100))}%'></i></div>"
            st.markdown(
                f"<div class='src'><div class='src-head'><span class='m'>{c['marker'][1:]}</span>"
                f"{html.escape(c['title'])}<span class='pg'>{html.escape(c['pages'])}</span></div>"
                f"<div class='src-meta'>Effective: {html.escape(str(c.get('effective_date', 'Not stated')))}"
                f" · {html.escape(c.get('source_file', ''))} {flags}</div>"
                f"<div class='src-text'>{html.escape(c['excerpt'])}</div>{bar}</div>",
                unsafe_allow_html=True)


def render_trace(result: dict):
    trace = result.get("trace", [])
    if not trace:
        return
    with st.expander("How this answer was made", icon=":material/account_tree:"):
        rows = "".join(
            f"<div class='trace-row'><span class='i'>{i}</span>"
            f"<span><b>{html.escape(s['step'])}</b> <span class='d'>· {html.escape(s.get('detail', ''))}</span></span>"
            f"<span class='ms'>{s['ms']} ms</span></div>"
            for i, s in enumerate(trace, start=1))
        plan = result.get("plan") or {}
        extra = ""
        if plan.get("standalone") and plan["standalone"] != result.get("question"):
            extra += f"<div class='subq'>Searched as: <i>{html.escape(plan['standalone'])}</i></div>"
        if len(plan.get("sub_questions", [])) > 1:
            items = "".join(f"<li>{html.escape(q)}</li>" for q in plan["sub_questions"])
            extra += f"<div class='subq'>Sub-questions:<ul>{items}</ul></div>"
        if result.get("invalid_citations"):
            extra += ("<div class='subq'>⚠ Removed citation markers that pointed at no source: "
                      + ", ".join(f"S{n}" for n in result["invalid_citations"]) + "</div>")
        st.markdown(f"<div class='trace'>{rows}</div>{extra}", unsafe_allow_html=True)


def render_assistant(result: dict, index: int):
    st.markdown("<span class='bot-msg'></span>", unsafe_allow_html=True)
    st.markdown(status_badge(result), unsafe_allow_html=True)
    st.markdown(md_safe(result["answer"]))
    render_sources(result)
    render_trace(result)
    st.feedback("thumbs", key=f"feedback_{index}")


# ------------------------------------------------------------------
# Empty state
# ------------------------------------------------------------------

if backend_error:
    st.error(f"Backend failed to load: {backend_error}", icon=":material/error:")

if not ss.messages and not ss.pending:
    n_docs = len([d for d in kb["docs"] if include_agent or "passenger-facing" in d["audience"].lower()])
    st.markdown(f"""
    <div class="hero">
      <span class="eyebrow">✈ Grounded in <b>{n_docs} official Air India documents</b></span>
      <h1>Travel policies, <span>answered with sources</span></h1>
      <p>Ask about cancellations, refunds, delays, pets in the cabin or baggage.
      Every answer cites the policy page it came from, and SkyWise tells you when the documents don't say.</p>
    </div>""", unsafe_allow_html=True)

    with st.container(key="suggestions"):
        cols = st.columns(2)
        for i, (icon, q) in enumerate(SUGGESTIONS):
            cols[i % 2].button(q, key=f"sugg_{i}", icon=icon, on_click=ask, args=(q,), use_container_width=True)

    st.markdown("<div class='footnote'>Academic project. Always confirm critical travel details on "
                "<a href='https://www.airindia.com' target='_blank'>airindia.com</a>.</div>",
                unsafe_allow_html=True)


# ------------------------------------------------------------------
# Conversation
# ------------------------------------------------------------------

for i, msg in enumerate(ss.messages):
    if msg["role"] == "user":
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown("<span class='user-msg'></span>", unsafe_allow_html=True)
            st.markdown(md_safe(msg["content"]))
    else:
        with st.chat_message("assistant", avatar=":material/flight_takeoff:"):
            render_assistant(msg["result"], i)

typed = st.chat_input("Ask about cancellations, refunds, pets, baggage...", disabled=bool(backend_error))
question = ss.pending or (typed.strip() if typed else None)
ss.pending = None

if question:
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    ss.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown("<span class='user-msg'></span>", unsafe_allow_html=True)
        st.markdown(md_safe(question))

    with st.chat_message("assistant", avatar=":material/flight_takeoff:"):
        st.markdown("<span class='bot-msg'></span>", unsafe_allow_html=True)
        try:
            with st.status("Searching Air India policies...", expanded=False) as status:
                t0 = time.perf_counter()
                prepared = backend.prepare(
                    question, top_k=top_k, strategy=strategy,
                    audience_mode="all" if include_agent else "passenger",
                    decompose=decompose, history=history,
                )
                for s in prepared["trace"]:
                    st.write(f"**{s['step']}** · {s['detail']}")
                label = ("No matching policy found" if prepared["blocked"]
                         else f"Found {len(prepared['chunks'])} relevant passages")
                status.update(label=f"{label} · {time.perf_counter() - t0:.1f}s", state="complete")

            placeholder, answer, g0 = st.empty(), "", time.perf_counter()
            for delta in backend.stream_answer(prepared):
                answer += delta
                placeholder.markdown(md_safe(answer) + " ▍")
            placeholder.empty()
            result = backend.finalize(prepared, answer, round((time.perf_counter() - g0) * 1000))
        except Exception as exc:
            result = {"answer": f"Sorry, something went wrong: `{exc}`", "status": "error",
                      "citations": [], "trace": []}
        result["question"] = question
        result.pop("chunks", None)
        render_assistant(result, len(ss.messages))

    ss.messages.append({"role": "assistant", "content": result["answer"], "result": result})
