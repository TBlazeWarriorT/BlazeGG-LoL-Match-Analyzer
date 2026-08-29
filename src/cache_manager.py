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

MAX_CACHE_BYTES = 1024 * 1024 * 1024  # 1 GB Cap
MAX_MATCH_FILES = 2500

def cleanup_cache_if_needed():
    """Keeps match and timeline cache within disk limit by purging oldest unaccessed files."""
    try:
        match_files = list(MATCH_CACHE_DIR.glob("*.json"))
        timeline_files = list(TIMELINE_CACHE_DIR.glob("*.json"))
        total_files = match_files + timeline_files
        
        total_size = sum(f.stat().st_size for f in total_files if f.is_file())
        
        if total_size > MAX_CACHE_BYTES or len(match_files) > MAX_MATCH_FILES:
            # Sort files by last modification/access time (oldest first)
            sorted_files = sorted(total_files, key=lambda f: f.stat().st_mtime)
            for f in sorted_files:
                if total_size <= (MAX_CACHE_BYTES * 0.8) and len(list(MATCH_CACHE_DIR.glob("*.json"))) <= (MAX_MATCH_FILES * 0.8):
                    break
                try:
                    total_size -= f.stat().st_size
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass

def save_cached_match(match_id: str, data: dict, target_puuid: str = "") -> None:
    if target_puuid and "metadata" in data:
        data["metadata"]["target_puuid"] = target_puuid
    save_json(MATCH_CACHE_DIR / f"{match_id}.json", data)
    cleanup_cache_if_needed()

def get_cached_timeline(match_id: str) -> Optional[dict]:
    return load_json(TIMELINE_CACHE_DIR / f"{match_id}.json")

def save_cached_timeline(match_id: str, data: dict) -> None:
    save_json(TIMELINE_CACHE_DIR / f"{match_id}.json", data)
    cleanup_cache_if_needed()

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
