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
        self._champions_by_id: Dict[str, str] = {}
        self._spells: Dict[str, Dict[str, str]] = {}
        self._runes: Dict[int, Dict[str, str]] = {}
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
        self._champ_images: Dict[str, str] = {}
        if cached_champs and "data" in cached_champs:
            for champ_id, details in cached_champs["data"].items():
                key = str(details.get("key"))
                name = details.get("name", champ_id)
                img_full = details.get("image", {}).get("full", f"{champ_id}.png")
                self._champions[key] = name
                self._champions_by_id[champ_id.lower()] = name
                self._champ_images[champ_id.lower()] = img_full
                self._champ_images[name.lower().replace(" ", "").replace("'", "")] = img_full

        spells_cache = DDRAGON_CACHE_DIR / f"spells_{self.version}_{self.language}.json"
        cached_spells = load_json(spells_cache)
        if not cached_spells:
            try:
                url = f"{BASE_CDN_URL}/{self.version}/data/{self.language}/summoner.json"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    cached_spells = resp.json()
                    save_json(spells_cache, cached_spells)
            except Exception:
                cached_spells = {}
        if cached_spells and "data" in cached_spells:
            for s_id, details in cached_spells["data"].items():
                s_key = str(details.get("key"))
                self._spells[s_key] = {
                    "name": details.get("name", s_id),
                    "icon": f"{BASE_CDN_URL}/{self.version}/img/spell/{details.get('image', {}).get('full', '')}"
                }

        runes_cache = DDRAGON_CACHE_DIR / f"runes_{self.version}_{self.language}.json"
        cached_runes = load_json(runes_cache)
        if not cached_runes:
            try:
                url = f"{BASE_CDN_URL}/{self.version}/data/{self.language}/runesReforged.json"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    cached_runes = resp.json()
                    save_json(runes_cache, cached_runes)
            except Exception:
                cached_runes = []
        if cached_runes and isinstance(cached_runes, list):
            for tree in cached_runes:
                tree_id = tree.get("id")
                tree_icon = tree.get("icon", "")
                self._runes[tree_id] = {
                    "name": tree.get("name", ""),
                    "icon": f"https://ddragon.leagueoflegends.com/cdn/img/{tree_icon}"
                }
                for slot in tree.get("slots", []):
                    for rune in slot.get("runes", []):
                        r_id = rune.get("id")
                        icon_path = rune.get("icon", "")
                        self._runes[r_id] = {
                            "name": rune.get("name", ""),
                            "icon": f"https://ddragon.leagueoflegends.com/cdn/img/{icon_path}"
                        }

    def get_spell_info(self, spell_id: int) -> Dict[str, str]:
        s = self._spells.get(str(spell_id))
        if s:
            return s
        return {"name": f"Spell {spell_id}", "icon": ""}

    def get_rune_info(self, rune_id: int) -> Dict[str, str]:
        r = self._runes.get(rune_id)
        if r:
            return r
        return {"name": f"Rune {rune_id}", "icon": ""}

    def get_rune_style_info(self, style_id: int) -> Dict[str, str]:
        r = self._runes.get(style_id)
        if r:
            return r
        return {"name": f"Style {style_id}", "icon": ""}

    def get_item_name(self, item_id: int) -> str:
        if not item_id or item_id == 0:
            return "Vazio"
        return self._items.get(str(item_id), f"Item {item_id}")

    def get_champion_name(self, key: int, fallback: str = "") -> str:
        return self._champions.get(str(key), fallback or f"Champ {key}")

    def get_clean_champion_name(self, raw_champ_name: str) -> str:
        if not raw_champ_name:
            return ""
        clean_key = raw_champ_name.replace(" ", "").replace("'", "").lower()
        return self._champions_by_id.get(clean_key, raw_champ_name)

    def get_champion_icon_url(self, champ_name: str) -> str:
        if not champ_name:
            return ""
        lookup_key = champ_name.replace(" ", "").replace("'", "").lower()
        img_file = self._champ_images.get(lookup_key)
        if not img_file:
            # Fallback
            clean_name = champ_name.replace(" ", "").replace("'", "")
            img_file = f"{clean_name}.png"
        return f"{BASE_CDN_URL}/{self.version}/img/champion/{img_file}"

    def get_item_icon_url(self, item_id: int) -> str:
        if not item_id or item_id == 0:
            return ""
        return f"{BASE_CDN_URL}/{self.version}/img/item/{item_id}.png"

