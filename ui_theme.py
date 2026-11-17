"""
Air India Official Design System Tokens & Dynamic Theme Engine (Light / Dark Mode)
Carefully tuned for seamless background, clean button contrast, and professional airline aesthetics.
"""

def get_theme_css(dark_mode: bool = True) -> str:
    if dark_mode:
        css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

:root {
  --air-red: #E02645;
  --air-aubergine: #4A122E;
  --air-gold: #DFC894;
  --air-rose-gold: #E8B4BC;
  --background: #14070D;
  --surface: #1E0B14;
  --surface-alt: #260E1A;
  --text-primary: #FAF7F2;
  --text-secondary: #BCAEBA;
  --border: #3D182B;
  --border-light: #52203A;
  --soft-highlight: #2A0E1E;
  --radius-card: 10px;
  --radius-button: 6px;
  --radius-input: 8px;
}

/* Base application container, viewport & bottom fixed area */
html, body, [data-testid="stAppViewContainer"], .stApp,
[data-testid="stBottom"], [data-testid="stBottom"] > div,
.stChatFloatingInputContainer, [data-testid="stBottomBlockContainer"] {
    background-color: var(--background) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 5.5rem !important;
    max-width: 960px !important;
}

[data-testid="stHeader"] {
    display: none !important;
}

/* Minimal Header Bar */
.fw-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-card);
    margin-bottom: 14px;
}

.fw-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.fw-logo-img {
    height: 48px;
    width: auto;
    object-fit: contain;
    filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.4));
}

.fw-title {
    font-family: 'Manrope', sans-serif;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.3px;
    color: var(--air-red);
    line-height: 1.1;
}

.fw-title span {
    color: var(--air-rose-gold);
}

.fw-sub {
    font-size: 10px;
    font-weight: 700;
    color: var(--air-gold);
    letter-spacing: 0.9px;
    text-transform: uppercase;
}

.fw-badge {
    background: var(--soft-highlight);
    color: var(--air-rose-gold);
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 14px;
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 6px;
}

.fw-badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #22c55e;
}

/* Welcome Banner */
.fw-welcome {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--air-red);
    border-radius: var(--radius-card);
    padding: 12px 18px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.fw-welcome-text {
    font-size: 13.5px;
    color: var(--text-primary);
    line-height: 1.45;
}

.fw-welcome-text strong {
    color: var(--air-gold);
    font-family: 'Manrope', sans-serif;
}

.fw-chips-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: var(--air-gold);
    margin-bottom: 8px;
}

/* ALL BUTTONS IN DARK MODE - Eliminate White Spots completely */
.stButton button,
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-primary"],
div[data-testid="stButton"] > button {
    background-color: var(--surface) !important;
    background: var(--surface) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-button) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}

.stButton button p,
button[data-testid="baseButton-secondary"] p,
div[data-testid="stButton"] > button p {
    color: var(--text-primary) !important;
}

.stButton button:hover,
button[data-testid="baseButton-secondary"]:hover,
button[data-testid="baseButton-primary"]:hover,
div[data-testid="stButton"] > button:hover {
    background-color: var(--surface-alt) !important;
    background: var(--surface-alt) !important;
    border-color: var(--air-gold) !important;
    color: #FFFFFF !important;
}

.stButton button:hover p {
    color: #FFFFFF !important;
}

.stButton button:focus,
.stButton button:active {
    box-shadow: none !important;
    outline: none !important;
    border-color: var(--air-gold) !important;
}

/* Chat Messages */
[data-testid="stChatMessage"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-card) !important;
    padding: 12px 16px !important;
    margin-bottom: 10px !important;
    font-size: 14px !important;
    line-height: 1.55 !important;
    color: var(--text-primary) !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    border-left: 3px solid var(--air-red) !important;
    background-color: var(--surface) !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    border-left: 3px solid var(--air-gold) !important;
    background-color: var(--surface-alt) !important;
}

