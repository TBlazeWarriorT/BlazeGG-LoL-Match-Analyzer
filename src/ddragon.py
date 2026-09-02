import re
import requests
from typing import Dict, Any, List
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
    _instances: Dict[str, "DataDragon"] = {}

    def __new__(cls, language: str = "pt_BR"):
        if language not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[language] = instance
        return cls._instances[language]

    def __init__(self, language: str = "pt_BR"):
        if getattr(self, "_initialized", False):
            return
        self.language = language
        self.version = self._get_latest_version()
        self._items: Dict[str, str] = {}
        self._item_tooltips: Dict[str, str] = {}
        self._champions: Dict[str, str] = {}
        self._champions_by_id: Dict[str, str] = {}
        self._spells: Dict[str, Dict[str, str]] = {}
        self._runes: Dict[int, Dict[str, str]] = {}
        self._load_dictionaries()
        self._initialized = True

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
                s_info_obj = {
                    "name": s_name,
                    "icon": f"{BASE_CDN_URL}/{self.version}/img/spell/{details.get('image', {}).get('full', '')}",
                    "tooltip": s_tooltip.replace('"', '&quot;')
                }
                self._spells[s_key] = s_info_obj
                self._spells[s_id] = s_info_obj
                self._spells[s_id.lower()] = s_info_obj

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
            tree_sub_label = get_text("secondary_rune_tree", lang=self.language)
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

        self._raw_rune_trees = cached_runes if isinstance(cached_runes, list) else []

        # Load Arena Augments from CommunityDragon
        aug_cache = DDRAGON_CACHE_DIR / f"augments_{self.language}.json"
        cached_aug = load_json(aug_cache)
        if not cached_aug:
            try:
                lang_code = "default" if self.language == "en_US" else self.language.lower().replace("-", "_")
                url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/{lang_code}/v1/cherry-augments.json"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    cached_aug = resp.json()
                    save_json(aug_cache, cached_aug)
            except Exception:
                cached_aug = []

        self._augments: Dict[int, Dict[str, Any]] = {}
        if cached_aug and isinstance(cached_aug, list):
            for item in cached_aug:
                aid = item.get("id")
                if not aid:
                    continue
                name = item.get("nameTRA") or item.get("name") or f"Augment {aid}"
                rarity_raw = item.get("rarity", "kSilver")
                icon_raw = item.get("augmentSmallIconPath", "")
                clean_path = icon_raw.lower().replace("/lol-game-data/assets/", "")
                icon_url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/{clean_path}" if icon_raw else ""
                
                if rarity_raw == "kPrismatic":
                    r_name = get_text("rarity_prismatic", lang=self.language)
                    r_color = "#c084fc"
                    r_border = "#a855f7"
                elif rarity_raw == "kGold":
                    r_name = get_text("rarity_gold", lang=self.language)
                    r_color = "#fbbf24"
                    r_border = "#f59e0b"
                else:
                    r_name = get_text("rarity_silver", lang=self.language)
                    r_color = "#cbd5e1"
                    r_border = "#94a3b8"
                
                aug_header = f'<div style="display:flex; justify-content:space-between; align-items:center; gap:8px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px; margin-bottom:6px;"><b style="color:#f8fafc; font-size:0.85rem;">{name}</b><span style="color:{r_color}; font-size:0.75rem; font-weight:700;">{r_name}</span></div>'
                aug_sub = f'<div style="color:#94a3b8; font-size:0.75rem;">{get_text("arena_augment_subtitle", lang=self.language)}</div>'
                aug_tooltip = f'{aug_header}{aug_sub}'
                self._augments[aid] = {
                    "id": aid,
                    "name": name,
                    "rarity": rarity_raw,
                    "rarity_name": r_name,
                    "rarity_color": r_color,
                    "rarity_border": r_border,
                    "icon": icon_url,
                    "tooltip": aug_tooltip.replace('"', '&quot;')
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

    def get_spell_info(self, spell_id: Any) -> Dict[str, str]:
        s_str = str(spell_id)
        s = self._spells.get(s_str) or self._spells.get(s_str.lower())
        if s:
            return s
        s_lower = s_str.lower()
        if "dot" in s_lower or "ignite" in s_lower:
            return self._spells.get("summonerdot", {"name": "Ignite", "icon": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerDot.png"})
        if "smite" in s_lower:
            return self._spells.get("summonersmite", {"name": "Smite", "icon": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerSmite.png"})
        if "snowball" in s_lower or "mark" in s_lower:
            return self._spells.get("summonersnowball", {"name": "Mark", "icon": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerSnowball.png"})
        if "exhaust" in s_lower:
            return self._spells.get("summonerexhaust", {"name": "Exhaust", "icon": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerExhaust.png"})
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

    def get_augment_info(self, augment_id: int) -> Dict[str, Any]:
        if not augment_id:
            return {}
        return self._augments.get(augment_id, {
            "id": augment_id,
            "name": f"Augment {augment_id}",
            "rarity": "kSilver",
            "rarity_name": get_text("rarity_silver", lang=self.language),
            "rarity_color": "#cbd5e1",
            "rarity_border": "#94a3b8",
            "icon": "",
            "tooltip": f"Augment {augment_id}"
        })

    STAT_SHARDS = {
        5008: ("Dano Adaptativo (+9)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAdaptiveForceIcon.png"),
        5005: ("Velocidade de Ataque (+10%)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAttackSpeedIcon.png"),
        5007: ("Aceleração de Habilidade (+8)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsCDRScalingIcon.png"),
        5010: ("Velocidade de Movimento (+2%)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsMovementSpeedIcon.png"),
        5001: ("Vida Escalonável (+10-180)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsHealthScalingIcon.png"),
        5011: ("Vida Plana (+65)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsHealthScalingIcon.png"),
        5013: ("Tenacidade (+10%)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsTenacityIcon.png"),
        5002: ("Armadura (+6)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsArmorIcon.png"),
        5003: ("Resistência Mágica (+8)", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsMagicResIcon.png"),
    }

    def get_full_rune_tree_tooltip(self, perks_data: Dict[str, Any]) -> str:
        if not perks_data:
            return ""
        primary_id = perks_data.get("primary_style", 0)
        sub_id = perks_data.get("sub_style", 0)
        selected_perks = set(perks_data.get("selected_perks", []))
        stat_perks = perks_data.get("stat_perks", [])

        trees_by_id = {t["id"]: t for t in self._raw_rune_trees}
        primary_tree = trees_by_id.get(primary_id)
        sub_tree = trees_by_id.get(sub_id)

        if not primary_tree:
            return ""

        prim_rows_html = []
        for slot_idx, slot in enumerate(primary_tree.get("slots", [])):
            runes_row = []
            for r in slot.get("runes", []):
                rid = r.get("id")
                is_sel = rid in selected_perks
                r_icon = f"https://ddragon.leagueoflegends.com/cdn/img/{r.get('icon', '')}"
                r_name = r.get("name", "")
                r_size = "26px" if slot_idx == 0 else "20px"
                if is_sel:
                    runes_row.append(f'<img src="{r_icon}" style="width:{r_size}; height:{r_size}; border-radius:50%; border:1.5px solid #38bdf8; box-shadow:0 0 6px rgba(56,189,248,0.5); transform:scale(1.08);" title="{r_name}"/>')
                else:
                    runes_row.append(f'<img src="{r_icon}" style="width:{r_size}; height:{r_size}; border-radius:50%; opacity:0.25; filter:grayscale(80%);" title="{r_name}"/>')
            prim_rows_html.append(f'<div style="display:flex; justify-content:center; gap:12px; margin-bottom:6px;">{"".join(runes_row)}</div>')

        sub_rows_html = []
        if sub_tree:
            for slot in sub_tree.get("slots", [])[1:]:
                runes_row = []
                for r in slot.get("runes", []):
                    rid = r.get("id")
                    is_sel = rid in selected_perks
                    r_icon = f"https://ddragon.leagueoflegends.com/cdn/img/{r.get('icon', '')}"
                    r_name = r.get("name", "")
                    if is_sel:
                        runes_row.append(f'<img src="{r_icon}" style="width:20px; height:20px; border-radius:50%; border:1.5px solid #fbbf24; box-shadow:0 0 6px rgba(251,191,36,0.5); transform:scale(1.08);" title="{r_name}"/>')
                    else:
                        runes_row.append(f'<img src="{r_icon}" style="width:20px; height:20px; border-radius:50%; opacity:0.25; filter:grayscale(80%);" title="{r_name}"/>')
                sub_rows_html.append(f'<div style="display:flex; justify-content:center; gap:12px; margin-bottom:6px;">{"".join(runes_row)}</div>')

        stat_rows_html = []
        if stat_perks:
            stat_icons = []
            for s_id in stat_perks:
                s_info = self.STAT_SHARDS.get(s_id, ("Stat Shard", "https://ddragon.leagueoflegends.com/cdn/img/perk-images/StatMods/StatModsAdaptiveForceIcon.png"))
                stat_icons.append(f'<img src="{s_info[1]}" style="width:15px; height:15px; border-radius:50%; border:1px solid #94a3b8; background:rgba(255,255,255,0.05);" title="{s_info[0]}"/>')
            stat_rows_html.append(f'<div style="display:flex; justify-content:center; gap:12px; margin-top:8px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.08);">{"".join(stat_icons)}</div>')

        prim_tree_name = primary_tree.get("name", "")
        prim_tree_icon = f"https://ddragon.leagueoflegends.com/cdn/img/{primary_tree.get('icon', '')}"
        sub_tree_name = sub_tree.get("name", "") if sub_tree else ""
        sub_tree_icon = f"https://ddragon.leagueoflegends.com/cdn/img/{sub_tree.get('icon', '')}" if sub_tree else ""

        tooltip = f"""
        <div style="min-width:280px; padding:3px;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:5px;">
                    <img src="{prim_tree_icon}" style="width:18px; height:18px;"/>
                    <b style="color:#38bdf8; font-size:0.82rem;">{prim_tree_name}</b>
                </div>
                {f'<div style="display:flex; align-items:center; gap:5px;"><img src="{sub_tree_icon}" style="width:18px; height:18px;"/><b style="color:#fbbf24; font-size:0.82rem;">{sub_tree_name}</b></div>' if sub_tree else ''}
            </div>
            <div style="display:flex; justify-content:space-around; gap:16px;">
                <div style="flex:1;">{''.join(prim_rows_html)}</div>
                {f'<div style="flex:1; border-left:1px solid rgba(255,255,255,0.08); padding-left:14px;">{"".join(sub_rows_html)}</div>' if sub_rows_html else ''}
            </div>
            {''.join(stat_rows_html)}
        </div>
        """
        return tooltip.strip().replace('"', '&quot;').replace('\n', '')

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

