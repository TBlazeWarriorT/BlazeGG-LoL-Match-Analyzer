import json
from pathlib import Path
from typing import Optional, Any
from .config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR, CACHE_DIR

SESSION_FILE = CACHE_DIR / "last_session.json"

def load_json(file_path: Path) -> Optional[Any]:
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_json(file_path: Path, data: Any) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_cached_match(match_id: str) -> Optional[dict]:
    return load_json(MATCH_CACHE_DIR / f"{match_id}.json")

def save_cached_match(match_id: str, data: dict) -> None:
    save_json(MATCH_CACHE_DIR / f"{match_id}.json", data)

def get_cached_timeline(match_id: str) -> Optional[dict]:
    return load_json(TIMELINE_CACHE_DIR / f"{match_id}.json")

def save_cached_timeline(match_id: str, data: dict) -> None:
    save_json(TIMELINE_CACHE_DIR / f"{match_id}.json", data)

def set_last_viewed(match_id: str, puuid: str, riot_id: str = ""):
    save_json(SESSION_FILE, {
        "match_id": match_id,
        "puuid": puuid,
        "riot_id": riot_id
    })

def get_last_viewed() -> Optional[dict]:
    return load_json(SESSION_FILE)

def save_session(game_name: str, tag_line: str, puuid: str, match_id: str = ""):
    save_json(SESSION_FILE, {
        "game_name": game_name,
        "tag_line": tag_line,
        "riot_id": f"{game_name}#{tag_line}",
        "puuid": puuid,
        "match_id": match_id
    })

def get_last_session() -> Optional[dict]:
    return load_json(SESSION_FILE)
