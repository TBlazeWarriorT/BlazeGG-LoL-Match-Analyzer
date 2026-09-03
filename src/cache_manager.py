import json
import gzip
import lzma
from pathlib import Path
from typing import Optional, Any, List
from .config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR, CACHE_DIR

SESSION_FILE = CACHE_DIR / "last_session.json"

def _base_path(file_path: Path) -> Path:
    """Strips a known compressed suffix (.gz/.xz) if present, returning the bare .json path."""
    if file_path.suffix in (".gz", ".xz"):
        return file_path.with_suffix("")
    return file_path

def load_json(file_path: Path) -> Optional[Any]:
    """Loads JSON data, trying (in order) the new lzma format (.json.xz), the legacy
    gzip format (.json.gz), and a plain uncompressed .json — so files written before
    the lzma switch keep working without needing to be migrated."""
    base = _base_path(file_path)

    xz_path = base.with_suffix(base.suffix + ".xz")
    if xz_path.exists():
        try:
            with lzma.open(xz_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    gz_path = base.with_suffix(base.suffix + ".gz")
    if gz_path.exists():
        try:
            with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if base.exists():
        try:
            with open(base, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_json(file_path: Path, data: Any, compress: bool = False) -> None:
    """Saves data to JSON. When compress=True, writes lzma (.json.xz) — meaningfully
    smaller than gzip for this data with no extra dependency (stdlib). Cleans up any
    older-format sibling file for the same match so we don't keep both around."""
    base = _base_path(file_path)
    if compress:
        target_path = base.with_suffix(base.suffix + ".xz")
        with lzma.open(target_path, "wt", encoding="utf-8", preset=6) as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        for stale in (base.with_suffix(base.suffix + ".gz"), base):
            if stale.exists() and stale != target_path:
                try:
                    stale.unlink(missing_ok=True)
                except Exception:
                    pass
    else:
        with open(base, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def list_cache_files(directory: Path) -> List[Path]:
    """Returns all cache files (.json, .json.gz legacy, .json.xz) in directory."""
    if not directory.exists():
        return []
    return list(directory.glob("*.json")) + list(directory.glob("*.json.gz")) + list(directory.glob("*.json.xz"))

def get_cached_match(match_id: str) -> Optional[dict]:
    return load_json(MATCH_CACHE_DIR / f"{match_id}.json")

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

# event_engine.py never reads any other event type or field than these — verified by
# auditing every ev.get(...)/frame.get(...) call in that module. Deliberately narrow:
# there's no plan to ever show more timeline detail than a kill/objective/item-purchase
# breakpoint, so if that changes later the fix is to re-fetch (cache is disposable),
# not to keep hedging disk space against a feature that isn't coming.
_KEEP_EVENT_TYPES = {"CHAMPION_KILL", "ELITE_MONSTER_KILL", "ITEM_PURCHASED", "ITEM_SOLD", "ITEM_DESTROYED", "ITEM_UNDO"}
_KILL_EVENT_FIELDS = {"type", "timestamp", "killerId", "victimId", "assistingParticipantIds", "victimDamageReceived", "killerTeamId", "monsterType", "monsterSubType"}
_ITEM_EVENT_FIELDS = {"type", "timestamp", "participantId", "itemId", "beforeId", "afterId"}

def _filter_kill_damage(dmg_rec):
    """Keeps only the ultimate + summoner-spell damage instances in victimDamageReceived
    — that's all the report's combat-spell badges and ult-kill detection ever look at."""
    if not isinstance(dmg_rec, list):
        return dmg_rec
    return [
        d for d in dmg_rec
        if d.get("spellSlot") == 3 or any(k in str(d.get("spellName") or d.get("name") or "").lower() for k in ("summoner", "smite", "dot", "ignite", "snowball", "exhaust", "ultimate"))
    ]

def sanitize_timeline(data: dict) -> dict:
    """Distills a raw Riot timeline down to only what the report ever reads: kill/objective/
    item-purchase events (with only their used fields) and, per frame, gold/xp/level for
    everyone plus a full championStats snapshot only for whoever was a killer or victim in
    that frame — instead of Riot's full per-minute-per-participant stat block for all 10
    players, which the report only ever samples at kill moments anyway."""
    if not isinstance(data, dict):
        return data
    frames = data.get("info", {}).get("frames", [])

    new_frames = []
    last_frame_idx = len(frames) - 1
    for frame_idx, frame in enumerate(frames):
        # The final frame's championStats is read for every participant (end-of-game
        # stat card), not just whoever's kill/death happened to land in that frame.
        needed_pids = set() if frame_idx != last_frame_idx else {
            int(pid) for pid in frame.get("participantFrames", {}) if str(pid).isdigit()
        }
        kept_events = []
        for ev in frame.get("events", []):
            ev_type = ev.get("type")
            if ev_type not in _KEEP_EVENT_TYPES:
                continue
            if ev_type in ("CHAMPION_KILL", "ELITE_MONSTER_KILL"):
                trimmed = {k: v for k, v in ev.items() if k in _KILL_EVENT_FIELDS}
                if "victimDamageReceived" in trimmed:
                    filtered = _filter_kill_damage(trimmed["victimDamageReceived"])
                    if filtered:
                        trimmed["victimDamageReceived"] = filtered
                    else:
                        trimmed.pop("victimDamageReceived", None)
                if ev_type == "CHAMPION_KILL":
                    if ev.get("killerId"):
                        needed_pids.add(ev["killerId"])
                    if ev.get("victimId"):
                        needed_pids.add(ev["victimId"])
            else:
                trimmed = {k: v for k, v in ev.items() if k in _ITEM_EVENT_FIELDS}
            kept_events.append(trimmed)

        compact_pframes = {}
        for pid_str, pf in frame.get("participantFrames", {}).items():
            entry = {"totalGold": pf.get("totalGold", 0), "xp": pf.get("xp", 0), "level": pf.get("level", 1)}
            try:
                pid = int(pid_str)
            except (TypeError, ValueError):
                pid = None
            if pid in needed_pids:
                entry["championStats"] = pf.get("championStats", {})
            compact_pframes[pid_str] = entry

        new_frames.append({
            "timestamp": frame.get("timestamp", 0),
            "events": kept_events,
            "participantFrames": compact_pframes,
        })

    data["info"]["frames"] = new_frames
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