/* Chat Input Bar Fixed at Bottom - Seamless Dark Theme */
[data-testid="stBottom"], [data-testid="stBottom"] > div {
    background-color: var(--background) !important;
    border-top: none !important;
}

[data-testid="stChatInput"] {
    border: 1px solid var(--border) !important;
    background-color: var(--surface) !important;
    border-radius: var(--radius-card) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45) !important;
}

[data-testid="stChatInput"] > div {
    background-color: var(--surface) !important;
    border-color: var(--border) !important;
}

[data-testid="stChatInput"] textarea {
    background-color: transparent !important;
    color: var(--text-primary) !important;
    font-size: 13.5px !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-secondary) !important;
    opacity: 0.7 !important;
}

[data-testid="stChatInput"] button {
    background-color: transparent !important;
    color: var(--air-gold) !important;
    border: none !important;
}

[data-testid="stChatInput"] button:hover {
    background-color: transparent !important;
    color: var(--air-red) !important;
}

/* Sources & Citations */
.fw-citation-card {
    background: #10050A;
    border: 1px solid var(--border);
    border-left: 3px solid var(--air-gold);
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 6px;
    margin-bottom: 6px;
    font-size: 12px;
}

.fw-citation-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;
    color: var(--air-gold);
    margin-bottom: 4px;
}

.fw-citation-pill {
    background: rgba(223, 200, 148, 0.12);
    color: var(--air-gold);
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 600;
    border: 1px solid rgba(223, 200, 148, 0.25);
}

.fw-citation-excerpt {
    color: var(--text-secondary);
    font-size: 11.5px;
    line-height: 1.4;
    font-style: italic;
    background: var(--surface);
    padding: 6px 8px;
    border-radius: 4px;
    border: 1px solid var(--border);
}

.fw-guardrail-notice {
    background: #200E08;
    border: 1px solid #54220E;
    border-left: 3px solid #D97706;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12.5px;
    color: #FCD34D;
    margin-top: 8px;
}

.fw-eval-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 10px;
    color: var(--text-secondary);
    background: var(--surface-alt);
    border: 1px solid var(--border);
    padding: 2px 7px;
    border-radius: 8px;
    margin-top: 6px;
}

