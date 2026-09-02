import json
from pathlib import Path
from typing import Dict, Any

LOCALES_DIR = Path(__file__).resolve().parent / "locales"

SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "en_US": {"name": "English", "flag_url": "https://flagcdn.com/w40/us.png", "short": "EN"},
    "pt_BR": {"name": "Português", "flag_url": "https://flagcdn.com/w40/br.png", "short": "PT"},
    "ko_KR": {"name": "한국어", "flag_url": "https://flagcdn.com/w40/kr.png", "short": "KO"},
    "vi_VN": {"name": "Tiếng Việt", "flag_url": "https://flagcdn.com/w40/vn.png", "short": "VI"},
    "es_ES": {"name": "Español", "flag_url": "https://flagcdn.com/w40/es.png", "short": "ES"},
    "de_DE": {"name": "Deutsch", "flag_url": "https://flagcdn.com/w40/de.png", "short": "DE"},
    "fr_FR": {"name": "Français", "flag_url": "https://flagcdn.com/w40/fr.png", "short": "FR"},
    "pl_PL": {"name": "Polski", "flag_url": "https://flagcdn.com/w40/pl.png", "short": "PL"},
    "tr_TR": {"name": "Türkçe", "flag_url": "https://flagcdn.com/w40/tr.png", "short": "TR"},
    "zh_TW": {"name": "繁體中文", "flag_url": "https://flagcdn.com/w40/tw.png", "short": "TW"},
    "uk_UA": {"name": "Українська", "flag_url": "https://flagcdn.com/w40/ua.png", "short": "UA"},
}

def _load_languages() -> Dict[str, Dict[str, str]]:
    langs: Dict[str, Dict[str, str]] = {}
    if LOCALES_DIR.exists():
        for file in LOCALES_DIR.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    langs[file.stem] = json.load(f)
            except Exception:
                pass
    return langs

LANGUAGES: Dict[str, Dict[str, str]] = _load_languages()

def get_text(key: str, lang: str = "en_US", **kwargs: Any) -> str:
    lang_dict = LANGUAGES.get(lang) or LANGUAGES.get("en_US", {})
    fallback_dict = LANGUAGES.get("en_US", {})
    text = lang_dict.get(key, fallback_dict.get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

def render_language_dropdown(current_lang: str = "en_US", on_change_callback: str = "changeLanguage") -> str:
    active_info = SUPPORTED_LANGUAGES.get(current_lang, SUPPORTED_LANGUAGES["en_US"])
    options_html = []
    for code, info in SUPPORTED_LANGUAGES.items():
        is_active = (code == current_lang)
        active_cls = " active" if is_active else ""
        options_html.append(f"""
        <button type="button" class="lang-option{active_cls}" onclick="{on_change_callback}('{code}')">
            <img class="lang-flag-img" src="{info['flag_url']}" alt="{info['short']}" />
            <span class="lang-name">{info['name']}</span>
            <span class="lang-code-tag">{info['short']}</span>
        </button>
        """)
    return f"""
    <div class="lang-dropdown-wrapper" id="lang-dropdown-wrapper">
        <button type="button" class="lang-dropdown-btn" onclick="toggleLanguageDropdown(event)">
            <img class="lang-flag-img" src="{active_info['flag_url']}" alt="{active_info['short']}" />
            <span class="lang-btn-text">{active_info['short']}</span>
            <span class="lang-arrow">▾</span>
        </button>
        <div class="lang-dropdown-menu" id="lang-dropdown-menu">
            {''.join(options_html)}
        </div>
    </div>
    """
