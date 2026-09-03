import requests
import base64
import io
from pathlib import Path
from typing import Dict
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False
from .config import CACHE_DIR

CDRAGON_CACHE_DIR = CACHE_DIR / "cdragon"
CDRAGON_CACHE_DIR.mkdir(parents=True, exist_ok=True)

CD_DRAGON_BASE = "https://raw.communitydragon.org/latest/game/assets/ux/announcements"
TEXTICONS_URL = "https://raw.communitydragon.org/latest/game/assets/ux/fonts/texticons.png"
HUDATLAS_URL = "https://raw.communitydragon.org/latest/game/assets/ux/lol/clarity_hudatlasupdate.png"

ASSETS = {
    "dragon_circle": {
        "url": f"{CD_DRAGON_BASE}/dragon_circle.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Cloud_DrakeSquare.png/48px-Cloud_DrakeSquare.png"
    },
    "dragon_circle_air": {
        "url": f"{CD_DRAGON_BASE}/dragon_circle_air.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Cloud_DrakeSquare.png/48px-Cloud_DrakeSquare.png"
    },
    "dragon_circle_chemtech": {
        "url": f"{CD_DRAGON_BASE}/dragon_circle_chemtech.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Chemtech_DrakeSquare.png/48px-Chemtech_DrakeSquare.png"
    },
    "dragon_circle_earth": {
        "url": f"{CD_DRAGON_BASE}/dragon_circle_earth.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Mountain_DrakeSquare.png/48px-Mountain_DrakeSquare.png"
    },
    "dragon_circle_fire": {
        "url": f"{CD_DRAGON_BASE}/dragon_circle_fire.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Infernal_DrakeSquare.png/48px-Infernal_DrakeSquare.png"
    },
    "dragon_circle_hextech": {
        "url": f"{CD_DRAGON_BASE}/dragon_circle_hextech.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Hextech_DrakeSquare.png/48px-Hextech_DrakeSquare.png"
    },
    "dragon_circle_water": {
        "url": f"{CD_DRAGON_BASE}/dragon_circle_water.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Ocean_DrakeSquare.png/48px-Ocean_DrakeSquare.png"
    },
    "sru_voidgrub_circle": {
        "url": f"{CD_DRAGON_BASE}/sru_voidgrub_circle.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/VoidgrubSquare.png/48px-VoidgrubSquare.png"
    },
    "sruriftherald_circle": {
        "url": f"{CD_DRAGON_BASE}/sruriftherald_circle.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Rift_HeraldSquare.png/48px-Rift_HeraldSquare.png"
    },
    "baron_circle": {
        "url": f"{CD_DRAGON_BASE}/baron_circle.png",
        "fallback": "https://wiki.leagueoflegends.com/en-us/images/thumb/Baron_NashorSquare.png/48px-Baron_NashorSquare.png"
    },
    "turret_blue_circle": {
        "url": "https://raw.communitydragon.org/latest/game/assets/characters/turret/hud/turret_blue_circle.png",
        "fallback": "https://raw.communitydragon.org/latest/game/assets/characters/turret/hud/turret_blue_circle.png"
    },
    "turret_red_circle": {
        "url": "https://raw.communitydragon.org/latest/game/assets/characters/turret/hud/turret_red_circle.png",
        "fallback": "https://raw.communitydragon.org/latest/game/assets/characters/turret/hud/turret_red_circle.png"
    },
    "inhibitor_blue_circle": {
        "url": "https://raw.communitydragon.org/latest/game/assets/characters/inhibitor/hud/inhibitor_blue_circle.png",
        "fallback": "https://raw.communitydragon.org/latest/game/assets/characters/inhibitor/hud/inhibitor_blue_circle.png"
    },
    "inhibitor_red_circle": {
        "url": "https://raw.communitydragon.org/latest/game/assets/characters/inhibitor/hud/inhibitor_red_circle.png",
        "fallback": "https://raw.communitydragon.org/latest/game/assets/characters/inhibitor/hud/inhibitor_red_circle.png"
    },
    "gromp_circle": {
        "url": "https://raw.communitydragon.org/latest/game/assets/characters/sru_gromp/hud/gromp_circle.png",
        "fallback": "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png"
    },
    "gromp_icon": {
        "url": "https://raw.communitydragon.org/latest/game/assets/characters/sru_gromp/hud/gromp_circle.png",
        "fallback": "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png"
    },
    "award_crown": {
        "url": "https://raw.communitydragon.org/latest/game/assets/items/icons2d/3056_demonkingscrown.png",
        "fallback": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/4644.png"
    },
    "award_smite": {
        "url": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/spell/SummonerSmite.png",
        "fallback": ""
    },
    "award_ie": {
        "url": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3031.png",
        "fallback": ""
    },
    "award_avarice": {
        "url": "https://raw.communitydragon.org/latest/game/assets/items/icons2d/773093_avarice_blade.png",
        "fallback": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/4403.png"
    },
    "award_might": {
        "url": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3110.png",
        "fallback": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3143.png"
    },
    "award_visionary": {
        "url": "https://raw.communitydragon.org/latest/game/assets/items/icons2d/772049_sightstone.png",
        "fallback": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/4643.png"
    },
    "oracle_lens": {
        "url": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3364.png",
        "fallback": ""
    },
    "stealth_ward": {
        "url": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3340.png",
        "fallback": ""
    },
    "control_ward": {
        "url": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/2055.png",
        "fallback": ""
    },
    "award_demolisher": {
        "url": "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/3181.png",
        "fallback": "https://raw.communitydragon.org/latest/game/assets/items/icons2d/3512_zzrot_portal.png"
    },
    "stat_hp": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/1/17/Health_icon.png/revision/latest/scale-to-width-down/15?cb=20240607103046", "fallback": ""},
    "stat_hpregen": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/3/31/Health_regeneration_icon.png/revision/latest/scale-to-width-down/15?cb=20240607102806", "fallback": ""},
    "stat_healshield": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/2/28/Heal_and_shield_power_icon.png/revision/latest/scale-to-width-down/15?cb=20240607102503", "fallback": ""},
    "stat_armor": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/f/f0/Armor_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203442", "fallback": ""},
    "stat_mr": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/8/84/Magic_resistance_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203539", "fallback": ""},
    "stat_tenacity": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/3/33/Tenacity_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203541", "fallback": ""},
    "stat_as": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/9/91/Attack_speed_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203443", "fallback": ""},
    "stat_ad": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/7/75/Attack_damage_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203443", "fallback": ""},
    "stat_ap": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/0/0a/Ability_power_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203441", "fallback": ""},
    "stat_crit": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/c/c6/Critical_strike_chance_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203445", "fallback": ""},
    "stat_critdmg": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/0/0f/Critical_strike_damage_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203445", "fallback": ""},
    "stat_armpen": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/6/64/Armor_penetration_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203442", "fallback": ""},
    "stat_mpen": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/6/62/Magic_penetration_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203538", "fallback": ""},
    "stat_lifesteal": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/7/76/Life_steal_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203537", "fallback": ""},
    "stat_omnivamp": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/3/35/Omnivamp_icon.png/revision/latest/scale-to-width-down/15?cb=20210120115930", "fallback": ""},
    "stat_ah": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/9/95/Cooldown_reduction_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203444", "fallback": ""},
    "stat_mana": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/8/8b/Mana_icon.png/revision/latest/scale-to-width-down/15?cb=20240607103302", "fallback": ""},
    "stat_manaregen": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/0/0c/Mana_regeneration_icon.png/revision/latest/scale-to-width-down/15?cb=20240607103627", "fallback": ""},
    "stat_energy": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/7/7d/Energy_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203447", "fallback": ""},
    "stat_energyregen": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/7/7e/Energy_regeneration_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203446", "fallback": ""},
    "stat_range": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/1/13/Range_icon.png/revision/latest/scale-to-width-down/15?cb=20170715002053", "fallback": ""},
    "stat_ms": {"url": "https://static.wikia.nocookie.net/leagueoflegends/images/e/ea/Movement_speed_icon.png/revision/latest/scale-to-width-down/15?cb=20170515203540", "fallback": ""}
}

