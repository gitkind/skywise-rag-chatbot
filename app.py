"""
FlyWise (SkyWise by Air India) — Premium Minimal Chatbot UI
Integrated with official SkyWise by Air India logo, dark/light mode engine,
guarded retrieval and citation verification.
"""

import base64
from pathlib import Path
import streamlit as st

# Configure page
st.set_page_config(
    page_title="SkyWise by Air India — Customer Support",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Session State for Dark Mode and Chat
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# Helper to encode logo to base64 for seamless HTML rendering
@st.cache_data
def get_base64_logo(dark: bool = True):
    logo_file = "assets/skywise_logo_dark.png" if dark else "assets/skywise_logo_light.png"
    logo_path = Path(logo_file)
    if not logo_path.exists():
        logo_path = Path("assets/skywise_logo_raw.png")
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{data}"
    return None

logo_base64 = get_base64_logo(st.session_state.dark_mode)

# Load Dynamic Theme (Light vs Dark)
from ui_theme import get_theme_css
st.markdown(get_theme_css(dark_mode=st.session_state.dark_mode), unsafe_allow_html=True)

# Import backend service with Guardrails and Re-ranking
from backend_service import get_flywise_response, is_openai_configured

def select_chip(q):
    st.session_state.pending_question = q


# ==============================================================================
# MINIMAL TOP NAVBAR (SkyWise by Air India Logo & Controls)
# ==============================================================================
col_nav_left, col_nav_right = st.columns([7.2, 2.8], vertical_alignment="center")

with col_nav_left:
    if logo_base64:
        st.markdown(f"""
        <div class="fw-brand">
            <img src="{logo_base64}" class="fw-logo-img" alt="SkyWise by Air India" />
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="fw-brand">
            <div>
                <div class="fw-title">Sky<span>Wise</span></div>
                <div class="fw-sub">by Air India</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_nav_right:
    c_theme, c_reset = st.columns([1, 1])
    with c_theme:
        mode_label = "Light" if st.session_state.dark_mode else "Dark"
        if st.button(mode_label, key="theme_toggle", help="Toggle appearance mode", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    with c_reset:
        if st.button("Reset", key="clear_chat", help="Start new conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()


# ==============================================================================
# WELCOME BANNER & CLEAN PASSENGER PROMPTS
# ==============================================================================
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="fw-welcome">
        <div class="fw-welcome-text">
            <strong>Namaste. Welcome to SkyWise.</strong><br/>
            Direct policy answers grounded in official Air India documents: Conditions of Carriage, Pet Guidelines, Cancellations & Baggage.
        </div>
        <div class="fw-badge">
            <span class="fw-badge-dot"></span> Active Policy RAG
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='fw-chips-label'>Common passenger inquiries</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("What happens if Air India cancels my flight?", key="q1", use_container_width=True):
            select_chip("What happens if Air India cancels my flight?")
            st.rerun()
        if st.button("What are the requirements for pets in the cabin?", key="q2", use_container_width=True):
            select_chip("What are the requirements for pets in the cabin?")
            st.rerun()
    with c2:
        if st.button("What can I carry as cabin baggage?", key="q3", use_container_width=True):
            select_chip("What can I carry as cabin baggage?")
            st.rerun()
        if st.button("What is the cancellation and refund policy?", key="q4", use_container_width=True):
            select_chip("What is the cancellation and refund policy?")
            st.rerun()

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# CONVERSATION STREAM
# ==============================================================================
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    citations = msg.get("citations", [])
    is_abstention = msg.get("is_abstention", False)
    eval_info = msg.get("evaluation", {})

    with st.chat_message(role):
        st.markdown(content)

        if is_abstention and role == "assistant":
            st.markdown("""
            <div class="fw-guardrail-notice">
                <strong>Policy Disclosure:</strong> Abstaining because supplied Air India documents do not establish an answer or entitlement for this query.
            </div>
            """, unsafe_allow_html=True)

        if citations and role == "assistant":
            with st.expander(f"Sources Used ({len(citations)})", expanded=False):
                for cit in citations:
                    st.markdown(f"""
                    <div class="fw-citation-card">
                        <div class="fw-citation-header">
                            <span>{cit['title']}</span>
                            <span class="fw-citation-pill">{cit['pages']}</span>
                        </div>
                        <div style="font-size:11px; opacity:0.75; margin-bottom:4px;">
                            Effective: {cit.get('effective_date', 'Undated')} | Source: {cit.get('source_file', 'N/A')}
                        </div>
                        <div class="fw-citation-excerpt">
                            "{cit['excerpt']}"
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        if eval_info and role == "assistant":
            st.markdown(f"""
            <div class="fw-eval-badge">
                Status: <strong>{eval_info.get('guardrail', 'verified')}</strong> • Relevance Score: {eval_info.get('max_cos_sim', 'N/A')}
            </div>
            """, unsafe_allow_html=True)


# ==============================================================================
# INPUT COMPOSER
# ==============================================================================
user_text = st.chat_input("Ask SkyWise about baggage, cancellations, refunds, pet policies...")

active_query = None
if st.session_state.pending_question:
    active_query = st.session_state.pending_question
    st.session_state.pending_question = None
elif user_text and user_text.strip():
    active_query = user_text.strip()

if active_query:
    st.session_state.messages.append({"role": "user", "content": active_query})

    with st.chat_message("user"):
        st.markdown(active_query)

    with st.chat_message("assistant"):
        with st.spinner("Checking Air India policy documents..."):
            result = get_flywise_response(active_query)

            answer = result["answer"]
            citations = result["citations"]
            is_abstention = result["is_abstention"]
            eval_info = result["evaluation"]

            st.markdown(answer)

            if is_abstention:
                st.markdown("""
                <div class="fw-guardrail-notice">
                    <strong>Policy Disclosure:</strong> Abstaining because supplied Air India documents do not establish an answer or entitlement for this query.
                </div>
                """, unsafe_allow_html=True)

            if citations:
                with st.expander(f"Sources Used ({len(citations)})", expanded=False):
                    for cit in citations:
                        st.markdown(f"""
                        <div class="fw-citation-card">
                            <div class="fw-citation-header">
                                <span>{cit['title']}</span>
                                <span class="fw-citation-pill">{cit['pages']}</span>
                            </div>
                            <div style="font-size:11px; opacity:0.75; margin-bottom:4px;">
                                Effective: {cit.get('effective_date', 'Undated')} | Source: {cit.get('source_file', 'N/A')}
                            </div>
                            <div class="fw-citation-excerpt">
                                "{cit['excerpt']}"
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            if eval_info:
                st.markdown(f"""
                <div class="fw-eval-badge">
                    Status: <strong>{eval_info.get('guardrail', 'verified')}</strong> • Relevance Score: {eval_info.get('max_cos_sim', 'N/A')}
                </div>
                """, unsafe_allow_html=True)

    # Persist in session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "citations": citations,
        "is_abstention": is_abstention,
        "evaluation": eval_info
    })


# ==============================================================================
# FOOTER
# ==============================================================================
st.markdown("""
<div class="fw-mini-footer">
    SkyWise is an academic AI assistant grounded in Air India policy documents. Always confirm critical flight details at <a href="https://www.airindia.com" target="_blank" style="color:var(--air-red); text-decoration:none; font-weight:600;">airindia.com</a>.
</div>
""", unsafe_allow_html=True)
