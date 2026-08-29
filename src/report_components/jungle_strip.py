from ..asset_cache import AssetManager
from ..i18n import get_text

def render_jungle_chronological(seq, lang: str = "en_US") -> str:
    if not seq:
        empty_lbl = get_text("no_neutral_objs", lang=lang)
        return f'<div class="empty-jungle-slot">{empty_lbl}</div>'
    items_html = []
    for item in seq:
        is_soul = item.get("is_soul", False)
        asset_key = str(item.get("asset_key", ""))
        name_str = str(item.get("name", "")).upper()
        is_baron = "BARON" in asset_key.upper() or "BARON" in name_str
        is_elder = "ELDER" in asset_key.upper() or "ELDER" in name_str or "ANCIÃO" in name_str

        glow_class = ""
        time_style = ""
        if is_soul:
            glow_class = "soul-dragon-badge"
            time_style = "color:#fbbf24; font-weight:800;"
        elif is_baron:
            glow_class = "baron-badge"
            time_style = "color:#c084fc; font-weight:800;"
        elif is_elder:
            glow_class = "elder-badge"
            time_style = "color:#f8fafc; font-weight:800;"

        soul_title_tag = " • DRAGON SOUL!" if is_soul else ""
        items_html.append(
            f'<div class="jungle-badge-wrapper" title="[{item["time"]}] {item["name"]}{soul_title_tag}">'
            f'<img class="obj-badge-icon-lg {glow_class}" src="{AssetManager.get_asset_uri(item["asset_key"])}"/>'
            f'<span class="badge-time" style="{time_style}">{item["time"]}</span>'
            f'</div>'
        )
    return "".join(items_html)