class AssetManager:
    _data_uri_cache: Dict[str, str] = {}

    @classmethod
    def get_asset_uri(cls, asset_key: str) -> str:
        if asset_key in cls._data_uri_cache:
            return cls._data_uri_cache[asset_key]

        if asset_key in ("gold_icon", "xp_icon", "cs_icon", "swords_icon", "ranged_icon") or asset_key.startswith("stat_"):
            return cls._get_cropped_icon(asset_key)

        info = ASSETS.get(asset_key)
        if not info:
            return ""

        ext = ".png"
        local_path = CDRAGON_CACHE_DIR / f"{asset_key}{ext}"

        if local_path.exists():
            uri = cls._file_to_data_uri(local_path, ext)
            cls._data_uri_cache[asset_key] = uri
            return uri

        data = cls._download_bytes(info["url"])
        if not data:
            data = cls._download_bytes(info["fallback"])

        if data:
            with open(local_path, "wb") as f:
                f.write(data)
            uri = cls._file_to_data_uri(local_path, ext)
            cls._data_uri_cache[asset_key] = uri
            return uri

        return info["url"]

    @classmethod
    def _get_cropped_icon(cls, icon_type: str) -> str:
        local_path = CDRAGON_CACHE_DIR / f"{icon_type}.png"
        if local_path.exists():
            uri = cls._file_to_data_uri(local_path, ".png")
            cls._data_uri_cache[icon_type] = uri
            return uri

        # Se for o ícone de CS (Minion), recortamos do clarity_hudatlasupdate.png
        if icon_type == "cs_icon":
            atlas_path = CDRAGON_CACHE_DIR / "clarity_hudatlasupdate.png"
            atlas_bytes = b""
            if atlas_path.exists():
                with open(atlas_path, "rb") as f:
                    atlas_bytes = f.read()
            else:
                atlas_bytes = cls._download_bytes(HUDATLAS_URL)
                if atlas_bytes:
                    with open(atlas_path, "wb") as f:
                        f.write(atlas_bytes)

            if atlas_bytes:
                try:
                    img = Image.open(io.BytesIO(atlas_bytes))
                    box = (977, 302, 977 + 24, 302 + 24)
                    cropped = img.crop(box)
                    cropped.save(local_path, "PNG")
                    uri = cls._file_to_data_uri(local_path, ".png")
                    cls._data_uri_cache[icon_type] = uri
                    return uri
                except Exception:
                    pass

            fallback_url = "https://wiki.leagueoflegends.com/en-us/images/thumb/Minion_icon.png/20px-Minion_icon.png"
            data = cls._download_bytes(fallback_url)
            if data:
                with open(local_path, "wb") as f:
                    f.write(data)
                uri = cls._file_to_data_uri(local_path, ".png")
                cls._data_uri_cache[icon_type] = uri
                return uri
            return fallback_url

        STAT_BOXES = {
            "gold_icon": (45, 92, 45 + 24, 92 + 24),
            "xp_icon": (47, 263, 47 + 24, 263 + 24),
            "stat_mana": (0, 0, 24, 24),
            "stat_manaregen": (24, 0, 48, 24),
            "stat_mpen": (48, 0, 72, 24),
            "stat_mr": (72, 0, 96, 24),
            "stat_ms": (96, 0, 120, 24),
            "stat_ad": (0, 24, 24, 48),
            "stat_omnivamp": (24, 24, 48, 48),
            "stat_tenacity": (48, 24, 72, 48),
            "stat_ap": (96, 24, 120, 48),
            "stat_armor": (0, 48, 24, 72),
            "stat_as": (24, 48, 48, 72),
            "stat_ah": (48, 48, 72, 72),
            "stat_crit": (72, 48, 96, 72),
            "stat_hp": (96, 48, 120, 72),
            "stat_lifesteal": (0, 72, 24, 96),
            "stat_range": (72, 72, 96, 96),
            "stat_armpen": (96, 72, 120, 96),
            "stat_hpregen": (0, 96, 24, 120),
            "stat_critdmg": (24, 240, 48, 264),
            "stat_healshield": (70, 262, 94, 286),
            "swords_icon": (144, 263, 144 + 20, 263 + 20),
            "ranged_icon": (120, 263, 120 + 20, 263 + 20),
        }

        # Ouro, XP e Stats do texticons.png
        atlas_path = CDRAGON_CACHE_DIR / "texticons.png"
        atlas_bytes = b""
        if atlas_path.exists():
            with open(atlas_path, "rb") as f:
                atlas_bytes = f.read()
        else:
            atlas_bytes = cls._download_bytes(TEXTICONS_URL)
            if atlas_bytes:
                with open(atlas_path, "wb") as f:
                    f.write(atlas_bytes)

        if atlas_bytes:
            try:
                img = Image.open(io.BytesIO(atlas_bytes))
                box = STAT_BOXES.get(icon_type, (0, 0, 24, 24))
                cropped = img.crop(box)
                cropped.save(local_path, "PNG")
                uri = cls._file_to_data_uri(local_path, ".png")
                cls._data_uri_cache[icon_type] = uri
                return uri
            except Exception:
                pass

        fallback_url = "https://wiki.leagueoflegends.com/en-us/images/Gold_colored_icon.svg" if icon_type == "gold_icon" else "https://wiki.leagueoflegends.com/en-us/images/Experience_icon.png"
        data = cls._download_bytes(fallback_url)
        ext = ".svg" if ".svg" in fallback_url else ".png"
        if data:
            with open(local_path, "wb") as f:
                f.write(data)
            uri = cls._file_to_data_uri(local_path, ext)
            cls._data_uri_cache[icon_type] = uri
            return uri

        return fallback_url

    @classmethod
    def get_icon_css_block(cls, keys) -> str:
        """Emits one background-image rule per key so callers can reuse an icon via
        class name instead of re-embedding its full base64 data on every occurrence."""
        rules = []
        seen = set()
        for k in keys:
            if k in seen:
                continue
            seen.add(k)
            uri = cls.get_asset_uri(k)
            if uri:
                rules.append(f".aico-{k} {{ background-image: url('{uri}'); }}")
        return "".join(rules)

    @classmethod
    def preload_all_assets(cls):
        """Pre-downloads and crops all icons in background and warms up analysis engine."""
        keys = list(ASSETS.keys()) + ["gold_icon", "xp_icon", "cs_icon"]
        for k in keys:
            try:
                cls.get_asset_uri(k)
            except Exception:
                pass

        # Warm up DataDragon dictionaries and template engines
        try:
            from .ddragon import DataDragon
            dd_pt = DataDragon(language="pt_BR")
            dd_en = DataDragon(language="en_US")
            import src.event_engine
            import src.html_report
            import src.report_components
        except Exception:
            pass

    @staticmethod
    def _download_bytes(url: str) -> bytes:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return b""

    @staticmethod
    def _file_to_data_uri(path: Path, ext: str) -> str:
        mime = "image/svg+xml" if ext == ".svg" else "image/png"
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
