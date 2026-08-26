import requests
import base64
import io
from pathlib import Path
from typing import Dict
from PIL import Image
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
    }
}

class AssetManager:
    _data_uri_cache: Dict[str, str] = {}

    @classmethod
    def get_asset_uri(cls, asset_key: str) -> str:
        if asset_key in cls._data_uri_cache:
            return cls._data_uri_cache[asset_key]

        if asset_key in ("gold_icon", "xp_icon", "cs_icon"):
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
                    # TopLeft (979, 303) 19x23 ajustado com 24x24
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

        # Ouro e XP do texticons.png
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
                if icon_type == "gold_icon":
                    box = (45, 92, 45 + 24, 92 + 24)
                else:
                    box = (47, 263, 47 + 24, 263 + 24)

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
