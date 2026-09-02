import re
import requests
from typing import Dict
from .config import DDRAGON_CACHE_DIR
from .cache_manager import load_json, save_json
from .i18n import get_text

DDRAGON_VERSION_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
BASE_CDN_URL = "https://ddragon.leagueoflegends.com/cdn"

QUEUE_ALIASES: Dict[int, int] = {
    490: 480,   # Quickplay
    720: 700,   # Clash ARAM -> Clash
    840: 830,   # Co-op vs AI variants -> 830
    850: 830,
    870: 830,
    880: 830,
    890: 830,
    960: 950,   # Doom Bots
    1010: 900,  # ARURF Snowdown -> ARURF
    1710: 1700, # Arena
    1820: 1810, # Swarm variants -> 1810
    1830: 1810,
    1840: 1810,
    1900: 76,   # Pick URF -> URF
    2010: 2000, # Tutorial variants -> 2000
    2020: 2000,
}

class DataDragon:
    def __init__(self, language: str = "pt_BR"):
        self.language = language
        self.version = self._get_latest_version()
        self._items: Dict[str, str] = {}
        self._item_tooltips: Dict[str, str] = {}
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
        self._item_crit: Dict[int, int] = {}
        self._item_tooltips: Dict[str, str] = {}
        if cached_items and "data" in cached_items:
            for item_id, details in cached_items["data"].items():
                name = details.get("name", f"Item {item_id}")
                self._items[str(item_id)] = name
                crit = details.get("stats", {}).get("FlatCritChanceMod", 0)
                if crit > 0:
                    self._item_crit[int(item_id)] = round(crit * 100)

                gold_total = details.get("gold", {}).get("total", 0)
                raw_desc = details.get("description", "")
                plaintext = details.get("plaintext", "")

                desc = raw_desc
                if desc:
                    desc = re.sub(r'</?(?:mainText|stats|rarity\w+|keyword\w+|status|scale\w+|unique)>', '', desc, flags=re.IGNORECASE)
                    desc = re.sub(r'<attention>(.*?)</attention>', r'<b style="color:#fb923c;">\1</b>', desc, flags=re.IGNORECASE | re.DOTALL)
                    desc = re.sub(r'<passive>(.*?)</passive>', r'<b style="color:#fbbf24;">\1</b>', desc, flags=re.IGNORECASE | re.DOTALL)
                    desc = re.sub(r'<active>(.*?)</active>', r'<b style="color:#34d399;">\1</b>', desc, flags=re.IGNORECASE | re.DOTALL)
                    desc = re.sub(r'<rules>(.*?)</rules>', r'<span style="color:#94a3b8; font-size:0.75rem;">\1</span>', desc, flags=re.IGNORECASE | re.DOTALL)
                    desc = re.sub(r'<(?!/?(?:br|b|span|div)\b)[^>]+>', '', desc)
                    desc = re.sub(r'(?:<br\s*/?>\s*){3,}', '<br><br>', desc)
                    desc = re.sub(r'^(?:<br\s*/?>|\s)+|(?:<br\s*/?>|\s)+$', '', desc).strip()
                elif plaintext:
                    desc = f'<span style="color:#94a3b8;">{plaintext}</span>'

                gold_badge = f'<div style="display:inline-flex; align-items:center; gap:4px; color:#fbbf24; font-weight:700; white-space:nowrap;">{gold_total} <i class="stat-ico ico-gold" style="width:12px; height:12px; display:inline-block;"></i></div>' if gold_total > 0 else ""
                header = f'<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px; margin-bottom:6px;"><b style="color:#f8fafc; font-size:0.85rem;">{name}</b>{gold_badge}</div>'
                
                tooltip_html = f'{header}<div>{desc}</div>' if desc else f'{header}'
                self._item_tooltips[str(item_id)] = tooltip_html.replace('"', '&quot;')

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
        self._champ_ranges: Dict[str, int] = {}
        if cached_champs and "data" in cached_champs:
            for champ_id, details in cached_champs["data"].items():
                key = str(details.get("key"))
                name = details.get("name", champ_id)
                img_full = details.get("image", {}).get("full", f"{champ_id}.png")
                attack_range = int(details.get("stats", {}).get("attackrange", 125))
                self._champions[key] = name
                self._champions_by_id[champ_id.lower()] = name
                self._champ_images[champ_id.lower()] = img_full
                self._champ_images[name.lower().replace(" ", "").replace("'", "")] = img_full
                self._champ_ranges[champ_id.lower()] = attack_range
                self._champ_ranges[name.lower().replace(" ", "").replace("'", "")] = attack_range

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
                s_name = details.get("name", s_id)
                cd_val = details.get("cooldownBurn", "")
                cd_badge = f'<span style="color:#94a3b8; font-size:0.75rem; font-weight:600;">{cd_val}s CD</span>' if cd_val else ""
                s_header = f'<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px; margin-bottom:6px;"><b style="color:#f8fafc; font-size:0.85rem;">{s_name}</b>{cd_badge}</div>'
                s_desc = details.get("description", "").strip()
                s_desc = re.sub(r'<[^>]+>', '', s_desc).strip()
                s_tooltip = f'{s_header}<div>{s_desc}</div>' if s_desc else f'{s_header}'
                self._spells[s_key] = {
                    "name": s_name,
                    "icon": f"{BASE_CDN_URL}/{self.version}/img/spell/{details.get('image', {}).get('full', '')}",
                    "tooltip": s_tooltip.replace('"', '&quot;')
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
            tree_sub_label = "Árvore de Runas Secundária" if self.language == "pt_BR" else "Secondary Rune Tree"
            for tree in cached_runes:
                tree_id = tree.get("id")
                tree_icon = tree.get("icon", "")
                tree_name = tree.get("name", "")
                tree_header = f'<div style="border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px; margin-bottom:6px;"><b style="color:#f8fafc; font-size:0.85rem;">{tree_name}</b></div>'
                tree_tooltip = f'{tree_header}<div style="color:#94a3b8; font-size:0.75rem;">{tree_sub_label}</div>'
                self._runes[tree_id] = {
                    "name": tree_name,
                    "icon": f"https://ddragon.leagueoflegends.com/cdn/img/{tree_icon}",
                    "tooltip": tree_tooltip.replace('"', '&quot;')
                }
                for slot in tree.get("slots", []):
                    for rune in slot.get("runes", []):
                        r_id = rune.get("id")
                        icon_path = rune.get("icon", "")
                        r_name = rune.get("name", "")
                        r_desc = rune.get("shortDesc", "")
                        if r_desc:
                            r_desc = re.sub(r'</?lol-uikit-tooltipped-keyword[^>]*>', '', r_desc)
                            r_desc = re.sub(r'<attention>(.*?)</attention>', r'<b style="color:#fb923c;">\1</b>', r_desc)
                            r_desc = re.sub(r'<(?!/?(?:br|b|span|div)\b)[^>]+>', '', r_desc)
                            r_desc = re.sub(r'^(?:<br\s*/?>|\s)+|(?:<br\s*/?>|\s)+$', '', r_desc).strip()
                        r_header = f'<div style="border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px; margin-bottom:6px;"><b style="color:#f8fafc; font-size:0.85rem;">{r_name}</b></div>'
                        r_tooltip = f'{r_header}<div>{r_desc}</div>' if r_desc else f'{r_header}'
                        self._runes[r_id] = {
                            "name": r_name,
                            "icon": f"https://ddragon.leagueoflegends.com/cdn/img/{icon_path}",
                            "tooltip": r_tooltip.replace('"', '&quot;')
                        }

        # Load queues.json from Riot Docs CDN
        queues_cache = DDRAGON_CACHE_DIR / "queues.json"
        cached_queues = load_json(queues_cache)
        if not cached_queues:
            try:
                url = "https://static.developer.riotgames.com/docs/lol/queues.json"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    cached_queues = resp.json()
                    save_json(queues_cache, cached_queues)
            except Exception:
                cached_queues = []
        self._queues: Dict[int, Dict[str, str]] = {}
        if cached_queues and isinstance(cached_queues, list):
            for q in cached_queues:
                qid = q.get("queueId")
                if qid is not None:
                    self._queues[qid] = {
                        "map": q.get("map") or "",
                        "description": q.get("description") or "",
                        "notes": q.get("notes") or ""
                    }

    def get_queue_raw_description(self, queue_id: int) -> str:
        q = self._queues.get(queue_id, {})
        desc = q.get("description") or ""
        if desc.endswith(" games"):
            desc = desc[:-6]
        elif desc.endswith(" Games"):
            desc = desc[:-6]
        return desc.strip()

    def get_queue_name(self, queue_id: int, lang: str = None) -> str:
        target_lang = lang or self.language
        resolved_id = QUEUE_ALIASES.get(queue_id, queue_id)
        key = f"queue_{resolved_id}"
        translated = get_text(key, lang=target_lang)
        if translated != key:
            return translated

        raw_desc = self.get_queue_raw_description(queue_id)
        if raw_desc:
            return raw_desc

        return get_text("queue_0" if queue_id == 0 else "queue_featured", lang=target_lang)

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

    def get_item_tooltip(self, item_id: int) -> str:
        if not item_id or item_id == 0:
            return ""
        return self._item_tooltips.get(str(item_id), self._items.get(str(item_id), f"Item {item_id}"))

    def get_item_crit_chance(self, item_id: int) -> int:
        if not item_id or item_id == 0:
            return 0
        return self._item_crit.get(int(item_id), 0)

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

    def get_champion_attack_range(self, champ_name: str) -> int:
        if not champ_name:
            return 125
        lookup_key = champ_name.replace(" ", "").replace("'", "").lower()
        return self._champ_ranges.get(lookup_key, 125)

