import os
import time
import re
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
RIOT_KEY_EXPIRES_AT = os.getenv("RIOT_KEY_EXPIRES_AT", "") # Unix timestamp in seconds
DEFAULT_ROUTING = os.getenv("DEFAULT_ROUTING", "americas")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "br1")

# Regional Routing Mapping (Match V5 requires specific continental clusters)
REGION_TO_ROUTING = {
    # Americas
    "BR1": "americas",
    "NA1": "americas",
    "LA1": "americas",
    "LA2": "americas",
    "OC1": "sea",
    # Europe
    "EUW1": "europe",
    "EUN1": "europe",
    "TR1": "europe",
    "RU": "europe",
    "ME1": "europe",
    # Asia
    "KR": "asia",
    "JP1": "asia",
    # SEA
    "PH2": "sea",
    "SG2": "sea",
    "TH2": "sea",
    "TW2": "sea",
    "VN2": "sea",
}

# Country flag icons for display
REGION_FLAGS = {
    "BR1": ("https://flagcdn.com/w40/br.png", "Brazil (BR1)"),
    "NA1": ("https://flagcdn.com/w40/us.png", "North America (NA1)"),
    "EUW1": ("https://flagcdn.com/w40/eu.png", "Europe West (EUW1)"),
    "EUN1": ("https://flagcdn.com/w40/eu.png", "Europe Nordic & East (EUN1)"),
    "KR": ("https://flagcdn.com/w40/kr.png", "Korea (KR)"),
    "JP1": ("https://flagcdn.com/w40/jp.png", "Japan (JP1)"),
    "LA1": ("https://flagcdn.com/w40/mx.png", "Latin America North (LAN)"),
    "LA2": ("https://flagcdn.com/w40/cl.png", "Latin America South (LAS)"),
    "OC1": ("https://flagcdn.com/w40/au.png", "Oceania (OCE)"),
    "TR1": ("https://flagcdn.com/w40/tr.png", "Turkey (TR1)"),
    "RU": ("https://flagcdn.com/w40/ru.png", "Russia (RU)"),
    "ME1": ("https://flagcdn.com/w40/ae.png", "Middle East (ME1)"),
    "PH2": ("https://flagcdn.com/w40/ph.png", "Philippines (PH2)"),
    "SG2": ("https://flagcdn.com/w40/sg.png", "Singapore (SG2)"),
    "TH2": ("https://flagcdn.com/w40/th.png", "Thailand (TH2)"),
    "TW2": ("https://flagcdn.com/w40/tw.png", "Taiwan (TW2)"),
    "VN2": ("https://flagcdn.com/w40/vn.png", "Vietnam (VN2)"),
}

def get_routing_for_match_id(match_id: str) -> str:
    """Extracts the region prefix from match_id (e.g. BR1_123, KR_123) and returns the correct routing cluster."""
    mid = (match_id or "").upper().strip()
    if "_" in mid:
        prefix = mid.split("_")[0]
        if prefix in REGION_TO_ROUTING:
            return REGION_TO_ROUTING[prefix]
        # Handle KR1 alias
        if prefix == "KR1":
            return "asia"
    return DEFAULT_ROUTING

def get_region_flag_badge(match_id: str) -> str:
    """Returns an HTML img flag badge for the match region."""
    mid = (match_id or "").upper().strip()
    prefix = mid.split("_")[0] if "_" in mid else ""
    if prefix == "KR1":
        prefix = "KR"
    flag_info = REGION_FLAGS.get(prefix)
    if flag_info:
        url, title = flag_info
        return f'<span class="region-flag-badge" title="{title}"><img src="{url}" alt="{prefix}" class="region-flag-img"/> <span class="region-tag-text">{prefix}</span></span>'
    elif prefix:
        return f'<span class="region-flag-badge"><span class="region-tag-text">{prefix}</span></span>'
    return ""

def get_api_key() -> str:
    global RIOT_API_KEY
    return os.getenv("RIOT_API_KEY") or RIOT_API_KEY or ""

def get_key_expires_at() -> str:
    global RIOT_KEY_EXPIRES_AT
    return os.getenv("RIOT_KEY_EXPIRES_AT") or RIOT_KEY_EXPIRES_AT or ""

def is_production_mode() -> bool:
    # Only active if explicitly defined as production or permanent in config/env
    exp = (get_key_expires_at() or "").lower()
    return bool(get_api_key() and (exp in ("permanent", "perma", "never") or os.getenv("BLAZE_ENV") == "production"))

def parse_expiry_str(text: str) -> int:
    import re
    if not text:
        return 0
    text = text.strip()
    if text.isdigit() and len(text) >= 10:
        return int(text)
    m_rel = re.search(r'in\s+(\d+)\s+hours?(?:\s+and\s+(\d+)\s+minutes?)?', text, re.I)
    if not m_rel:
        m_rel = re.search(r'em\s+(\d+)\s+horas?(?:\s+e\s+(\d+)\s+minutos?)?', text, re.I)
    if m_rel:
        hours = int(m_rel.group(1))
        minutes = int(m_rel.group(2)) if m_rel.group(2) else 0
        return int(time.time() + hours * 3600 + minutes * 60)
    m_min = re.search(r'in\s+(\d+)\s+minutes?', text, re.I) or re.search(r'em\s+(\d+)\s+minutos?', text, re.I)
    if m_min:
        return int(time.time() + int(m_min.group(1)) * 60)
    return int(time.time() + 24 * 3600)

def save_api_key(new_key: str, expiry_text: str = ""):
    global RIOT_API_KEY, RIOT_KEY_EXPIRES_AT
    import time
    RIOT_API_KEY = new_key
    exp_ts = parse_expiry_str(expiry_text) if expiry_text else (int(time.time() + 24 * 3600))
    RIOT_KEY_EXPIRES_AT = str(exp_ts)

    env_file = BASE_DIR / ".env"
    lines = []
    found_key = False
    found_exp = False
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("RIOT_API_KEY="):
                    lines.append(f"RIOT_API_KEY={new_key}\n")
                    found_key = True
                elif line.startswith("RIOT_KEY_EXPIRES_AT="):
                    lines.append(f"RIOT_KEY_EXPIRES_AT={exp_ts}\n")
                    found_exp = True
                else:
                    lines.append(line)
    if not found_key:
        lines.append(f"RIOT_API_KEY={new_key}\n")
    if not found_exp:
        lines.append(f"RIOT_KEY_EXPIRES_AT={exp_ts}\n")
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.environ["RIOT_API_KEY"] = new_key
    os.environ["RIOT_KEY_EXPIRES_AT"] = str(exp_ts)

CACHE_DIR = BASE_DIR / "data_cache"
MATCH_CACHE_DIR = CACHE_DIR / "matches"
TIMELINE_CACHE_DIR = CACHE_DIR / "timelines"
DDRAGON_CACHE_DIR = CACHE_DIR / "ddragon"

for d in [MATCH_CACHE_DIR, TIMELINE_CACHE_DIR, DDRAGON_CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)
