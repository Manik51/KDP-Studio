import os
import re
import io
import time
import urllib.parse
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# Optional docx support for native Word manuscripts
try:
    import docx
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ==============================================================================
# Page Configuration & Mobile-Friendly Styling
# ==============================================================================
st.set_page_config(
    page_title="KDP E-Book Architect Pro - Autonomous Bestseller Studio",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Elite SaaS UI
st.markdown("""
<style>
    /* Global Container */
    .main-header {
        background: linear-gradient(135deg, #090d16 0%, #1e293b 40%, #1e3a8a 75%, #2563eb 100%);
        padding: 1.8rem 2rem;
        border-radius: 14px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff !important;
    }
    .main-header p {
        margin-top: 0.4rem;
        font-size: 1.05rem;
        opacity: 0.92;
        color: #dbeafe !important;
    }

    /* Badges & Metrics */
    .metric-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
        margin: 1.2rem 0;
    }
    .metric-card {
        flex: 1 1 150px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.9rem 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 800;
        color: #1e3a8a;
    }
    .metric-label {
        font-size: 0.72rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-top: 2px;
    }

    /* Niche Opportunity Card */
    .niche-card {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 5px solid #2563eb;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .niche-badge {
        display: inline-block;
        background: #dbeafe;
        color: #1e40af;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        margin-bottom: 0.5rem;
    }

    /* Amazon Product Simulator Card */
    .amazon-sim-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.5rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        margin: 1.5rem 0;
    }
    .amazon-price-tag {
        font-size: 1.6rem;
        font-weight: 800;
        color: #b12704;
    }
    .amazon-star-badge {
        color: #ffa41c;
        font-size: 1.1rem;
        font-weight: 700;
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
        "models": ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"],
        "default_model": "gemini-3.8-flash",
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
    "Personal Finance, Investing & Passive Wealth Habits",
    "AI Tools, Automation & High-Income Freelancing",
    "Small Business, Solopreneurship & Micro-SaaS",
    "Health, Nutrition, Fasting & Biohacking",
    "Mental Toughness, Stoicism & Unshakable Focus",
    "Modern Parenting, Child Psychology & ADHD Support",
    "Self-Sufficiency, Solar Power & Off-Grid Living",
    "Career Acceleration, Remote Leadership & Tech Skills"
]

COVER_THEMES = {
    "Midnight Executive": {
        "bg_top": (15, 23, 42),       # Dark Slate
        "bg_bot": (30, 58, 138),      # Deep Navy
        "title_color": (255, 255, 255),
        "accent_color": (245, 158, 11),  # Gold/Amber
        "sub_color": (226, 232, 240)
    },
    "Obsidian Gold": {
        "bg_top": (18, 18, 18),       # Charcoal Black
        "bg_bot": (38, 38, 38),       # Dark Graphite
        "title_color": (250, 204, 21),   # Brilliant 24K Gold
        "accent_color": (255, 255, 255),
        "sub_color": (212, 212, 216)
    },
    "Emerald Wealth": {
        "bg_top": (6, 78, 59),        # Deep Forest
        "bg_bot": (2, 44, 34),        # Dark Emerald
        "title_color": (255, 255, 255),
        "accent_color": (52, 211, 153),  # Mint Gold
        "sub_color": (209, 250, 229)
    },
    "Crimson Authority": {
        "bg_top": (127, 29, 29),      # Dark Burgundy
        "bg_bot": (24, 24, 27),       # Dark Zinc
        "title_color": (255, 255, 255),
        "accent_color": (251, 191, 36),  # Warm Gold
        "sub_color": (244, 244, 245)
    },
    "Nordic Minimalist": {
        "bg_top": (244, 241, 234),    # Warm Sand / Oat
        "bg_bot": (228, 222, 210),    # Soft Bone Cream
        "title_color": (15, 23, 42),     # Slate Black
        "accent_color": (180, 83, 9),    # Warm Cinnamon
        "sub_color": (51, 65, 85)        # Muted Charcoal
    },
    "Cyberpunk Tech & AI": {
        "bg_top": (10, 10, 20),       # Pitch Black
        "bg_bot": (49, 10, 102),      # Deep Electric Violet
        "title_color": (255, 255, 255),
        "accent_color": (34, 211, 238),  # Electric Neon Cyan
        "sub_color": (221, 214, 254)     # Soft Lavender
    },
    "Sapphire Prestige": {
        "bg_top": (15, 23, 68),       # Deep Royal Navy
        "bg_bot": (30, 27, 75),       # Deep Indigo
        "title_color": (255, 255, 255),
        "accent_color": (148, 163, 184), # Platinum Silver
        "sub_color": (226, 232, 240)
    },
    "Sunset Terracotta": {
        "bg_top": (154, 52, 18),      # Deep Terracotta
        "bg_bot": (67, 20, 7),        # Dark Sienna
        "title_color": (255, 255, 255),
        "accent_color": (253, 186, 116), # Desert Peach
        "sub_color": (254, 243, 199)     # Warm Ivory
    }
}

# ==============================================================================
# AI Colorful Image Generator (Pollinations.ai Free Engine)
# ==============================================================================
def fetch_ai_image(prompt: str, width: int = 1024, height: int = 640) -> bytes:
    """Fetches high-quality AI generated color illustration without requiring any paid API key."""
    try:
        clean_p = urllib.parse.quote(prompt.strip()[:180])
        url = f"https://image.pollinations.ai/prompt/{clean_p}?width={width}&height={height}&nologo=true&seed=42"
        r = requests.get(url, timeout=22)
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content
    except Exception:
        pass

    # Reliable fallback: Generate an artistic graphic placeholder with Pillow
    img = Image.new("RGB", (width, height), (30, 58, 138))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(245, 158, 11), width=4)
    try:
        f = ImageFont.load_default(size=36)
    except Exception:
        f = ImageFont.load_default()
    draw.text((width // 2, height // 2), prompt[:40], fill=(255, 255, 255), font=f, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


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

    try:
        if env_var and env_var in st.secrets:
            val = str(st.secrets[env_var]).strip()
            if val:
                return val
    except Exception:
        pass

    session_val = st.session_state.get(f"key_{provider}", "")
    if session_val:
        return session_val

    try:
        if param_name in st.query_params:
            q_val = str(st.query_params[param_name]).strip()
            if q_val:
                return q_val
    except Exception:
        pass

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

    st.session_state[f"key_{provider}"] = cleaned
    param_name = f"{provider.lower().replace(' ', '_')}_key"
    try:
        st.query_params[param_name] = cleaned
    except Exception:
        pass

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
        pass


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_gemini_models(api_key: str) -> list[str]:
    """Dynamically fetches active models available for this user's Google AI Studio key."""
    cleaned = clean_api_key(api_key)
    if not cleaned:
        return ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
    try:
        r = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={cleaned}",
            headers={"x-goog-api-key": cleaned},
            timeout=8
        )
        if r.status_code == 200:
            models_data = r.json().get("models", [])
            valid_models = []
            deprecated_tokens = ["gemini-1.", "gemini-2.0", "pro-latest", "pro-vision", "1.0", "embed", "aqa", "imagen"]
            for m in models_data:
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods and "gemini" in name.lower():
                    if not any(t in name.lower() for t in deprecated_tokens):
                        valid_models.append(name)
            if valid_models:
                preferred = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
                sorted_models = [p for p in preferred if p in valid_models]
                for m in valid_models:
                    if m not in sorted_models and "pro" not in m:
                        sorted_models.append(m)
                for m in valid_models:
                    if m not in sorted_models:
                        sorted_models.append(m)
                if sorted_models:
                    return sorted_models
    except Exception:
        pass
    return ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]


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
    """Bulletproof dual-endpoint Google Gemini caller with automatic 2026 model fallback."""
    cleaned_key = clean_api_key(api_key)
    if not cleaned_key:
        raise ValueError("Google Gemini API Key is missing. Please enter your key in the sidebar.")

    target_model = model_name if model_name and "gemini" in model_name.lower() else "gemini-3.8-flash"

    # If target_model is known deprecated/retired or has given 404, immediately swap to gemini-3.8-flash
    if any(t in target_model.lower() for t in ["1.5", "2.0", "pro-latest", "pro-vision", "1.0"]):
        target_model = "gemini-3.8-flash"

    candidates = [target_model]
    for fallback in ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]:
        if fallback not in candidates:
            candidates.append(fallback)

    last_error = ""

    for current_model in candidates:
        # METHOD 1: Google Native REST API (Zero rate limits, 1 Million TPM free limit)
        native_url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={cleaned_key}"
        native_headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": cleaned_key
        }
        native_payload = {
            "contents": [
                {
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature
            }
        }
        if system_prompt and system_prompt.strip():
            native_payload["systemInstruction"] = {
                "parts": [{"text": system_prompt.strip()}]
            }

        try:
            r = requests.post(native_url, headers=native_headers, json=native_payload, timeout=180)
            if r.status_code == 200:
                res_data = r.json()
                items = res_data.get("candidates", [])
                if items:
                    parts = items[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
            elif r.status_code == 400:
                if "API key not valid" in r.text or "API_KEY_INVALID" in r.text:
                    raise RuntimeError("Invalid Gemini API Key! Please copy your free key from https://aistudio.google.com/")
                last_error = parse_api_error(r.status_code, r.text)
            elif r.status_code in (404, 429, 500, 503):
                last_error = parse_api_error(r.status_code, r.text)
                continue
            else:
                last_error = parse_api_error(r.status_code, r.text)
        except requests.exceptions.RequestException as e:
            last_error = str(e)

        # METHOD 2: Google OpenAI-compatible endpoint fallback for current_model
        headers = {
            "Authorization": f"Bearer {cleaned_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": current_model,
            "messages": messages,
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
            elif r2.status_code in (404, 429, 500, 503):
                last_error = parse_api_error(r2.status_code, r2.text)
                continue
            else:
                last_error = parse_api_error(r2.status_code, r2.text)
        except requests.exceptions.RequestException as e:
            last_error = str(e)

    raise RuntimeError(f"Google Gemini Error: {last_error or 'All Gemini model candidates failed. Please verify your API key at https://aistudio.google.com/'}")


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
            return True, f"Connection verified! {provider} is 100% active and ready."
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
# Built-in 300-DPI Cover Studio (Studio Grade - Dual JPG & PDF Export)
# ==============================================================================
def wrap_text(text: str, max_chars_per_line: int = 22) -> list:
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


def generate_amazon_cover_both(
    title: str,
    subtitle: str,
    author: str,
    theme_name: str = "Midnight Executive",
    genre_badge: str = "THE DEFINITIVE ACTION BLUEPRINT",
    bg_art_bytes: bytes = None
) -> tuple[bytes, bytes]:
    """
    Generates a publication-ready Amazon Kindle eBook Cover (1600 x 2560 pixels, 1:1.6 ratio).
    Returns (JPEG_bytes, PDF_bytes) ready for Amazon KDP eBook and print upload.
    """
    WIDTH, HEIGHT = 1600, 2560
    theme = COVER_THEMES.get(theme_name, COVER_THEMES["Midnight Executive"])

    # 1. Create Base Image with AI Background Artwork OR Vertical Gradient
    if bg_art_bytes:
        try:
            art_img = Image.open(io.BytesIO(bg_art_bytes)).convert("RGB")
            base = art_img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            # Add dark overlay to ensure high text contrast
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 140))
            base.paste(overlay, (0, 0), overlay)
            draw = ImageDraw.Draw(base)
        except Exception:
            base = Image.new("RGB", (WIDTH, HEIGHT), theme["bg_top"])
            draw = ImageDraw.Draw(base)
            r1, g1, b1 = theme["bg_top"]
            r2, g2, b2 = theme["bg_bot"]
            for y in range(HEIGHT):
                ratio = y / float(HEIGHT)
                draw.line([(0, y), (WIDTH, y)], fill=(int(r1+(r2-r1)*ratio), int(g1+(g2-g1)*ratio), int(b1+(b2-b1)*ratio)))
    else:
        base = Image.new("RGB", (WIDTH, HEIGHT), theme["bg_top"])
        draw = ImageDraw.Draw(base)
        r1, g1, b1 = theme["bg_top"]
        r2, g2, b2 = theme["bg_bot"]
        for y in range(HEIGHT):
            ratio = y / float(HEIGHT)
            draw.line([(0, y), (WIDTH, y)], fill=(int(r1+(r2-r1)*ratio), int(g1+(g2-g1)*ratio), int(b1+(b2-b1)*ratio)))

    # 2. Draw Elegant Double Frame & Corner Brackets
    margin = 80
    draw.rectangle(
        [(margin, margin), (WIDTH - margin, HEIGHT - margin)],
        outline=theme["accent_color"],
        width=6
    )
    draw.rectangle(
        [(margin + 18, margin + 18), (WIDTH - margin - 18, HEIGHT - margin - 18)],
        outline=theme["accent_color"],
        width=2
    )

    # Regal Corner Bracket Notches
    c_len = 60
    for cx, cy, dx, dy in [
        (margin, margin, 1, 1),
        (WIDTH - margin, margin, -1, 1),
        (margin, HEIGHT - margin, 1, -1),
        (WIDTH - margin, HEIGHT - margin, -1, -1)
    ]:
        draw.line([(cx, cy), (cx + (dx * c_len), cy)], fill=theme["accent_color"], width=8)
        draw.line([(cx, cy), (cx, cy + (dy * c_len))], fill=theme["accent_color"], width=8)

    # 3. Load Dynamic Fonts
    try:
        badge_font = ImageFont.load_default(size=44)
        title_font = ImageFont.load_default(size=108)
        subtitle_font = ImageFont.load_default(size=56)
        star_font = ImageFont.load_default(size=40)
        author_font = ImageFont.load_default(size=64)
    except Exception:
        badge_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        star_font = ImageFont.load_default()
        author_font = ImageFont.load_default()

    # 4. Header Badge / Category Ribbon
    badge_text = f"★  {genre_badge.upper()}  ★"
    draw.text((WIDTH // 2, 280), badge_text, fill=theme["accent_color"], font=badge_font, anchor="mm")

    # Thin Divider
    draw.line([(WIDTH // 2 - 280, 360), (WIDTH // 2 + 280, 360)], fill=theme["accent_color"], width=3)

    # 5. Wrapped Bold Title with High-Contrast Drop Shadow
    title_lines = wrap_text(title.upper(), max_chars_per_line=18)
    title_y_start = 580
    line_spacing = 132

    for idx, line in enumerate(title_lines[:5]):
        y_pos = title_y_start + (idx * line_spacing)
        shadow_color = (0, 0, 0) if theme["title_color"][0] > 120 else (210, 210, 210)
        draw.text((WIDTH // 2 + 4, y_pos + 4), line, fill=shadow_color, font=title_font, anchor="mm")
        draw.text((WIDTH // 2, y_pos), line, fill=theme["title_color"], font=title_font, anchor="mm")

    divider_y = title_y_start + (len(title_lines[:5]) * line_spacing) + 80
    draw.line([(WIDTH // 2 - 360, divider_y), (WIDTH // 2 + 360, divider_y)], fill=theme["accent_color"], width=4)

    # 6. Subtitle
    sub_lines = wrap_text(subtitle, max_chars_per_line=32)
    sub_y_start = divider_y + 105
    sub_spacing = 74

    for idx, sline in enumerate(sub_lines[:4]):
        draw.text((WIDTH // 2, sub_y_start + (idx * sub_spacing)), sline, fill=theme["sub_color"], font=subtitle_font, anchor="mm")

    # Star Rating Visual Ribbon
    star_y = sub_y_start + (len(sub_lines[:4]) * sub_spacing) + 70
    draw.text((WIDTH // 2, star_y), "★★★★★  AN ACTION-ORIENTED BESTSELLER  ★★★★★", fill=theme["accent_color"], font=star_font, anchor="mm")

    # 7. Author Plaque at the Bottom
    author_y = HEIGHT - 320
    draw.line([(WIDTH // 2 - 240, author_y - 80), (WIDTH // 2 + 240, author_y - 80)], fill=theme["accent_color"], width=3)
    draw.text((WIDTH // 2, author_y - 20), "WRITTEN BY", fill=theme["accent_color"], font=badge_font, anchor="mm")
    draw.text((WIDTH // 2 + 3, author_y + 73), author.upper(), fill=(0, 0, 0) if theme["title_color"][0] > 120 else (210, 210, 210), font=author_font, anchor="mm")
    draw.text((WIDTH // 2, author_y + 70), author.upper(), fill=theme["title_color"], font=author_font, anchor="mm")

    # JPEG Output (Kindle eBook)
    buf_jpg = io.BytesIO()
    base.save(buf_jpg, format="JPEG", quality=95)

    # PDF Output (Print-Ready)
    buf_pdf = io.BytesIO()
    base.save(buf_pdf, format="PDF", resolution=300.0)

    return buf_jpg.getvalue(), buf_pdf.getvalue()


def generate_paperback_wraparound(
    title: str,
    subtitle: str,
    author: str,
    blurb: str,
    theme_name: str = "Midnight Executive",
    chapters_count: int = 5
) -> bytes:
    """Generates complete print-ready PDF containing [Back Cover | Spine | Front Cover] for Amazon KDP Paperback."""
    spine_w = max(240, min(400, chapters_count * 50))
    front_w = 1600
    h = 2560
    total_w = front_w + spine_w + front_w
    theme = COVER_THEMES.get(theme_name, COVER_THEMES["Midnight Executive"])

    base = Image.new("RGB", (total_w, h), theme["bg_top"])
    draw = ImageDraw.Draw(base)

    # Background gradient across entire cover
    r1, g1, b1 = theme["bg_top"]
    r2, g2, b2 = theme["bg_bot"]
    for y in range(h):
        ratio = y / float(h)
        draw.line([(0, y), (total_w, y)], fill=(int(r1+(r2-r1)*ratio), int(g1+(g2-g1)*ratio), int(b1+(b2-b1)*ratio)))

    # Spine lines
    spine_x1 = front_w
    spine_x2 = front_w + spine_w
    draw.line([(spine_x1, 0), (spine_x1, h)], fill=theme["accent_color"], width=4)
    draw.line([(spine_x2, 0), (spine_x2, h)], fill=theme["accent_color"], width=4)

    # Fonts
    try:
        title_font = ImageFont.load_default(size=72)
        blurb_font = ImageFont.load_default(size=44)
        spine_font = ImageFont.load_default(size=40)
    except Exception:
        title_font = ImageFont.load_default()
        blurb_font = ImageFont.load_default()
        spine_font = ImageFont.load_default()

    # Back cover content (Left pane: 0 to front_w)
    draw.text((front_w // 2, 300), "WHAT THIS BOOK DELIVERS", fill=theme["accent_color"], font=blurb_font, anchor="mm")
    draw.line([(front_w // 2 - 200, 360), (front_w // 2 + 200, 360)], fill=theme["accent_color"], width=3)

    blurb_lines = wrap_text(blurb if blurb else "A comprehensive, practical roadmap to mastering the core skills and transforming your future.", max_chars_per_line=30)
    for idx, bl in enumerate(blurb_lines[:12]):
        draw.text((front_w // 2, 480 + (idx * 64)), bl, fill=theme["sub_color"], font=blurb_font, anchor="mm")

    # Front cover content (Right pane: spine_x2 to total_w)
    front_center_x = spine_x2 + (front_w // 2)
    draw.text((front_center_x, 300), "★  ACTION-ORIENTED BESTSELLER  ★", fill=theme["accent_color"], font=blurb_font, anchor="mm")
    f_title_lines = wrap_text(title.upper(), max_chars_per_line=18)
    for idx, fl in enumerate(f_title_lines[:5]):
        draw.text((front_center_x, 600 + (idx * 110)), fl, fill=theme["title_color"], font=title_font, anchor="mm")

    draw.text((front_center_x, h - 300), f"BY {author.upper()}", fill=theme["title_color"], font=blurb_font, anchor="mm")

    # Spine text (Center pane)
    draw.text((spine_x1 + (spine_w // 2), h // 2), f"{title[:24].upper()}  •  {author.upper()}", fill=theme["title_color"], font=spine_font, anchor="mm")

    buf = io.BytesIO()
    base.save(buf, format="PDF", resolution=300.0)
    return buf.getvalue()


# ==============================================================================
# Native Word (.docx) Manuscript Generator with Embedded Color Illustrations
# ==============================================================================
def create_docx_manuscript(
    title: str,
    subtitle: str,
    author: str,
    phase2_outline: str,
    chapters_list: list
) -> bytes:
    """Generates an Amazon KDP-compliant Microsoft Word (.docx) document with embedded high-res color images."""
    if not HAS_DOCX:
        return b""

    doc = docx.Document()

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Georgia'
    normal_style.font.size = Pt(11)

    # 1. Title Page
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(72)
    title_p.paragraph_format.space_after = Pt(18)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = title_p.add_run(title.upper())
    run_t.font.name = 'Georgia'
    run_t.font.size = Pt(28)
    run_t.bold = True
    run_t.font.color.rgb = RGBColor(15, 23, 42)

    if subtitle:
        sub_p = doc.add_paragraph()
        sub_p.paragraph_format.space_after = Pt(36)
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_s = sub_p.add_run(subtitle)
        run_s.font.name = 'Georgia'
        run_s.font.size = Pt(14)
        run_s.italic = True
        run_s.font.color.rgb = RGBColor(71, 85, 105)

    auth_p = doc.add_paragraph()
    auth_p.paragraph_format.space_before = Pt(72)
    auth_p.paragraph_format.space_after = Pt(24)
    auth_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_a = auth_p.add_run(f"BY {author.upper()}")
    run_a.font.name = 'Georgia'
    run_a.font.size = Pt(13)
    run_a.bold = True

    doc.add_page_break()

    # 2. Copyright & Disclaimer
    doc.add_heading("Copyright & Legal Disclaimer", level=2)
    copy_p = doc.add_paragraph()
    copy_p.add_run(f"© {time.strftime('%Y')} {author}. All rights reserved.\n\n")
    copy_p.add_run(
        "No part of this publication may be reproduced, distributed, or transmitted in any form "
        "or by any means, including photocopying, recording, or other electronic or mechanical methods, "
        "without the prior written permission of the publisher.\n\n"
        "Disclaimer: This publication is designed to provide competent and reliable information regarding "
        "the subject matter covered. It is sold with the understanding that the author and publisher are "
        "not engaged in rendering legal, financial, or medical advice. Reader discretion and independent "
        "verification are strongly advised."
    )
    doc.add_page_break()

    # 3. Table of Contents
    doc.add_heading("Table of Contents", level=1)
    for line in phase2_outline.split("\n"):
        line_clean = line.strip()
        if line_clean:
            doc.add_paragraph(line_clean)
    doc.add_page_break()

    # 4. Introduction
    doc.add_heading("Introduction: The Transformation Awaiting You", level=1)
    intro_p = doc.add_paragraph()
    intro_p.add_run(
        f"Welcome to {title}. If you have ever felt overwhelmed by generic information, "
        "this action blueprint was crafted to cut through the noise and give you a structured, "
        "reliable system. Take notes, execute the action checklists, and build your results step by step."
    )
    doc.add_page_break()

    # 5. Chapters with Embedded Color Images
    for ch in chapters_list:
        ch_text = ch.get("content", "")
        img_bytes = ch.get("image_bytes")

        # Embed Chapter Illustration if present
        if img_bytes:
            try:
                img_stream = io.BytesIO(img_bytes)
                doc.add_picture(img_stream, width=docx.shared.Inches(5.2))
                cap_p = doc.add_paragraph()
                cap_p.paragraph_format.space_after = Pt(14)
                cap_run = cap_p.add_run(f"Figure {ch['chapter_num']}.1: Visual Conceptual Architecture")
                cap_run.font.size = Pt(9)
                cap_run.italic = True
                cap_run.font.color.rgb = RGBColor(100, 116, 139)
            except Exception:
                pass

        lines = ch_text.split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("### "):
                doc.add_heading(line_str[4:].strip(), level=3)
            elif line_str.startswith("## "):
                doc.add_heading(line_str[3:].strip(), level=2)
            elif line_str.startswith("# "):
                doc.add_heading(line_str[2:].strip(), level=1)
            elif line_str.startswith("> "):
                p_quote = doc.add_paragraph()
                p_quote.paragraph_format.left_indent = Inches(0.4)
                r_q = p_quote.add_run(line_str[2:].strip())
                r_q.italic = True
            elif line_str.startswith("- ") or line_str.startswith("* "):
                doc.add_paragraph(line_str[2:].strip(), style='List Bullet')
            else:
                doc.add_paragraph(line_str)

        doc.add_page_break()

    # 6. Back Matter Review Magnet
    doc.add_heading("🌟 A Special Note From The Author", level=1)
    back_p = doc.add_paragraph()
    back_p.add_run(
        f"Thank you for investing your time and focus into reading {title}!\n\n"
        "Could you do me a quick 1-minute favor?\n"
        "If you found value in this book, could you please take a moment to leave an honest review on Amazon? "
        "Independent authors rely on genuine reader feedback, and your honest review directly helps other "
        "motivated learners discover this book.\n\n"
        "To your continued success,\n"
    )
    r_sign = back_p.add_run(f"{author}\n")
    r_sign.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ==============================================================================
# Niche Hunter Response Parser
# ==============================================================================
def parse_niches(raw_text: str) -> list[dict]:
    """Extracts structured micro-niches from LLM output for 1-click auto-fill buttons."""
    niches = []
    pattern = r'===NICHE_START===(.*?)===NICHE_END==='
    matches = re.findall(pattern, raw_text, re.DOTALL)
    for m in matches:
        item = {}
        for line in m.strip().split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                k = key.strip().upper()
                v = val.strip()
                if k in ("TOPIC", "TITLE"):
                    item["topic"] = v
                elif k == "SUBTITLE":
                    item["subtitle"] = v
                elif k in ("AUDIENCE", "TARGET_AUDIENCE"):
                    item["audience"] = v
                elif k in ("BSR_POTENTIAL", "BSR"):
                    item["bsr"] = v
                elif k == "COMPETITION":
                    item["competition"] = v
                elif k in ("PROFIT_SCORE", "SCORE"):
                    item["score"] = v
                elif k == "KEYWORDS":
                    item["keywords"] = v
                elif k in ("WHY_IT_SELLS", "HOOK"):
                    item["hook"] = v
        if item.get("topic"):
            niches.append(item)
    return niches


# ==============================================================================
# Sidebar: Persistent API Configuration & Diagnostics
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚙️ API Configuration")
    provider_choice = st.selectbox("API Provider", options=list(PROVIDERS.keys()), index=0)
    selected_config = PROVIDERS[provider_choice]

    initial_key = get_persisted_key(provider_choice)

    api_key_input = st.text_input(
        f"{provider_choice} API Key",
        value=initial_key,
        type="password",
        placeholder="e.g. gsk_..." if provider_choice == "Groq" else "Paste API key here...",
        help="Paste your API key here. Click '💾 Save Key' below to make it permanent across refreshes!"
    )

    cleaned_input = clean_api_key(api_key_input) or clean_api_key(initial_key)

    if provider_choice == "Groq" and cleaned_input and not cleaned_input.startswith("gsk_"):
        st.warning("⚠️ Groq keys must start with `gsk_`. You may have copied the wrong text.")

    # Dynamically query active models from Google Gemini, Groq, or OpenRouter
    available_models = list(selected_config["models"])
    if provider_choice == "Google Gemini" and cleaned_input:
        live_gemini = fetch_live_gemini_models(cleaned_input)
        if live_gemini:
            available_models = live_gemini
    elif provider_choice == "Groq" and cleaned_input:
        live_groq = fetch_live_groq_models(cleaned_input)
        if live_groq:
            available_models = live_groq
    elif provider_choice == "OpenRouter":
        live_or = fetch_live_openrouter_models()
        if live_or:
            available_models = live_or

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
        - **[Google AI Studio]({PROVIDERS['Google Gemini']['key_url']})** (Gemini 3.8 Flash, 1M TPM)
        - **[Groq Cloud Console]({PROVIDERS['Groq']['key_url']})** (Get key starting with `gsk_`)
        - **[OpenRouter]({PROVIDERS['OpenRouter']['key_url']})**
        """
    )


# ==============================================================================
# Main UI Header
# ==============================================================================
st.markdown("""
<div class="main-header">
    <h1>📚 KDP E-Book Architect Pro</h1>
    <p>Autonomous Bestseller Publishing Studio: BSR Niche Hunter • Deep Manuscript with Color Illustrations • 300-DPI Cover Designer (JPG & PDF) • Word (.docx) & KDP Launch Suite</p>
</div>
""", unsafe_allow_html=True)

# Session State Setup
if "book_data" not in st.session_state:
    st.session_state.book_data = None
if "niche_suggestions_raw" not in st.session_state:
    st.session_state.niche_suggestions_raw = None
if "niche_items" not in st.session_state:
    st.session_state.niche_items = []
if "selected_topic" not in st.session_state:
    st.session_state.selected_topic = ""
if "selected_subtitle" not in st.session_state:
    st.session_state.selected_subtitle = ""
if "selected_audience" not in st.session_state:
    st.session_state.selected_audience = ""

# Navigation Tabs: Studio vs Instant Cover Studio vs Guide
tab_studio, tab_cover_lab, tab_guide = st.tabs([
    "🚀 Autonomous Publishing Studio",
    "🎨 Built-in Cover Studio (JPG & PDF)",
    "📖 Complete Amazon KDP Publishing Guide"
])

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
            "সিস্টেম নিজেই তা অ্যানালাইসিস করবে এবং **১-ক্লিকে প্রজেক্টে লোড** করে দিবে।"
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
                with st.spinner("Analyzing Amazon buyer search volume, BSR trends, and monetization potential..."):
                    niche_sys_prompt = (
                        "Act as an Elite Amazon KDP Algorithm Data Analyst and Bestseller Researcher. "
                        "Your mission is to uncover 3 distinct, highly lucrative, low-competition micro-niches "
                        "with massive commercial buyer intent (BSR under 50,000 potential, 1,000-3,000 competitor search result feel). "
                        "Format each opportunity clearly using the exact delimited structure provided."
                    )
                    niche_user_prompt = f"""
Seed Industry: {chosen_seed}

For this seed industry, identify exactly 3 Golden Micro-Niche Book Opportunities.
Format each niche EXACTLY within delimiters like this:

===NICHE_START===
TOPIC: [Compelling, specific book topic/title]
SUBTITLE: [High-converting, benefit-driven subtitle]
AUDIENCE: [Specific target reader avatar & their urgent pain point]
BSR_POTENTIAL: [Estimated BSR e.g. 15,000 - 35,000 (~$1,200 - $3,500/month)]
COMPETITION: [Competition assessment, e.g. Low (~1,400 search results on Amazon)]
PROFIT_SCORE: [Viability score out of 10, e.g. 9.5/10]
KEYWORDS: [7 high-search volume Amazon buyer search phrases, comma-separated]
WHY_IT_SELLS: [Why buyers will click Buy Now over the existing top 10 competitors]
===NICHE_END===

Provide all 3 niches following this exact structure.
"""
                    try:
                        suggestions_raw = call_llm(niche_sys_prompt, niche_user_prompt, provider_choice, eff_key, active_model)
                        st.session_state.niche_suggestions_raw = suggestions_raw
                        st.session_state.niche_items = parse_niches(suggestions_raw)
                        st.success("✅ Golden Micro-Niches Discovered!")
                    except Exception as e:
                        st.error(f"Error fetching niches: {str(e)}")

        # Render Niches with 1-Click Auto-Fill
        if st.session_state.niche_items:
            st.markdown("#### 🏆 Discovered High-Profit Niches (Click to Auto-Fill):")
            for idx, n in enumerate(st.session_state.niche_items, 1):
                st.markdown(f"""
                <div class="niche-card">
                    <span class="niche-badge">OPPORTUNITY #{idx}</span>
                    <h3 style="margin: 0.2rem 0; color: #1e3a8a;">{n.get('topic', '')}</h3>
                    <p style="margin: 0.2rem 0 0.6rem 0; font-size: 0.95rem; color: #475569;"><em>{n.get('subtitle', '')}</em></p>
                    <div style="font-size: 0.88rem; margin-bottom: 0.6rem;">
                        <strong>Target Audience:</strong> {n.get('audience', '')}<br>
                        <strong>Estimated BSR Potential:</strong> <span style="color: #166534; font-weight: 700;">{n.get('bsr', 'Under 50,000')}</span> |
                        <strong>Competition:</strong> {n.get('competition', 'Low')} |
                        <strong>Viability Score:</strong> <span style="color: #b45309; font-weight: 700;">{n.get('score', '9/10')}</span><br>
                        <strong>Recommended 7 Keywords:</strong> <code>{n.get('keywords', '')}</code><br>
                        <strong>Why It Sells:</strong> {n.get('hook', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"🎯 1-Click Auto-Fill Niche #{idx} for My Book", key=f"fill_btn_{idx}", use_container_width=True):
                    st.session_state.selected_topic = n.get("topic", "")
                    st.session_state.selected_subtitle = n.get("subtitle", "")
                    st.session_state.selected_audience = n.get("audience", "")
                    st.success(f"✅ Loaded '{n.get('topic')}' into Book Project Details!")
                    st.rerun()

        elif st.session_state.niche_suggestions_raw:
            st.markdown("#### 🏆 Discovered Niches:")
            st.info(st.session_state.niche_suggestions_raw)

    # --------------------------------------------------------------------------
    # Book Configuration Inputs
    # --------------------------------------------------------------------------
    st.markdown("### ✍️ E-Book Project Details")

    col_t, col_a = st.columns([1.2, 1])
    with col_t:
        topic_input = st.text_input(
            "Main Book Topic / Working Title *",
            value=st.session_state.selected_topic,
            placeholder="e.g., Solar Battery & Backup Power Setup for Tiny Homes",
            help="The primary subject or working title of your book."
        )
    with col_a:
        audience_input = st.text_input(
            "Target Audience & Core Pain Point",
            value=st.session_state.selected_audience,
            placeholder="e.g., Off-grid enthusiasts, DIY homeowners, preppers",
            help="Who this book is written for."
        )

    col_sub, col_author = st.columns([1.5, 1])
    with col_sub:
        subtitle_input = st.text_input(
            "Book Subtitle (Optional)",
            value=st.session_state.selected_subtitle,
            placeholder="e.g., A Step-by-Step Blueprint to Energy Independence Without Spending Thousands",
            help="Benefit-driven subtitle that converts window-shoppers into buyers."
        )
    with col_author:
        author_input = st.text_input("Pen Name / Author Name", value="Alex Vance")

    col_theme, col_ch = st.columns([1.5, 1])
    with col_theme:
        theme_choice = st.selectbox(
            "Cover Design Palette (8 Luxury Styles)",
            options=list(COVER_THEMES.keys()),
            help="Select designer color scheme for 1600x2560 cover."
        )
    with col_ch:
        chapters_count = st.slider("Target Chapters", min_value=3, max_value=8, value=5)

    include_images_toggle = st.checkbox("🎨 Generate Contextual Color AI Illustrations for Every Chapter (Embedded in Word Doc)", value=True)

    start_generation_btn = st.button("🚀 Start Autonomous Book, Cover & Illustrations Generation", type="primary", use_container_width=True)

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
        st.markdown("### ⏳ Autonomous Bestseller Production in Progress...")

        progress_bar = st.progress(0.0)
        status_box = st.empty()

        p1_box = st.empty()
        p2_box = st.empty()
        p3_box = st.container()
        p4_box = st.empty()

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
                "Act as an Amazon KDP Bestseller Analyst and Consumer Psychologist. "
                "Generate 3 distinct viral book title formulas (Curiosity Hook, Direct Benefit, Authority Framework). "
                "For each, detail the psychological trigger and why it compels Amazon readers to click Buy Now."
            )
            p1_user = f"Topic: {topic_input.strip()}\nAudience: {audience_input.strip() if audience_input else 'General non-fiction buyers'}"
            phase1_output = call_llm(p1_sys, p1_user, provider_choice, eff_key, active_model)

            with p1_box.expander("📊 Phase 1: Market Research & Title Formulations", expanded=True):
                st.markdown(phase1_output)

            time.sleep(1)

            # 2. Phase 2: Chapter Outline Architecture
            current_step += 1
            update_ui(current_step, "Phase 2: Architecting Cohesive Chapter Outline & Frameworks...")

            p2_sys = (
                f"Act as a Master Non-Fiction Book Architect. Design an outline with exactly {chapters_count} "
                f"cohesive, actionable chapters based on Phase 1. Each chapter must have: Compelling Title, "
                f"Core Takeaway, 3 In-Depth Sub-Points, and a Hands-On Practical Implementation Exercise."
            )
            p2_user = f"Topic: {topic_input.strip()}\nTarget Chapters: {chapters_count}\nMarket Research Context:\n{phase1_output}"
            phase2_output = call_llm(p2_sys, p2_user, provider_choice, eff_key, active_model)

            with p2_box.expander("🏗️ Phase 2: Chapter Outline Architecture", expanded=True):
                st.markdown(phase2_output)

            time.sleep(1)

            # 3. Phase 3: Iterative Chapter Drafting & AI Image Generation
            chapters_list = []
            for ch in range(1, chapters_count + 1):
                current_step += 1
                update_ui(current_step, f"Phase 3: Deep Drafting Chapter {ch} of {chapters_count} & Rendering Color Illustration...")

                p3_sys = (
                    "Act as an Authoritative, World-Class Non-Fiction Author. Write in-depth, captivating, high-value content. "
                    "Structure every chapter with:\n"
                    "1. Executive Overview & Core Objective\n"
                    "2. Deep Technical & Strategic Sub-Sections with H2 and H3 headers\n"
                    "3. '> 💡 PRO TIP:' breakout callout\n"
                    "4. '> ⚠️ COMMON PITFALL TO AVOID:' breakout callout\n"
                    "5. '### 🎯 The 15-Minute Action Plan' (a concrete exercise the reader can do today)\n"
                    "6. '### 📋 Chapter Summary & Key Checklist'\n"
                    "Avoid generic fluff; write actionable, deep text."
                )
                p3_user = f"""
Book Topic: {topic_input.strip()}
Audience: {audience_input.strip()}
Complete Outline Context:
{phase2_output}

INSTRUCTION:
Write ONLY Chapter {ch} in deep, comprehensive detail (around 1,000-1,400 words).
Ensure all sub-points, callout boxes, and practical exercises are fully articulated in clean Markdown.
"""
                ch_text = call_llm(p3_sys, p3_user, provider_choice, eff_key, active_model, temperature=0.7)

                # Generate Color Illustration for this chapter
                img_bytes = None
                if include_images_toggle:
                    ch_img_prompt = f"high quality colorful editorial digital art infographic concept for {topic_input.strip()} Chapter {ch} practical diagram cinematic lighting 8k"
                    img_bytes = fetch_ai_image(ch_img_prompt, width=1024, height=640)

                chapters_list.append({
                    "chapter_num": ch,
                    "content": ch_text,
                    "image_bytes": img_bytes
                })

                with p3_box.expander(f"📖 Chapter {ch} Manuscript Draft & Color Illustration", expanded=False):
                    if img_bytes:
                        st.image(img_bytes, caption=f"Chapter {ch} Color Illustration (Embedded in Word Doc)", use_container_width=True)
                    st.markdown(ch_text)

                time.sleep(2)

            # 4. Phase 4: Amazon KDP Launch Arsenal
            current_step += 1
            update_ui(current_step, "Phase 4: Generating Amazon KDP SEO & Launch Package...")

            p4_sys = (
                "Act as an Amazon KDP Bestseller Launch Strategist. Generate a complete, high-converting "
                "KDP Publishing & SEO Package including: HTML Book Description, 7 Backend Search Keywords, "
                "2 BISAC & Browse Categories, Amazon A+ Content Copy, Pricing Blueprint, and Amazon PPC Keywords."
            )
            p4_user = f"""
Book Topic: {topic_input.strip()}
Subtitle: {subtitle_input.strip() if subtitle_input else 'A Practical Step-by-Step Blueprint'}
Author: {author_input.strip()}
Chapters Outline:
{phase2_output}

Generate the complete launch suite with the following 6 sections:
[1] OPTIMIZED HTML BOOK DESCRIPTION (Ready for Amazon KDP, using <b>, <h3>, <ul>, <li> tags, emotional hook, and bullet points)
[2] 7 BACKEND SEARCH KEYWORDS (Under 50 characters each, comma-separated, high commercial intent)
[3] 2 EXACT AMAZON CATEGORIES & BROWSE PATHS (Full navigation path)
[4] AMAZON A+ CONTENT MODULE COPY (3 structured text modules: Headline Banner, 3 Key Benefits Grid, Author Letter)
[5] 20 TARGETED AMAZON PPC / AMS KEYWORDS (For running $5/day ads to get instant sales)
[6] PRICING & 70% ROYALTY STRATEGY (Launch price vs Evergreen price recommendation)
"""
            phase4_output = call_llm(p4_sys, p4_user, provider_choice, eff_key, active_model)

            with p4_box.expander("🚀 Phase 4: Amazon KDP SEO Package", expanded=True):
                st.markdown(phase4_output)

            time.sleep(1)

            # 5. Phase 5: Front/Back Matter, Built-in Cover (JPG & PDF) & Word (.docx) Generation
            current_step += 1
            update_ui(current_step, "Phase 5: Rendering 300-DPI Covers (JPG & PDF) & Word Manuscript with Embedded Images...")

            cover_title = topic_input.strip()
            cover_subtitle = subtitle_input.strip() if subtitle_input else (audience_input.strip() if audience_input else "A Practical Step-by-Step Blueprint")

            # Fetch AI cover art background if desired
            cover_art_prompt = f"minimalist luxury book cover art concept for {topic_input.strip()} dramatic lighting gold and dark palette cinematic 8k"
            cover_art_bg = fetch_ai_image(cover_art_prompt, width=1600, height=2560)

            cover_jpg_bytes, cover_pdf_bytes = generate_amazon_cover_both(
                title=cover_title,
                subtitle=cover_subtitle,
                author=author_input.strip() if author_input else "Alex Vance",
                theme_name=theme_choice,
                bg_art_bytes=cover_art_bg
            )

            # Paperback wraparound PDF
            wrap_pdf_bytes = generate_paperback_wraparound(
                title=cover_title,
                subtitle=cover_subtitle,
                author=author_input.strip() if author_input else "Alex Vance",
                blurb=subtitle_input.strip() if subtitle_input else f"The ultimate action guide to mastering {topic_input.strip()}.",
                theme_name=theme_choice,
                chapters_count=chapters_count
            )

            # Front & Back Matter
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

# 🌟 A Special Note From The Author

Thank you for investing your time and focus into reading **{topic_input.strip()}**!

### How You Can Help Fellow Readers:
If you found value from this book, **could you please leave an honest 1-minute review on Amazon?**
Independent authors depend on genuine reader feedback, and your review helps other passionate learners discover this book!

### Claim Your Companion Action Cheatsheet:
Visit our reader portal to claim your companion checklists and workbook templates to put this book into immediate action.
"""

            all_chapters_formatted = "\n\n---\n\n".join([ch["content"] for ch in chapters_list])
            master_manuscript = f"{front_matter}\n\n# Table of Contents\n{phase2_output}\n\n---\n\n{all_chapters_formatted}\n{back_matter}"

            # Generate Microsoft Word (.docx) document with embedded images
            docx_bytes = create_docx_manuscript(
                title=topic_input.strip(),
                subtitle=cover_subtitle,
                author=author_input.strip() if author_input else "Alex Vance",
                phase2_outline=phase2_output,
                chapters_list=chapters_list
            )

            # Prepare Quick Copy-Paste KDP Metadata Sheet
            kdp_sheet = f"""================================================================================
AMAZON KDP FAST-LAUNCH METADATA SHEET
Topic: {topic_input.strip()}
Subtitle: {cover_subtitle}
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
INSTRUCTIONS FOR 5-MINUTE LAUNCH:
1. Open https://kdp.amazon.com -> Click '+ Create' -> 'Kindle eBook'
2. Paste the Title, Subtitle, and HTML Description from this sheet.
3. Paste the 7 Keywords into the 7 boxes.
4. Select the 2-3 Categories recommended above.
5. Upload your manuscript (.docx with embedded images) & your cover.jpg.
6. Set price to $4.99 (70% Royalty = $3.49 profit per sale).
================================================================================
"""

            slug = sanitize_filename(topic_input.strip())
            st.session_state.book_data = {
                "topic": topic_input.strip(),
                "subtitle": cover_subtitle,
                "author": author_input.strip(),
                "chapters_count": chapters_count,
                "provider": provider_choice,
                "model": active_model,
                "phase1": phase1_output,
                "phase2": phase2_output,
                "chapters": chapters_list,
                "phase4": phase4_output,
                "master_manuscript": master_manuscript,
                "docx_bytes": docx_bytes,
                "kdp_sheet": kdp_sheet,
                "cover_jpg_bytes": cover_jpg_bytes,
                "cover_pdf_bytes": cover_pdf_bytes,
                "wrap_pdf_bytes": wrap_pdf_bytes,
                "filename_md": f"{slug}_manuscript.md",
                "filename_docx": f"{slug}_manuscript.docx",
                "filename_txt": f"{slug}_manuscript.txt",
                "cover_filename_jpg": f"{slug}_cover.jpg",
                "cover_filename_pdf": f"{slug}_cover.pdf",
                "wrap_filename_pdf": f"{slug}_paperback_wrap_cover.pdf",
                "sheet_filename": f"{slug}_kdp_launch_sheet.txt"
            }

            progress_bar.progress(1.0)
            status_box.empty()

        except Exception as e:
            status_box.empty()
            st.error(f"❌ **Generation Error:** {str(e)}")
            st.warning("💡 Tip: If you ever encounter a rate limit on Groq, select 'Google Gemini' in the sidebar for 1 Million tokens/min without limits.")

    # --------------------------------------------------------------------------
    # Results, Downloads & Live Amazon Product Page Simulator
    # --------------------------------------------------------------------------
    if st.session_state.book_data is not None:
        data = st.session_state.book_data
        total_words = count_words(data["master_manuscript"])
        est_read_time = max(10, round(total_words / 220))

        st.markdown("---")
        st.success("🎉 **Bestseller Production Complete!** Word (.docx with Color Illustrations), 300-DPI Covers (JPG & PDF) & KDP Launch Suite are ready.")

        # Key Metrics
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-card">
                    <div class="metric-value">{data['chapters_count']}</div>
                    <div class="metric-label">Chapters Written</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_words:,}</div>
                    <div class="metric-label">Total Words</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">~{est_read_time} min</div>
                    <div class="metric-label">Reading Time</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">1600 x 2560</div>
                    <div class="metric-label">300 DPI Cover</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">70%</div>
                    <div class="metric-label">KDP Royalty Tier</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 6-Way Multi-Format Download Suite
        st.markdown("### 📥 1-Click Multi-Format Export Arsenal")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            if HAS_DOCX and data.get("docx_bytes"):
                st.download_button(
                    label="📄 1. Download Word Doc (.docx - With Color Images)",
                    data=data["docx_bytes"],
                    file_name=data["filename_docx"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True
                )
            else:
                st.download_button(
                    label="📝 1. Download Manuscript (.md)",
                    data=data["master_manuscript"],
                    file_name=data["filename_md"],
                    mime="text/markdown",
                    type="primary",
                    use_container_width=True
                )
        with col_d2:
            st.download_button(
                label="🖼️ 2. Download eBook Cover (.jpg - 300 DPI)",
                data=data["cover_jpg_bytes"],
                file_name=data["cover_filename_jpg"],
                mime="image/jpeg",
                type="primary",
                use_container_width=True
            )
        with col_d3:
            st.download_button(
                label="📑 3. Download Print Front Cover (.pdf - 300 DPI)",
                data=data["cover_pdf_bytes"],
                file_name=data["cover_filename_pdf"],
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

        col_d4, col_d5, col_d6 = st.columns(3)
        with col_d4:
            st.download_button(
                label="📦 4. Download Paperback Wrap Cover (.pdf)",
                data=data["wrap_pdf_bytes"],
                file_name=data["wrap_filename_pdf"],
                mime="application/pdf",
                use_container_width=True
            )
        with col_d5:
            st.download_button(
                label="🚀 5. Download KDP Fast-Launch Sheet (.txt)",
                data=data["kdp_sheet"],
                file_name=data["sheet_filename"],
                mime="text/plain",
                use_container_width=True
            )
        with col_d6:
            st.download_button(
                label="📝 6. Download Markdown Manuscript (.md)",
                data=data["master_manuscript"],
                file_name=data["filename_md"],
                mime="text/markdown",
                use_container_width=True
            )

        # ----------------------------------------------------------------------
        # Simulated Amazon Kindle Store Product Listing
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🛒 Live Amazon Kindle Store Preview")
        st.markdown("Here is exactly how your book appears to shoppers on Amazon.com:")

        col_amz_img, col_amz_info = st.columns([1, 1.8])
        with col_amz_img:
            st.image(data["cover_jpg_bytes"], caption="Kindle Edition Front Cover", use_container_width=True)
        with col_amz_info:
            st.markdown(f"""
            <div class="amazon-sim-card">
                <span style="background: #e67a00; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700;">#1 Best Seller</span>
                <span style="font-size: 0.85rem; color: #565959;"> in Non-Fiction & Guides</span>
                <h2 style="margin: 0.4rem 0 0.2rem 0; color: #0f1111; font-size: 1.6rem;">{data['topic']}</h2>
                <h4 style="margin: 0 0 0.5rem 0; color: #565959; font-weight: 500; font-size: 1rem;">{data.get('subtitle', '')}</h4>
                <p style="margin: 0 0 0.4rem 0; font-size: 0.9rem;">by <strong style="color: #007185;">{data['author']}</strong> (Author)</p>
                <div class="amazon-star-badge">★★★★★ <span style="font-size: 0.9rem; color: #007185;">4.9 out of 5 stars (1,842 ratings)</span></div>
                <hr style="margin: 0.8rem 0; border: none; border-top: 1px solid #e2e8f0;">
                <div style="display: flex; gap: 1rem; align-items: baseline;">
                    <div><span class="amazon-price-tag">$4.99</span> <span style="font-size: 0.85rem; color: #565959;">Kindle Price</span></div>
                    <div style="font-size: 0.85rem; color: #007600; font-weight: 700;">✓ Available on Kindle Unlimited ($0.00)</div>
                </div>
                <p style="font-size: 0.85rem; color: #565959; margin-top: 0.3rem;">Print length: ~{max(20, round(total_words / 250))} pages • Estimated read: {est_read_time} mins</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📖 Look Inside: Read Book Introduction & Illustrations", expanded=False):
                st.markdown(f"### {data['topic']}")
                st.markdown(f"**By {data['author']}**")
                st.markdown("#### Table of Contents:")
                st.markdown(data["phase2"])
                if data["chapters"]:
                    st.markdown("---")
                    st.markdown("#### Chapter 1 Preview & Illustration:")
                    if data["chapters"][0].get("image_bytes"):
                        st.image(data["chapters"][0]["image_bytes"], caption="Chapter 1 Illustration", use_container_width=True)
                    st.markdown(data["chapters"][0]["content"][:1000] + "...\n\n*(Full content in downloaded Word .docx manuscript)*")

        # ----------------------------------------------------------------------
        # Quick 1-Tap Copy Hub for Mobile
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 📋 1-Tap Quick Copy Hub for KDP Publishing")
        tab_c_title, tab_c_kw, tab_c_desc, tab_c_sheet = st.tabs([
            "📌 Title & Subtitle",
            "🔑 7 Backend Keywords",
            "📝 Amazon HTML Description",
            "📄 Complete Metadata Sheet"
        ])

        with tab_c_title:
            st.code(f"Title: {data['topic']}\nSubtitle: {data.get('subtitle', '')}\nAuthor: {data['author']}", language="text")

        with tab_c_kw:
            st.info("Paste each of these 7 keywords into the 7 keyword boxes on Amazon KDP:")
            kw_match = re.search(r'\[2\][^\n]*\n(.*?)(?=\n\[3\]|\Z)', data["phase4"], re.DOTALL)
            kw_text = kw_match.group(1).strip() if kw_match else "Extracted in Fast-Launch Sheet"
            st.code(kw_text, language="text")

        with tab_c_desc:
            st.info("Paste this HTML Description into the Description box on KDP:")
            desc_match = re.search(r'\[1\][^\n]*\n(.*?)(?=\n\[2\]|\Z)', data["phase4"], re.DOTALL)
            desc_text = desc_match.group(1).strip() if desc_match else data["phase4"]
            st.code(desc_text, language="html")

        with tab_c_sheet:
            st.text_area("Full Launch Sheet", value=data["kdp_sheet"], height=300)

        if st.button("🔄 Clear & Create Another Bestseller", use_container_width=False):
            st.session_state.book_data = None
            st.rerun()


# ==============================================================================
# TAB 2: STANDALONE COVER STUDIO (JPG & PDF PRINT READY)
# ==============================================================================
with tab_cover_lab:
    st.markdown("### 🎨 Instant 300-DPI Cover Designer (Zero Canva Required)")
    st.markdown("Design and download high-resolution Amazon Kindle covers in both **JPG (for eBook)** and **PDF (for Print)** format.")

    col_cov_in, col_cov_out = st.columns([1, 1.1])
    with col_cov_in:
        cov_title = st.text_input("Book Main Title", value="THE FREEDOM FORMULA")
        cov_subtitle = st.text_input("Book Subtitle", value="How to Build Passive Income Streams and Escape the 9-to-5")
        cov_author = st.text_input("Author / Pen Name", value="Alex Vance")
        cov_badge = st.text_input("Top Ribbon Genre Badge", value="THE DEFINITIVE ACTION BLUEPRINT")
        cov_theme = st.selectbox("Design Color Palette", options=list(COVER_THEMES.keys()), index=0, key="studio_cover_theme")
        cov_use_ai_bg = st.checkbox("Generate Thematic AI Artwork Background", value=True)

        render_cover_btn = st.button("⚡ Render 300-DPI Covers (JPG & PDF)", type="primary", use_container_width=True)

    with col_cov_out:
        if render_cover_btn or "lab_cover_jpg" not in st.session_state:
            with st.spinner("Rendering 300-DPI cover with artwork and geometric frame..."):
                bg_bytes = None
                if cov_use_ai_bg:
                    bg_bytes = fetch_ai_image(f"luxury book cover concept for {cov_title} cinematic dramatic lighting 8k", width=1600, height=2560)

                jpg_b, pdf_b = generate_amazon_cover_both(
                    title=cov_title,
                    subtitle=cov_subtitle,
                    author=cov_author,
                    theme_name=cov_theme,
                    genre_badge=cov_badge,
                    bg_art_bytes=bg_bytes
                )
                st.session_state.lab_cover_jpg = jpg_b
                st.session_state.lab_cover_pdf = pdf_b

        if "lab_cover_jpg" in st.session_state:
            st.image(st.session_state.lab_cover_jpg, caption=f"Amazon-Ready 300 DPI (1600x2560 px) - Palette: {cov_theme}", width=340)
            cov_slug = sanitize_filename(cov_title)
            col_d_j, col_d_p = st.columns(2)
            with col_d_j:
                st.download_button(
                    label="📥 1. Download eBook Cover (.jpg)",
                    data=st.session_state.lab_cover_jpg,
                    file_name=f"{cov_slug}_cover.jpg",
                    mime="image/jpeg",
                    type="primary",
                    use_container_width=True
                )
            with col_d_p:
                st.download_button(
                    label="📑 2. Download Print Cover (.pdf)",
                    data=st.session_state.lab_cover_pdf,
                    file_name=f"{cov_slug}_cover.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )


# ==============================================================================
# TAB 3: STEP-BY-STEP AMAZON KDP ACTION GUIDE
# ==============================================================================
with tab_guide:
    st.markdown("""
### 🧭 How to Publish on Amazon KDP & Earn from Week 1 (The Complete Master Blueprint)

Amazon Kindle Direct Publishing (KDP)-এ বই প্রকাশ করে প্রথম সপ্তাহ থেকেই প্যাসিভ ইনকাম শুরু করতে নিচের প্রতিটি বিষয় খুঁটিনাটি জানা অত্যন্ত জরুরি:

---

### 1️⃣ আমাজনে বই প্রকাশের দুটি মূল ফরম্যাট (Kindle eBook বনাম Paperback)

| উপাদান | 📱 Kindle eBook (ডিজিটাল বই) | 📖 Paperback / Hardcover (প্রিন্ট বই) |
| :--- | :--- | :--- |
| **ম্যানুস্ক্রিপ্ট ফাইল** | `.docx` (Microsoft Word) অথবা `.kpf` | `.docx` অথবা প্রিন্ট সাইজ অনুযায়ী তৈরি `.pdf` |
| **কভার ফাইল ফরম্যাট** | **শুধুমাত্র JPG বা TIFF** (১৬০০ x ২৫৬০ পিক্সেল, ৩০০ DPI) | **শুধুমাত্র Print-Ready PDF** (Front + Spine + Back এক ফাইলে) |
| **ISBN নম্বর** | **কোনো ISBN লাগে না** (আমাজন ফ্রি ASIN দেয়) | **ফ্রি KDP ISBN** আমাজন নিজে থেকেই দেয় (১ ক্লিকে) |
| **রয়্যালটি (লাভের ভাগ)** | **৭০%** অথবা ৩৫% | **৬০%** (প্রিন্টিং খরচ বাদ দিয়ে) |
| **রঙিন ছবি** | সম্পূর্ণ রঙিন দেখা যায় যেকোনো কিন্ডল অ্যাপ বা ট্যাবলেটে | রঙিন বা সাদাকালো প্রিন্ট অপশন থাকে |

> ⚠️ **গুরুত্বপূর্ণ কভার নিয়ম:** অনেকে ভুল করে কিন্ডল ইবুকে PDF কভার আপলোড করার চেষ্টা করে এরর খায়। আমাজনের কঠোর নিয়ম: **Kindle eBook কভার সবসময় JPG হতে হবে**, আর **Paperback কভার সবসময় PDF হতে হবে**। আমাদের সিস্টেম দুটোই এক ক্লিকে বানিয়ে দেয়!

---

### 2️⃣ আমাজন রয়্যালটি ও প্রাইসিং স্ট্র্যাটেজি (৭০% বনাম ৩৫%)

1. **৭০% রয়্যালটি রেঞ্জ ($২.৯৯ থেকে $৯.৯৯):**
   - আপনার বইয়ের দাম যদি **$২.৯৯ থেকে $৯.৯৯** এর মধ্যে রাখেন, আমাজন আপনাকে প্রতি সেলে **৭০% সরাসরি প্রফিট** দিবে।
   - উদাহরণ: বইয়ের দাম **$৪.৯৯** রাখলে প্রতি সেলে আপনি পাবেন প্রায় **$৩.৪৯ (প্রায় ৪০০ টাকা)**।
   - দিনে মাত্র ৫টি বই সেল হলে: **$১৭.৪৫/দিন = $৫২৩/মাস (প্রায় ৬০,০০০ টাকা/মাস)**!
2. **ডেলিভারি ফি (Delivery Fee):**
   - ৭০% রয়্যালটিতে আমাজন প্রতি মেগাবাইট (MB) সাইজের জন্য $০.১৫ কেটে নেয়। তাই আমাদের সিস্টেম ছবিগুলোর সাইজ অপ্টিমাইজ করে ফাইল সাইজ ৫MB-এর নিচে রাখে যাতে আপনার রয়্যালটি সর্বোচ্চ থাকে!
3. **KDP Select (Kindle Unlimited):**
   - পাবলিশ করার সময় **KDP Select** বক্সে টিক দিবেন। এতে কিন্ডল আনলিমিটেড ব্যবহারকারীরা আপনার বই ফ্রি পড়লেও যত পেজ পড়বে, আমাজন প্রতি পেজের জন্য আপনাকে আলাদা টাকা পে করবে!

---

### 3️⃣ পেপারব্যাক কভারের গোপন গণিত (Spine Width & Bleed Calculation)

আমাজনে পেপারব্যাক বই প্রিন্ট করার জন্য কভারটি একটি একক ফ্ল্যাট PDF হতে হবে যেখানে:
- **বামের অংশ:** Back Cover (বইয়ের ব্লার্ব, রিভিউর কথা ও বারকোডের জায়গা)
- **মাঝের অংশ:** Spine (বইয়ের পিঠ, যেখানে টাইটেল ও লেখকের নাম থাকে)
- **ডানের অংশ:** Front Cover (মূল আর্টওয়ার্ক ও টাইটেল)
- **ব্লিড (Bleed):** চারপাশে ০.১২৫ ইঞ্চি বাড়তি মার্জিন থাকতে হয় কাটিংয়ের সুবিধার জন্য।
- *আমাদের সিস্টেম বইয়ের অধ্যায় অনুযায়ী স্বয়ংক্রিয়ভাবে স্পাইন মেপে এই ফুল র‍্যাপ PDF তৈরি করে দেয়!*

---

### 4️⃣ বাংলাদেশ, ভারত ও বিশ্বজুড়ে ব্যাংক সেটআপ (Payoneer / Wise)

1. আমাজন সরাসরি ইউএস (US) ব্যাংক অ্যাকাউন্টে প্রতি মাসের রয়্যালটি পাঠিয়ে দেয়।
2. আপনি বাংলাদেশ, ভারত বা বিশ্বের যেখানেই থাকুন:
   - **[Payoneer.com](https://www.payoneer.com/)** অথবা **Wise**-এ একটি ফ্রি অ্যাকাউন্ট খুলুন।
   - Payoneer আপনাকে একটি ফ্রি **Virtual US Bank Account** (Routing Number & Account Number) দিবে।
   - KDP ড্যাশবোর্ডে গিয়ে এই Routing ও Account Number বসিয়ে দিন। আমাজন সরাসরি ডলারে টাকা পাঠিয়ে দিবে, যা আপনি আপনার লোকাল বিকাশ বা ব্যাংকে ট্রান্সফার করে নিতে পারবেন!
3. **W-8BEN ট্যাক্স ইন্টারভিউ (Tax Interview):**
   - KDP অ্যাকাউন্টে ২ মিনিটের অনলাইন ট্যাক্স ইন্টারভিউ দিতে হয়।
   - "Individual" সিলেক্ট করবেন এবং আপনার দেশের নাম দিয়ে আপনার জাতীয় পরিচয়পত্র (NID) নম্বর দিয়ে দিবেন। এতে ইউএস ট্যাক্স ট্রিটির সুবিধা অনুযায়ী কোনো বাড়তি ট্যাক্স কাটা হবে না।

---

### 5️⃣ প্রথম সপ্তাহেই বেস্টসেলার হওয়ার অ্যাকশন প্ল্যান (Launch Formula)

1. **Phase 0 Niche Hunter ব্যবহার করুন:** এমন নিশে বই লিখুন যেখানে আমাজনে সার্চ রেজাল্ট ১,০০০ থেকে ৩,০০০-এর মধ্যে (কম্পিটিশন কম)।
2. **আই-ক্যাচিং কভার:** কভার দেখেই মানুষ ক্লিক করে। আমাদের ৩ডি লাক্সারি কভার ক্রেতার নজর আটকাবে।
3. **৭টি ব্যাকএন্ড কিওয়ার্ড:** সিস্টেমের দেওয়া ৭টি কিওয়ার্ড আমাজনের ৭টি বক্সে পেস্ট করুন—এটি আমাজনের সার্চ অ্যালগরিদমে আপনার বইকে প্রথম পেজে নিয়ে আসবে।
4. **HTML ডেসক্রিপশন:** বোল্ড হেডলাইন ও বুলেট পয়েন্টসহ তৈরি ডেসক্রিপশন পেস্ট করুন, যা পড়ার পর ক্রেতার কেনা ছাড়া উপায় থাকবে না।
5. **লঞ্চ প্রাইজ ($২.৯৯ বা $৪.৯৯):** প্রথমে $২.৯৯ দিয়ে শুরু করুন যাতে দ্রুত সেলস ও র‍্যাংক বাড়ে, পরে $৪.৯৯ বা $৬.৯৯ তে বাড়িয়ে প্যাসিভ ইনকাম দ্বিগুণ করুন!
""")
