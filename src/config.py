import os
import time
import re
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
RIOT_KEY_EXPIRES_AT = os.getenv("RIOT_KEY_EXPIRES_AT", "") # Timestamp unix em segundos
DEFAULT_ROUTING = os.getenv("DEFAULT_ROUTING", "americas")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "br1")

def get_api_key() -> str:
    global RIOT_API_KEY
    return os.getenv("RIOT_API_KEY") or RIOT_API_KEY or ""

def get_key_expires_at() -> str:
    global RIOT_KEY_EXPIRES_AT
    return os.getenv("RIOT_KEY_EXPIRES_AT") or RIOT_KEY_EXPIRES_AT or ""

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