[data-testid="stExpander"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

.fw-mini-footer {
    text-align: center;
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 18px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
}
</style>
"""
    else:
        # Light Mode (Air India official design tokens)
        css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

:root {
  --air-red: #B5122B;
  --air-aubergine: #4B1838;
  --air-gold: #B88A55;
  --air-rose-gold: #D9A0A7;
  --background: #FAF8F5;
  --surface: #FFFFFF;
  --surface-alt: #FCFAF8;
  --text-primary: #29252A;
  --text-secondary: #777078;
  --border: #E9E1DC;
  --soft-highlight: #F5E9EB;
  --radius-card: 10px;
  --radius-button: 6px;
  --radius-input: 8px;
}

html, body, [data-testid="stAppViewContainer"], .stApp,
[data-testid="stBottom"], [data-testid="stBottom"] > div,
.stChatFloatingInputContainer, [data-testid="stBottomBlockContainer"] {
    background-color: var(--background) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 5.5rem !important;
    max-width: 960px !important;
}

[data-testid="stHeader"] {
    display: none !important;
}

/* Minimal Header Bar */
.fw-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-card);
    margin-bottom: 14px;
}

.fw-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}

.fw-logo-img {
    height: 48px;
    width: auto;
    object-fit: contain;
}

.fw-title {
    font-family: 'Manrope', sans-serif;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.3px;
    color: var(--air-red);
    line-height: 1.1;
}

.fw-title span {
    color: var(--air-aubergine);
}

.fw-sub {
    font-size: 10px;
    font-weight: 700;
    color: var(--air-gold);
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

.fw-badge {
    background: var(--soft-highlight);
    color: var(--air-red);
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 14px;
    border: 1px solid rgba(181, 18, 43, 0.2);
    display: flex;
    align-items: center;
    gap: 6px;
}

.fw-badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #15803d;
}

/* Welcome Banner */
.fw-welcome {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--air-red);
    border-radius: var(--radius-card);
    padding: 12px 18px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.fw-welcome-text {
    font-size: 13.5px;
    color: var(--text-primary);
    line-height: 1.45;
}

.fw-welcome-text strong {
    color: var(--air-aubergine);
    font-family: 'Manrope', sans-serif;
}

.fw-chips-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--air-aubergine);
    margin-bottom: 8px;
}

/* Streamlit Button Overrides for Light Mode */
.stButton button,
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-primary"],
div[data-testid="stButton"] > button {
    background-color: var(--surface) !important;
    background: var(--surface) !important;
    border-radius: var(--radius-button) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 14px !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    transition: all 0.15s ease !important;
}

.stButton button p,
button[data-testid="baseButton-secondary"] p,
div[data-testid="stButton"] > button p {
    color: var(--text-primary) !important;
}

.stButton button:hover,
button[data-testid="baseButton-secondary"]:hover,
div[data-testid="stButton"] > button:hover {
    border-color: var(--air-red) !important;
    color: var(--air-red) !important;
    background-color: var(--soft-highlight) !important;
    background: var(--soft-highlight) !important;
}

.stButton button:hover p {
    color: var(--air-red) !important;
}

.stButton button:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* Chat Messages */
[data-testid="stChatMessage"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-card) !important;
    padding: 12px 16px !important;
    margin-bottom: 10px !important;
    font-size: 14px !important;
    line-height: 1.55 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    border-left: 3px solid var(--air-red) !important;
    background-color: #FFFFFF !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    border-left: 3px solid var(--air-aubergine) !important;
    background-color: var(--surface-alt) !important;
}

/* Chat Input Bar Fixed at Bottom */
[data-testid="stBottom"], [data-testid="stBottom"] > div {
    background-color: var(--background) !important;
    border-top: none !important;
}

[data-testid="stChatInput"] {
    border: 1px solid var(--border) !important;
    background-color: var(--surface) !important;
    border-radius: var(--radius-card) !important;
    box-shadow: 0 2px 10px rgba(41, 37, 42, 0.05) !important;
}

[data-testid="stChatInput"] > div {
    background-color: var(--surface) !important;
    border-color: var(--border) !important;
}

[data-testid="stChatInput"] textarea {
    background-color: transparent !important;
    color: var(--text-primary) !important;
    font-size: 13.5px !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-secondary) !important;
}

[data-testid="stChatInput"] button {
    background-color: transparent !important;
    color: var(--air-red) !important;
    border: none !important;
}

/* Sources */
.fw-citation-card {
    background: #FAF8F5;
    border: 1px solid var(--border);
    border-left: 3px solid var(--air-gold);
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 6px;
    margin-bottom: 6px;
    font-size: 12px;
}

.fw-citation-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;
    color: var(--air-aubergine);
    margin-bottom: 4px;
}

.fw-citation-pill {
    background: rgba(184, 138, 85, 0.15);
    color: var(--air-aubergine);
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 600;
}

.fw-citation-excerpt {
    color: var(--text-secondary);
    font-size: 11.5px;
    line-height: 1.4;
    font-style: italic;
    background: #FFFFFF;
    padding: 6px 8px;
    border-radius: 4px;
    border: 1px solid #ECE6E1;
}

.fw-guardrail-notice {
    background: #FFF9F3;
    border: 1px solid #FADCB8;
    border-left: 3px solid #D97706;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12.5px;
    color: #92400E;
    margin-top: 8px;
}

.fw-eval-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 10px;
    color: var(--text-secondary);
    background: #F1ECE6;
    padding: 2px 7px;
    border-radius: 8px;
    margin-top: 6px;
}

[data-testid="stExpander"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

.fw-mini-footer {
    text-align: center;
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 18px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
}
</style>
"""
    return css
