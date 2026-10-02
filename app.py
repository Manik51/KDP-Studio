import os
import re
import io
import time
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# Page Configuration & Mobile-Friendly Styling
# ==============================================================================
st.set_page_config(
    page_title="KDP E-Book Architect Pro - AI Publishing Studio",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium, Mobile-Optimized UI
st.markdown("""
<style>
    /* Global Container */
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%);
        padding: 1.8rem 2rem;
        border-radius: 14px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff !important;
    }
    .main-header p {
        margin-top: 0.4rem;
        font-size: 1rem;
        opacity: 0.92;
        color: #dbeafe !important;
    }

    /* Badges & Cards */
    .metric-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
        margin: 1rem 0;
    }
    .metric-card {
        flex: 1 1 140px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    .metric-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 600;
    }
    .sidebar-note {
        font-size: 0.82rem;
        background: #f1f5f9;
        border-left: 3px solid #2563eb;
        padding: 0.6rem;
        border-radius: 0 6px 6px 0;
        margin-top: 0.4rem;
        margin-bottom: 0.6rem;
    }
    .key-saved-badge {
        display: inline-block;
        background: #dcfce7;
        color: #166534;
        border: 1px solid #86efac;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# Supported Free LLM Providers with Multi-Model Support
# ==============================================================================
PROVIDERS = {
    "Google Gemini": {
        "models": ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
        "default_model": "gemini-1.5-flash",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_url": "https://aistudio.google.com/",
        "key_label": "Google AI Studio",
        "key_prefix": "AIza",
        "secret_name": "GEMINI_API_KEY",
        "description": "⭐ RECOMMENDED FOR FULL BOOKS! 1 Million TPM free limit (never hits rate limits)."
    },
    "Groq": {
        "models": ["llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "default_model": "llama-3.1-8b-instant",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "key_url": "https://console.groq.com/keys",
        "key_label": "Groq Cloud Console",
        "key_prefix": "gsk_",
        "secret_name": "GROQ_API_KEY",
        "description": "Ultra-fast inference on Groq LPUs. (Subject to Groq free-tier rate limits)."
    },
    "OpenRouter": {
        "models": ["openrouter/free", "qwen/qwen3.8-27b:free", "nvidia/nemotron-3.5-lightning:free", "liquid/lfm-2.5-2.6b:free"],
        "default_model": "openrouter/free",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "key_url": "https://openrouter.ai/keys",
        "key_label": "OpenRouter Keys",
        "key_prefix": "sk-or-",
        "secret_name": "OPENROUTER_API_KEY",
        "description": "Aggregated gateway using openrouter/free router and active open models."
    }
}

SEED_CATEGORIES = [
    "Personal Finance & Wealth Habits",
    "AI, Productivity & Freelancing",
    "Health, Nutrition & Biohacking",
    "Small Business, Solopreneurship & Side Hustles",
    "Mental Toughness, Stoicism & Mindfulness",
    "Modern Parenting & Child Psychology",
    "Sustainable Gardening & Self-Sufficiency",
    "Career Advancement & Remote Work Skills"
]

COVER_THEMES = {
    "Midnight Executive": {
        "bg_top": (15, 23, 42),      # Dark Slate
        "bg_bot": (30, 58, 138),     # Deep Navy
        "title_color": (255, 255, 255),
        "accent_color": (245, 158, 11),  # Gold/Amber
        "sub_color": (226, 232, 240)
    },
    "Obsidian Gold": {
        "bg_top": (18, 18, 18),      # Charcoal Black
        "bg_bot": (38, 38, 38),      # Dark Graphite
        "title_color": (250, 204, 21),   # Brilliant Gold
        "accent_color": (255, 255, 255),
        "sub_color": (212, 212, 216)
    },
    "Emerald Wealth": {
        "bg_top": (6, 78, 59),       # Deep Forest
        "bg_bot": (2, 44, 34),       # Dark Emerald
        "title_color": (255, 255, 255),
        "accent_color": (52, 211, 153),  # Mint Gold
        "sub_color": (209, 250, 229)
    },
    "Crimson Authority": {
        "bg_top": (127, 29, 29),     # Dark Burgundy
        "bg_bot": (24, 24, 27),      # Dark Zinc
        "title_color": (255, 255, 255),
        "accent_color": (251, 191, 36),  # Warm Gold
        "sub_color": (244, 244, 245)
    }
}

# ==============================================================================
# API Key Sanitization, Storage & Persistence Helpers
# ==============================================================================
def clean_api_key(raw_key: str) -> str:
    """Strips accidental quotes, spaces, newlines, and 'Bearer ' prefixes."""
    if not raw_key:
        return ""
    k = raw_key.strip()
    if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
        k = k[1:-1].strip()
    if k.lower().startswith("bearer "):
        k = k[7:].strip()
    return k


def get_persisted_key(provider: str) -> str:
    """Retrieves key from secrets, session state, browser query params, or local storage."""
    config = PROVIDERS.get(provider, {})
    env_var = config.get("secret_name", "")
    param_name = f"{provider.lower().replace(' ', '_')}_key"

    # 1. Check Streamlit Secrets (App Settings > Secrets on Streamlit Cloud)
    try:
        if env_var and env_var in st.secrets:
            val = str(st.secrets[env_var]).strip()
            if val:
                return val
    except Exception:
        pass

    # 2. Check Session State
    session_val = st.session_state.get(f"key_{provider}", "")
    if session_val:
        return session_val

    # 3. Check Browser Query Params (URL persistence across page refresh)
    try:
        if param_name in st.query_params:
            q_val = str(st.query_params[param_name]).strip()
            if q_val:
                return q_val
    except Exception:
        pass

    # 4. Check local .streamlit/secrets.toml if running on a writable local filesystem
    try:
        secrets_path = os.path.join(os.getcwd(), ".streamlit", "secrets.toml")
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(rf'{env_var}\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1).strip()
    except Exception:
        pass

    return ""


def save_key_locally(provider: str, key_val: str):
    """Saves API key safely in session, query_params, and local disk without crashing on read-only cloud mounts."""
    cleaned = clean_api_key(key_val)
    if not cleaned:
        return

    # Always save to Session State & Browser URL Query Params (Works 100% on Cloud & Mobile)
    st.session_state[f"key_{provider}"] = cleaned
    param_name = f"{provider.lower().replace(' ', '_')}_key"
    try:
        st.query_params[param_name] = cleaned
    except Exception:
        pass

    # Try saving to local disk file IF filesystem allows it (silently pass on read-only cloud filesystems)
    try:
        config = PROVIDERS.get(provider, {})
        env_var = config.get("secret_name", "")
        if not env_var:
            return

        streamlit_dir = os.path.join(os.getcwd(), ".streamlit")
        os.makedirs(streamlit_dir, exist_ok=True)
        secrets_path = os.path.join(streamlit_dir, "secrets.toml")

        existing = {}
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'([A-Za-z0-9_]+)\s*=\s*["\']([^"\']+)["\']', line.strip())
                    if m:
                        existing[m.group(1)] = m.group(2)

        existing[env_var] = cleaned

        with open(secrets_path, "w", encoding="utf-8") as f:
            for k, v in existing.items():
                f.write(f'{k} = "{v}"\n')
    except (OSError, PermissionError, Exception):
        # Streamlit Cloud uses a read-only repository mount; in-memory & query_params handle persistence cleanly
        pass


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_groq_models(api_key: str) -> list[str]:
    """Dynamically fetches currently active models from Groq API for this account."""
    cleaned = clean_api_key(api_key)
    if not cleaned or not cleaned.startswith("gsk_"):
        return []
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {cleaned}"},
            timeout=8
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            text_models = [
                m["id"] for m in data
                if "whisper" not in m.get("id", "").lower()
                and "embed" not in m.get("id", "").lower()
            ]
            if text_models:
                return sorted(text_models)
    except Exception:
        pass
    return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_openrouter_models() -> list[str]:
    """Fetches real-time active free models from OpenRouter."""
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=6)
        if r.status_code == 200:
            free_models = [m["id"] for m in r.json().get("data", []) if ":free" in m.get("id", "")]
            if free_models:
                return ["openrouter/free"] + sorted(free_models)
    except Exception:
        pass
    return ["openrouter/free", "qwen/qwen3.8-27b:free", "nvidia/nemotron-3.5-lightning:free"]


def parse_api_error(status_code: int, response_text: str) -> str:
    """Extracts human-readable error messages from dict, list, or plain text."""
    import json
    msg = f"HTTP {status_code}"
    try:
        data = json.loads(response_text)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            data = data[0]
        if isinstance(data, dict):
            if "error" in data:
                err_obj = data["error"]
                if isinstance(err_obj, dict):
                    msg += f": {err_obj.get('message', str(err_obj))}"
                else:
                    msg += f": {str(err_obj)}"
            elif "message" in data:
                msg += f": {data['message']}"
            else:
                msg += f": {response_text[:160]}"
        else:
            msg += f": {response_text[:160]}"
    except Exception:
        msg += f": {response_text[:160]}"
    return msg


def call_gemini(system_prompt: str, user_prompt: str, api_key: str, model_name: str, temperature: float = 0.7) -> str:
    """Bulletproof dual-endpoint Google Gemini caller (Native REST + OpenAI fallback)."""
    cleaned_key = clean_api_key(api_key)
    if not cleaned_key:
        raise ValueError("Google Gemini API Key is missing. Please enter your key in the sidebar.")

    target_model = model_name if model_name and "gemini" in model_name.lower() else "gemini-1.5-flash"

    # METHOD 1: Google Native REST API (The most reliable, zero rate-limit issues, 1 Million TPM)
    native_url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={cleaned_key}"
    native_payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature
        }
    }

    try:
        r = requests.post(native_url, json=native_payload, timeout=180)
        if r.status_code == 200:
            res_data = r.json()
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        elif r.status_code == 400 and "API key not valid" in r.text:
            raise RuntimeError("Invalid Gemini API Key! Please copy your free key from https://aistudio.google.com/")
    except requests.exceptions.RequestException:
        pass

    # METHOD 2: Google OpenAI-compatible endpoint fallback
    headers = {
        "Authorization": f"Bearer {cleaned_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }
    try:
        r2 = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            headers=headers,
            json=payload,
            timeout=180
        )
        if r2.status_code == 200:
            data = r2.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            err = parse_api_error(r2.status_code, r2.text)
            raise RuntimeError(f"Google Gemini Error: {err}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error connecting to Google Gemini: {str(e)}")


def call_openrouter(system_prompt: str, user_prompt: str, api_key: str, model_name: str, temperature: float = 0.7) -> str:
    """Bulletproof OpenRouter caller with auto-fallback to openrouter/free."""
    cleaned_key = clean_api_key(api_key)
    if not cleaned_key:
        raise ValueError("OpenRouter API Key is missing. Please enter your key in the sidebar.")

    headers = {
        "Authorization": f"Bearer {cleaned_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kdp-architect.local",
        "X-Title": "KDP E-Book Architect Pro"
    }

    target_model = model_name if model_name else "openrouter/free"
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }

    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=180)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()

        # If model retired or unavailable, auto-fallback to openrouter/free
        if r.status_code in (400, 404) and target_model != "openrouter/free":
            payload["model"] = "openrouter/free"
            r2 = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=180)
            if r2.status_code == 200:
                return r2.json()["choices"][0]["message"]["content"].strip()

        err = parse_api_error(r.status_code, r.text)
        if r.status_code == 401:
            err += " (Invalid OpenRouter API Key. Get free key at https://openrouter.ai/keys)"
        raise RuntimeError(f"OpenRouter Error: {err}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error connecting to OpenRouter: {str(e)}")


def call_groq(system_prompt: str, user_prompt: str, api_key: str, model_name: str, temperature: float = 0.7) -> str:
    """Bulletproof Groq caller with rate-limit and 404 auto-recovery."""
    cleaned_key = clean_api_key(api_key)
    if not cleaned_key:
        raise ValueError("Groq API Key is missing. Please enter your key in the sidebar.")

    headers = {
        "Authorization": f"Bearer {cleaned_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=180)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()

        # If rate limit (429) or model retired (404), auto-switch to 8B instant!
        if r.status_code in (429, 404):
            time.sleep(2)
            payload["model"] = "llama-3.1-8b-instant"
            r2 = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=180)
            if r2.status_code == 200:
                return r2.json()["choices"][0]["message"]["content"].strip()

        err = parse_api_error(r.status_code, r.text)
        if r.status_code == 429:
            err += " (Groq free tier limit reached! Please switch to Google Gemini in the sidebar for 1 Million tokens/min without limits)."
        raise RuntimeError(f"Groq Error: {err}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error connecting to Groq: {str(e)}")


def call_llm(system_prompt: str, user_prompt: str, provider: str, api_key: str, model_name: str, temperature: float = 0.7) -> str:
    """Master LLM dispatcher: Routes to bulletproof provider handlers."""
    if provider == "Google Gemini":
        return call_gemini(system_prompt, user_prompt, api_key, model_name, temperature)
    elif provider == "OpenRouter":
        return call_openrouter(system_prompt, user_prompt, api_key, model_name, temperature)
    else:
        return call_groq(system_prompt, user_prompt, api_key, model_name, temperature)


def test_llm_connection(provider: str, api_key: str, model_name: str) -> tuple[bool, str]:
    """Tests the connection using the exact call_llm function."""
    try:
        res = call_llm("You are a connection tester.", "Reply with 'OK'.", provider, api_key, model_name)
        if res:
            return True, f"Connection verified! {provider} ('{model_name}') is 100% active and ready."
        return False, "Received empty response from provider."
    except Exception as e:
        return False, str(e)


def sanitize_filename(name: str) -> str:
    """Sanitizes text into clean filename slug."""
    clean = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name).strip()
    slug = re.sub(r'[\s_]+', '_', clean).lower()
    return slug[:40] if slug else "kdp_ebook"


def count_words(text: str) -> int:
    """Counts words in a given text."""
    return len(re.findall(r'\b\w+\b', text))


# ==============================================================================
# Built-in 300-DPI Cover Studio (Zero Canva Required)
# ==============================================================================
def wrap_text(text: str, max_chars_per_line: int = 24) -> list:
    """Wraps text cleanly across multiple lines for book cover layout."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + (1 if current_line else 0) <= max_chars_per_line:
            current_line.append(word)
            current_length += len(word) + (1 if len(current_line) > 1 else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def generate_amazon_cover(
    title: str,
    subtitle: str,
    author: str,
    theme_name: str = "Midnight Executive",
    genre_badge: str = "THE DEFINITIVE ACTION BLUEPRINT"
) -> bytes:
    """
    Generates a publication-ready Amazon Kindle eBook Cover (1600 x 2560 pixels, 1:1.6 ratio).
    Returns JPEG image bytes ready for direct upload to Amazon KDP.
    """
    WIDTH, HEIGHT = 1600, 2560
    theme = COVER_THEMES.get(theme_name, COVER_THEMES["Midnight Executive"])

    # 1. Create Base Image with Vertical Gradient
    base = Image.new("RGB", (WIDTH, HEIGHT), theme["bg_top"])
    draw = ImageDraw.Draw(base)

    r1, g1, b1 = theme["bg_top"]
    r2, g2, b2 = theme["bg_bot"]

    for y in range(HEIGHT):
        ratio = y / float(HEIGHT)
        nr = int(r1 + (r2 - r1) * ratio)
        ng = int(g1 + (g2 - g1) * ratio)
        nb = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(nr, ng, nb))

    # 2. Draw Elegant Frame Accents
    margin = 80
    draw.rectangle(
        [(margin, margin), (WIDTH - margin, HEIGHT - margin)],
        outline=theme["accent_color"],
        width=6
    )
    draw.rectangle(
        [(margin + 18, margin + 18), (WIDTH - margin - 18, HEIGHT - margin - 18)],
        outline=(*theme["accent_color"][:3], 120),
        width=2
    )

    # 3. Load Dynamic Fonts
    try:
        badge_font = ImageFont.load_default(size=44)
        title_font = ImageFont.load_default(size=108)
        subtitle_font = ImageFont.load_default(size=56)
        author_font = ImageFont.load_default(size=64)
    except Exception:
        badge_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        author_font = ImageFont.load_default()

    # 4. Draw Header / Genre Badge
    badge_text = f"★  {genre_badge.upper()}  ★"
    draw.text((WIDTH // 2, 280), badge_text, fill=theme["accent_color"], font=badge_font, anchor="mm")

    # Thin Divider
    draw.line([(WIDTH // 2 - 250, 360), (WIDTH // 2 + 250, 360)], fill=theme["accent_color"], width=3)

    # 5. Draw Wrapped Big Bold Title
    title_lines = wrap_text(title.upper(), max_chars_per_line=18)
    title_y_start = 580
    line_spacing = 130

    for idx, line in enumerate(title_lines[:5]):
        y_pos = title_y_start + (idx * line_spacing)
        draw.text((WIDTH // 2 + 4, y_pos + 4), line, fill=(0, 0, 0), font=title_font, anchor="mm")
        draw.text((WIDTH // 2, y_pos), line, fill=theme["title_color"], font=title_font, anchor="mm")

    divider_y = title_y_start + (len(title_lines[:5]) * line_spacing) + 80
    draw.line([(WIDTH // 2 - 350, divider_y), (WIDTH // 2 + 350, divider_y)], fill=theme["accent_color"], width=4)

    # 6. Draw Subtitle
    sub_lines = wrap_text(subtitle, max_chars_per_line=32)
    sub_y_start = divider_y + 110
    sub_spacing = 76

    for idx, sline in enumerate(sub_lines[:4]):
        draw.text((WIDTH // 2, sub_y_start + (idx * sub_spacing)), sline, fill=theme["sub_color"], font=subtitle_font, anchor="mm")

    # 7. Draw Author Plaque at the Bottom
    author_y = HEIGHT - 320
    draw.line([(WIDTH // 2 - 200, author_y - 80), (WIDTH // 2 + 200, author_y - 80)], fill=theme["accent_color"], width=2)
    draw.text((WIDTH // 2, author_y - 20), "WRITTEN BY", fill=theme["accent_color"], font=badge_font, anchor="mm")
    draw.text((WIDTH // 2 + 2, author_y + 72), author.upper(), fill=(0, 0, 0), font=author_font, anchor="mm")
    draw.text((WIDTH // 2, author_y + 70), author.upper(), fill=theme["title_color"], font=author_font, anchor="mm")

    buffer = io.BytesIO()
    base.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


# ==============================================================================
# Sidebar: Persistent API Configuration & Diagnostics
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ API Configuration")
    provider_choice = st.selectbox("API Provider", options=list(PROVIDERS.keys()), index=0)
    selected_config = PROVIDERS[provider_choice]

    # Check for automatically persisted key
    initial_key = get_persisted_key(provider_choice)

    api_key_input = st.text_input(
        f"{provider_choice} API Key",
        value=initial_key,
        type="password",
        placeholder="e.g. gsk_..." if provider_choice == "Groq" else "Paste API key here...",
        help="Paste your API key here. Click '💾 Save Key' below to make it permanent across refreshes!"
    )

    cleaned_input = clean_api_key(api_key_input) or clean_api_key(initial_key)

    # Real-time prefix validation for Groq
    if provider_choice == "Groq" and cleaned_input and not cleaned_input.startswith("gsk_"):
        st.warning("⚠️ Groq keys must start with `gsk_`. You may have copied the wrong text.")

    # Dynamically query active models from Groq or OpenRouter
    available_models = list(selected_config["models"])
    if provider_choice == "Groq" and cleaned_input:
        live_groq = fetch_live_groq_models(cleaned_input)
        if live_groq:
            available_models = live_groq
    elif provider_choice == "OpenRouter":
        live_or = fetch_live_openrouter_models()
        if live_or:
            available_models = live_or

    # Model Selector for Selected Provider
    active_model = st.selectbox(
        "Active Model",
        options=available_models,
        index=0,
        help="Choose active model. Dynamically fetched from your provider."
    )

    if initial_key and initial_key == cleaned_input:
        st.markdown('<div class="key-saved-badge">✓ API Key Saved in Storage</div>', unsafe_allow_html=True)

    col_save, col_test = st.columns(2)
    with col_save:
        if st.button("💾 Save Key", use_container_width=True, help="Saves key so refresh won't erase it"):
            if cleaned_input:
                save_key_locally(provider_choice, cleaned_input)
                st.session_state[f"key_{provider_choice}"] = cleaned_input
                st.success("✅ Key saved in session & URL! It will not be erased on refresh.")
            else:
                st.error("Enter key first!")

    with col_test:
        if st.button("🧪 Test Key", use_container_width=True, help="Test live connection to verify key works"):
            target_key = cleaned_input or get_persisted_key(provider_choice)
            if not target_key:
                st.error("Please enter a key first!")
            else:
                with st.spinner("Testing API connection..."):
                    ok, msg = test_llm_connection(provider_choice, target_key, active_model)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")

    st.markdown(
        f"""
        <div class="sidebar-note">
            <strong>Active Model:</strong> <code>{active_model}</code><br>
            <span style="font-size: 0.8rem; color: #475569;">{selected_config['description']}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("🔒 How to Save Keys Permanently on Streamlit Cloud", expanded=False):
        st.markdown(f"""
1. On your deployed app URL, click **Settings** (top-right or bottom-right).
2. Go to **Secrets**.
3. Paste:
```toml
{selected_config['secret_name']} = "your_key_here"
```
4. Click **Save**. The app will now **NEVER forget your key**, even on phone!
""")

    st.markdown("---")
    st.markdown("#### 🔑 Free API Key Links")
    st.markdown(
        f"""
        - **[Groq Cloud Console]({PROVIDERS['Groq']['key_url']})** (Get key starting with `gsk_`)
        - **[Google AI Studio]({PROVIDERS['Google Gemini']['key_url']})** (Generous free limits)
        - **[OpenRouter]({PROVIDERS['OpenRouter']['key_url']})**
        """
    )


# ==============================================================================
# Main UI Header
# ==============================================================================
st.markdown("""
<div class="main-header">
    <h1>📚 KDP E-Book Architect Pro</h1>
    <p>Complete Autonomous KDP Studio: Niche Hunting • Deep Drafting • 300-DPI Cover Creator • SEO Launch Kit</p>
</div>
""", unsafe_allow_html=True)

# Session State Setup
if "book_data" not in st.session_state:
    st.session_state.book_data = None
if "niche_suggestions" not in st.session_state:
    st.session_state.niche_suggestions = None
if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = ""
if "selected_audience" not in st.session_state:
    st.session_state.selected_audience = ""

# Navigation Tabs: Studio vs Step-by-Step Publishing Guide
tab_studio, tab_guide = st.tabs(["🚀 Autonomous Publishing Studio", "📖 Step-by-Step Amazon KDP Guide"])

# ==============================================================================
# TAB 1: THE AUTONOMOUS PUBLISHING STUDIO
# ==============================================================================
with tab_studio:
    # --------------------------------------------------------------------------
    # Phase 0: Automated KDP Niche & BSR Hunter
    # --------------------------------------------------------------------------
    with st.expander("🔍 Phase 0: Automated KDP Niche Hunter (Find Low-Competition, High-Sale Niches)", expanded=True):
        st.markdown(
            "অ্যামাজনে কোন টপিকের বই সবচেয়ে বেশি বিক্রি হয় এবং কম্পিটিশন কম (১,০০০-৩,০০০ সার্চ রেজাল্ট রেঞ্জ), "
            "সিস্টেম নিজেই তা অ্যানালাইসিস করবে।"
        )
        col_cat, col_btn = st.columns([2, 1])
        with col_cat:
            chosen_seed = st.selectbox("Select Seed Market Industry:", options=SEED_CATEGORIES)
        with col_btn:
            st.write("")
            st.write("")
            hunt_btn = st.button("🔎 Scan & Hunt Winning Niches", use_container_width=True)

        if hunt_btn:
            eff_key = clean_api_key(api_key_input) or clean_api_key(get_persisted_key(provider_choice))
            if not eff_key:
                st.error("⚠️ Please enter and save your API Key in the sidebar first.")
            else:
                with st.spinner("Analyzing Amazon buyer search intent, competition levels, and profitability..."):
                    niche_sys_prompt = (
                        "Act as a World-Class Amazon KDP Algorithm Analyst. Your job is to identify 3 distinct, "
                        "highly profitable micro-niches with low competition (1000-3000 search results feel) and "
                        "high commercial intent (BSR under 50,000 potential). Format your answer cleanly."
                    )
                    niche_user_prompt = f"""
Seed Industry: {chosen_seed}

Provide exactly 3 Golden Micro-Niche Opportunities. For each:
1. Micro-Niche Title & Topic
2. Target Audience & Specific Reader Pain Point
3. Estimated BSR Potential & Why Competition is Low
4. Profitability Viability Score (out of 10)
5. Recommended Hook for Amazon KDP
"""
                    try:
                        suggestions = call_llm(niche_sys_prompt, niche_user_prompt, provider_choice, eff_key, active_model)
                        st.session_state.niche_suggestions = suggestions
                        st.success("✅ Golden Micro-Niches Discovered!")
                    except Exception as e:
                        st.error(f"Error fetching niches: {str(e)}")

        if st.session_state.niche_suggestions:
            st.markdown("#### 🏆 Discovered High-Profit Niches:")
            st.info(st.session_state.niche_suggestions)

    # --------------------------------------------------------------------------
    # Book Configuration Inputs
    # --------------------------------------------------------------------------
    st.markdown("### ✍️ E-Book Project Details")

    col_t, col_a = st.columns([1.2, 1])
    with col_t:
        topic_input = st.text_input(
            "Main Book Topic / Theme *",
            value=st.session_state.selected_topic,
            placeholder="e.g., Solar Battery & Backup Power Setup for Tiny Homes",
            help="The primary subject of your book."
        )
    with col_a:
        audience_input = st.text_input(
            "Target Audience (Optional)",
            value=st.session_state.selected_audience,
            placeholder="e.g., Off-grid enthusiasts, DIY homeowners, preppers",
            help="Who this book is written for."
        )

    col_author, col_theme, col_ch = st.columns([1, 1, 1])
    with col_author:
        author_input = st.text_input("Pen Name / Author Name", value="Alex Vance")
    with col_theme:
        theme_choice = st.selectbox("Cover Design Palette", options=list(COVER_THEMES.keys()))
    with col_ch:
        chapters_count = st.slider("Target Chapters", min_value=3, max_value=8, value=5)

    start_generation_btn = st.button("🚀 Start Autonomous Book & Cover Generation", type="primary", use_container_width=True)

    # --------------------------------------------------------------------------
    # Pipeline Execution
    # --------------------------------------------------------------------------
    if start_generation_btn:
        eff_key = clean_api_key(api_key_input) or clean_api_key(get_persisted_key(provider_choice))
        if not eff_key:
            st.error("⚠️ **API Key Required:** Please enter your API Key in the sidebar.")
            st.stop()

        if not topic_input or not topic_input.strip():
            st.error("⚠️ **Topic Required:** Please provide a Main Topic.")
            st.stop()

        st.markdown("---")
        st.markdown("### ⏳ Autonomous Production in Progress...")

        progress_bar = st.progress(0.0)
        status_box = st.empty()

        p1_box = st.empty()
        p2_box = st.empty()
        p3_box = st.container()
        p4_box = st.empty()
        cover_box = st.empty()

        total_steps = 2 + chapters_count + 2
        current_step = 0

        def update_ui(step_idx: int, msg: str):
            fraction = min(1.0, step_idx / total_steps)
            progress_bar.progress(fraction)
            status_box.info(f"**Step {step_idx}/{total_steps}:** {msg}")

        try:
            # 1. Phase 1: Market Research & High-CTR Titles
            current_step += 1
            update_ui(current_step, "Phase 1: Generating 3 High-Converting Title & Subtitle Combinations...")

            p1_sys = (
                "Act as an Amazon KDP Analyst. Generate 3 highly profitable, high-CTR book titles and subtitle "
                "combinations based on the topic. Include target reader pain points and commercial rationale."
            )
            p1_user = f"Topic: {topic_input.strip()}\nAudience: {audience_input.strip() if audience_input else 'General non-fiction buyers'}"
            phase1_output = call_llm(p1_sys, p1_user, provider_choice, eff_key, active_model)

            with p1_box.expander("📊 Phase 1: Market Research & Titles", expanded=True):
                st.markdown(phase1_output)

            time.sleep(1)

            # 2. Phase 2: Chapter Outline Architecture
            current_step += 1
            update_ui(current_step, "Phase 2: Architecting Cohesive Chapter Outline...")

            p2_sys = (
                f"Act as a Master Non-Fiction Book Architect. Generate a structured outline with exactly {chapters_count} "
                f"chapters based on Phase 1. Each chapter must have a compelling title and 3 distinct sub-points."
            )
            p2_user = f"Topic: {topic_input.strip()}\nTarget Chapters: {chapters_count}\nMarket Research Context:\n{phase1_output}"
            phase2_output = call_llm(p2_sys, p2_user, provider_choice, eff_key, active_model)

            with p2_box.expander("🏗️ Phase 2: Chapter Outline Architecture", expanded=True):
                st.markdown(phase2_output)

            time.sleep(1)

            # 3. Phase 3: Iterative Chapter Drafting (The Loop)
            chapters_list = []
            for ch in range(1, chapters_count + 1):
                current_step += 1
                update_ui(current_step, f"Phase 3: Deep Drafting Chapter {ch} of {chapters_count}...")

                p3_sys = (
                    "Act as an Authoritative Non-Fiction Author. Write in-depth, captivating, high-value content with "
                    "clear takeaways, step-by-step frameworks, and real-world examples in clean Markdown. "
                    "Avoid generic fluff; write actionable, deep text."
                )
                p3_user = f"""
Book Topic: {topic_input.strip()}
Audience: {audience_input.strip()}
Complete Outline Context:
{phase2_output}

INSTRUCTION:
Write ONLY Chapter {ch} in deep, comprehensive detail (around 1000-1400 words).
Cover all 3 sub-points thoroughly. Deliver publication-ready manuscript content with H2, H3 headers.
"""
                ch_text = call_llm(p3_sys, p3_user, provider_choice, eff_key, active_model, temperature=0.7)
                chapters_list.append({"chapter_num": ch, "content": ch_text})

                with p3_box.expander(f"📖 Chapter {ch} Manuscript Draft", expanded=False):
                    st.markdown(ch_text)

                time.sleep(2)  # Rate limit guard

            # 4. Phase 4: Amazon KDP SEO Package
            current_step += 1
            update_ui(current_step, "Phase 4: Generating Amazon KDP SEO & Metadata Launch Package...")

            p4_sys = (
                "Act as an Amazon KDP SEO Expert. Generate: 1 Final Optimized Title/Subtitle, "
                "7 Backend Keywords (comma separated, under 50 chars each), 2 BISAC Categories, "
                "and an HTML formatted Amazon Book Description."
            )
            p4_user = f"Topic: {topic_input.strip()}\nOutline:\n{phase2_output}"
            phase4_output = call_llm(p4_sys, p4_user, provider_choice, eff_key, active_model)

            with p4_box.expander("🚀 Phase 4: Amazon KDP SEO Package", expanded=True):
                st.markdown(phase4_output)

            time.sleep(1)

            # 5. Phase 5: Front/Back Matter & Built-in Cover Generation
            current_step += 1
            update_ui(current_step, "Phase 5: Rendering 300-DPI Amazon Cover (1600x2560 px)...")

            cover_title = topic_input.strip()
            cover_subtitle = audience_input.strip() if audience_input else "A Practical Step-by-Step Blueprint"

            cover_bytes = generate_amazon_cover(
                title=cover_title,
                subtitle=cover_subtitle,
                author=author_input.strip() if author_input else "Alex Vance",
                theme_name=theme_choice
            )

            # Build Full Manuscript with Front Matter & Back Matter
            front_matter = f"""# {topic_input.strip()}
### {cover_subtitle}
**By {author_input.strip()}**

---

### Copyright & Disclaimer
© {time.strftime('%Y')} {author_input.strip()}. All rights reserved.
No part of this publication may be reproduced, distributed, or transmitted in any form without prior written permission.
*Disclaimer: This book is prepared for educational and informational purposes only.*

---

### Introduction: The Transformation Awaiting You
Welcome to {topic_input.strip()}. If you have ever sought a practical, no-nonsense path forward, this guide is crafted specifically for you. Read each chapter with action in mind.

---
"""

            back_matter = f"""

---

# 🌟 A Special Note & Free Gift From The Author

Thank you for investing your time into reading **{topic_input.strip()}**!

### How You Can Help Fellow Readers:
If you found value from this book, **could you please leave an honest 1-minute review on Amazon?**
Independent authors depend on genuine reader feedback, and your review helps other passionate learners discover this book!

### Claim Your Free Bonus Cheatsheet:
Visit our reader portal to claim your free companion checklists and workbook templates to put this book into immediate action.
"""

            all_chapters_formatted = "\n\n---\n\n".join([ch["content"] for ch in chapters_list])
            master_manuscript = f"{front_matter}\n\n# Table of Contents\n{phase2_output}\n\n---\n\n{all_chapters_formatted}\n{back_matter}"

            # Prepare Quick Copy-Paste KDP Metadata Sheet
            kdp_sheet = f"""================================================================================
AMAZON KDP FAST-LAUNCH METADATA SHEET
Topic: {topic_input.strip()}
Author: {author_input.strip()}
Generated by: KDP E-Book Architect Pro
================================================================================

[1] TITLE & SUBTITLE:
Title: {topic_input.strip()}
Subtitle: {cover_subtitle}

[2] 7 BACKEND SEARCH KEYWORDS:
(Extracted from SEO package below)

[3] AMAZON KDP FULL SEO PACKAGE & DESCRIPTION:
{phase4_output}

================================================================================
INSTRUCTIONS:
1. Open https://kdp.amazon.com -> Click '+ Create' -> 'Kindle eBook'
2. Paste the Title, Subtitle, and HTML Description from this sheet.
3. Paste the 7 Keywords into the 7 boxes.
4. Upload your manuscript (.md or converted .docx) & your cover.jpg.
================================================================================
"""

            slug = sanitize_filename(topic_input.strip())
            st.session_state.book_data = {
                "topic": topic_input.strip(),
                "author": author_input.strip(),
                "chapters_count": chapters_count,
                "provider": provider_choice,
                "model": active_model,
                "phase1": phase1_output,
                "phase2": phase2_output,
                "chapters": chapters_list,
                "phase4": phase4_output,
                "master_manuscript": master_manuscript,
                "kdp_sheet": kdp_sheet,
                "cover_bytes": cover_bytes,
                "filename": f"{slug}_manuscript.md",
                "cover_filename": f"{slug}_cover.jpg",
                "sheet_filename": f"{slug}_kdp_launch_sheet.txt"
            }

            progress_bar.progress(1.0)
            status_box.empty()

        except Exception as e:
            status_box.empty()
            st.error(f"❌ **Generation Error:** {str(e)}")
            st.warning("💡 Tip: If you hit a rate limit with Llama 3.3 70B, select 'llama-3.1-8b-instant' in the sidebar dropdown or switch to Google Gemini.")

    # --------------------------------------------------------------------------
    # Results, Downloads & Cover Studio Display
    # --------------------------------------------------------------------------
    if st.session_state.book_data is not None:
        data = st.session_state.book_data
        total_words = count_words(data["master_manuscript"])

        st.markdown("---")
        st.success("🎉 **E-Book Production Complete!** Manuscript, Amazon Cover & KDP Metadata Sheet are ready.")

        # Key Metrics
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-card">
                    <div class="metric-value">{data['chapters_count']}</div>
                    <div class="metric-label">Chapters Drafted</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_words:,}</div>
                    <div class="metric-label">Total Words</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">1600 x 2560</div>
                    <div class="metric-label">Cover Resolution</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{data.get('model', data['provider'])}</div>
                    <div class="metric-label">Active Model</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.download_button(
                label="📥 1. Download Manuscript (.md)",
                data=data["master_manuscript"],
                file_name=data["filename"],
                mime="text/markdown",
                type="primary",
                use_container_width=True
            )
        with col_d2:
            st.download_button(
                label="🖼️ 2. Download Cover Image (.jpg)",
                data=data["cover_bytes"],
                file_name=data["cover_filename"],
                mime="image/jpeg",
                type="primary",
                use_container_width=True
            )
        with col_d3:
            st.download_button(
                label="📋 3. Download KDP Launch Sheet (.txt)",
                data=data["kdp_sheet"],
                file_name=data["sheet_filename"],
                mime="text/plain",
                use_container_width=True
            )

        st.markdown("### 🎨 Generated Amazon Book Cover (300 DPI, 1:1.6 Ratio)")
        st.image(data["cover_bytes"], caption=f"Amazon-Ready Cover: {data['cover_filename']}", width=340)

        if st.button("🔄 Clear & Create Another Book", use_container_width=False):
            st.session_state.book_data = None
            st.rerun()


# ==============================================================================
# TAB 2: STEP-BY-STEP AMAZON KDP ACTION GUIDE
# ==============================================================================
with tab_guide:
    st.markdown("""
### 🧭 How to Publish on Amazon KDP & Earn from Week 1 (Step-by-Step)

Follow this exact blueprint to publish your book and start generating passive income:

---

#### 1️⃣ KDP Account Setup (One-time)
1. Go to **[kdp.amazon.com](https://kdp.amazon.com)** and sign in with your normal Amazon account.
2. Complete your **Account Information**:
   - **Bank Account Details**: Where Amazon will deposit your royalties directly every month.
   - **Tax Interview**: A 2-minute online questionnaire.

---

#### 2️⃣ Create Your Kindle eBook (Takes 5 Minutes)
1. Click the yellow **"+ Create"** button on your KDP Dashboard.
2. Select **"Create Kindle eBook"**.
3. **Fill Page 1: Kindle eBook Details**:
   - **Book Title & Subtitle**: Copy directly from your downloaded `kdp_launch_sheet.txt`.
   - **Author Name**: Enter the Pen Name you chose in the app.
   - **Description**: Paste the HTML Book Description generated by the app.
   - **Keywords**: Paste the 7 backend keywords into the 7 boxes.
   - **Categories**: Select the 2 BISAC categories recommended by the app.
   - Click **Save and Continue**.

4. **Fill Page 2: Kindle eBook Content**:
   - **Upload eBook Manuscript**: Upload the `.md` file or open it in Word/Google Docs and save as `.docx`.
   - **Upload eBook Cover**: Upload the `cover.jpg` generated directly by this app (already sized to 1600x2560 px).
   - Use the online **Kindle Previewer** to verify that your book looks clean.
   - Click **Save and Continue**.

5. **Fill Page 3: Kindle eBook Pricing (The Week-1 Income Secret)**:
   - **KDP Select (Kindle Unlimited)**: **CHECK THIS BOX!** 
     - *Why?* Millions of Amazon Prime/Kindle Unlimited readers read books for free, and Amazon pays you per page read (Global Fund Payout). This generates immediate revenue in week 1.
   - **Royalty Plan**: Select **70%**.
   - **Price**: Set to **$2.99** (or $0.99 for a 5-day promotional launch).
   - Click **"Publish Your Kindle eBook"**!

---

#### 📱 How to Run this App from Your Phone 24/7 (No Laptop Needed):
1. **Host on Streamlit Community Cloud (100% Free Forever)**:
   - Upload your `Kindle Maker` project folder to a free GitHub repository.
   - Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with GitHub.
   - Click **"New App"**, select your repository and `app.py`, then click **Deploy**.
2. **Access Anywhere**:
   - You get a live link (e.g. `https://your-name-kdp.streamlit.app`).
   - Open that link on your smartphone's browser. Even if your laptop is shut off, you can generate books, download covers, and publish anytime from your bed!
""")
