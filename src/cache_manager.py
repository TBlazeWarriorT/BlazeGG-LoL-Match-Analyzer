import json
import gzip
from pathlib import Path
from typing import Optional, Any, List
from .config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR, CACHE_DIR

SESSION_FILE = CACHE_DIR / "last_session.json"

def load_json(file_path: Path) -> Optional[Any]:
    """Loads JSON data from file, supporting both .json.gz (compressed) and standard .json."""
    gz_path = file_path if file_path.name.endswith(".gz") else file_path.with_suffix(file_path.suffix + ".gz")
    raw_path = file_path if not file_path.name.endswith(".gz") else file_path.with_suffix("")

    # Try compressed version first
    if gz_path.exists():
        try:
            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback to uncompressed version if exists
    if raw_path.exists():
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_json(file_path: Path, data: Any, compress: bool = False) -> None:
    """Saves data to JSON, optionally compressed with gzip (.json.gz)."""
    if compress:
        target_path = file_path if file_path.name.endswith(".gz") else file_path.with_suffix(file_path.suffix + ".gz")
        with gzip.open(target_path, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        # Clean up legacy uncompressed file if exists
        uncompressed = target_path.with_suffix("")
        if uncompressed.exists() and uncompressed != target_path:
            try:
                uncompressed.unlink(missing_ok=True)
            except Exception:
                pass
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def list_cache_files(directory: Path) -> List[Path]:
    """Returns all cache files (.json and .json.gz) in directory."""
    if not directory.exists():
        return []
    return list(directory.glob("*.json")) + list(directory.glob("*.json.gz"))

def get_cached_match(match_id: str) -> Optional[dict]:
    return load_json(MATCH_CACHE_DIR / f"{match_id}.json.gz")

MAX_CACHE_BYTES = 1024 * 1024 * 1024  # 1 GB Cap
MAX_MATCH_FILES = 2500

def cleanup_cache_if_needed():
    """Keeps match and timeline cache within disk limit by purging oldest unaccessed files."""
    try:
        match_files = list_cache_files(MATCH_CACHE_DIR)
        timeline_files = list_cache_files(TIMELINE_CACHE_DIR)
        total_files = match_files + timeline_files
        
        total_size = sum(f.stat().st_size for f in total_files if f.is_file())
        
        if total_size > MAX_CACHE_BYTES or len(match_files) > MAX_MATCH_FILES:
            sorted_files = sorted(total_files, key=lambda f: f.stat().st_mtime)
            for f in sorted_files:
                current_match_files = list_cache_files(MATCH_CACHE_DIR)
                if total_size <= (MAX_CACHE_BYTES * 0.8) and len(current_match_files) <= (MAX_MATCH_FILES * 0.8):
                    break
                try:
                    total_size -= f.stat().st_size
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass

TIMELINE_EVENT_BLACKLIST_KEYS = (
    "victimDamageReceived",
    "victimDamageDealt",
    "victimTeamfightDamageReceived",
    "victimTeamfightDamageDealt",
)

def sanitize_timeline(data: dict) -> dict:
    """Retains only compact combat summoner spells in victimDamageReceived, discarding heavy skill logs to save disk."""
    if not isinstance(data, dict):
        return data
    frames = data.get("info", {}).get("frames", [])
    for frame in frames:
        for ev in frame.get("events", []):
            if ev.get("type") == "CHAMPION_KILL":
                dmg_rec = ev.get("victimDamageReceived", [])
                if isinstance(dmg_rec, list):
                    filtered_spells = [
                        d for d in dmg_rec
                        if d.get("spellSlot") == 3 or any(k in str(d.get("spellName") or d.get("name") or "").lower() for k in ("summoner", "smite", "dot", "ignite", "snowball", "exhaust", "ultimate"))
                    ]
                    if filtered_spells:
                        ev["victimDamageReceived"] = filtered_spells
                    else:
                        ev.pop("victimDamageReceived", None)
                for key in ("victimDamageDealt", "victimTeamfightDamageReceived", "victimTeamfightDamageDealt"):
                    ev.pop(key, None)
    return data

def save_cached_match(match_id: str, data: dict, target_puuid: str = "") -> None:
    if target_puuid and "metadata" in data:
        data["metadata"]["target_puuid"] = target_puuid
    save_json(MATCH_CACHE_DIR / f"{match_id}.json.gz", data, compress=True)
    cleanup_cache_if_needed()

def get_cached_timeline(match_id: str) -> Optional[dict]:
    return load_json(TIMELINE_CACHE_DIR / f"{match_id}.json.gz")

def save_cached_timeline(match_id: str, data: dict) -> None:
    sanitized = sanitize_timeline(data)
    save_json(TIMELINE_CACHE_DIR / f"{match_id}.json.gz", sanitized, compress=True)
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
