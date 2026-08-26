import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

RIOT_API_KEY = os.getenv("RIOT_API_KEY", "")
RIOT_KEY_EXPIRES_AT = os.getenv("RIOT_KEY_EXPIRES_AT", "") # Timestamp unix em segundos
DEFAULT_ROUTING = os.getenv("DEFAULT_ROUTING", "americas")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "br1")

CACHE_DIR = BASE_DIR / "data_cache"
MATCH_CACHE_DIR = CACHE_DIR / "matches"
TIMELINE_CACHE_DIR = CACHE_DIR / "timelines"
DDRAGON_CACHE_DIR = CACHE_DIR / "ddragon"

for d in [MATCH_CACHE_DIR, TIMELINE_CACHE_DIR, DDRAGON_CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)
