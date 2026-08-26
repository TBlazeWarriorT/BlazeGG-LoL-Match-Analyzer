import requests
from typing import Dict
from .config import DDRAGON_CACHE_DIR
from .cache_manager import load_json, save_json

DDRAGON_VERSION_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
BASE_CDN_URL = "https://ddragon.leagueoflegends.com/cdn"

class DataDragon:
    def __init__(self, language: str = "pt_BR"):
        self.language = language
        self.version = self._get_latest_version()
        self._items: Dict[str, str] = {}
        self._champions: Dict[str, str] = {}
        self._load_dictionaries()

    def _get_latest_version(self) -> str:
        cache_path = DDRAGON_CACHE_DIR / "versions.json"
        cached = load_json(cache_path)
        if cached and isinstance(cached, list) and len(cached) > 0:
            return cached[0]
        try:
            resp = requests.get(DDRAGON_VERSION_URL, timeout=10)
            if resp.status_code == 200:
                versions = resp.json()
                save_json(cache_path, versions)
                return versions[0]
        except Exception:
            pass
        return "14.16.1"

    def _load_dictionaries(self) -> None:
        items_cache = DDRAGON_CACHE_DIR / f"items_{self.version}_{self.language}.json"
        cached_items = load_json(items_cache)
        if not cached_items:
            try:
                url = f"{BASE_CDN_URL}/{self.version}/data/{self.language}/item.json"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    cached_items = resp.json()
                    save_json(items_cache, cached_items)
            except Exception:
                cached_items = {}
        if cached_items and "data" in cached_items:
            for item_id, details in cached_items["data"].items():
                self._items[str(item_id)] = details.get("name", f"Item {item_id}")

        champs_cache = DDRAGON_CACHE_DIR / f"champions_{self.version}_{self.language}.json"
        cached_champs = load_json(champs_cache)
        if not cached_champs:
            try:
                url = f"{BASE_CDN_URL}/{self.version}/data/{self.language}/champion.json"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    cached_champs = resp.json()
                    save_json(champs_cache, cached_champs)
            except Exception:
                cached_champs = {}
        if cached_champs and "data" in cached_champs:
            for champ_id, details in cached_champs["data"].items():
                key = str(details.get("key"))
                self._champions[key] = details.get("name", champ_id)

    def get_item_name(self, item_id: int) -> str:
        if not item_id or item_id == 0:
            return "Vazio"
        return self._items.get(str(item_id), f"Item {item_id}")

    def get_champion_name(self, key: int, fallback: str = "") -> str:
        return self._champions.get(str(key), fallback or f"Champ {key}")
