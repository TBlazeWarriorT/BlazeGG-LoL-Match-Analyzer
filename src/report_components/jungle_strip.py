from ..asset_cache import AssetManager
from ..i18n import get_text

def render_jungle_chronological(seq, lang: str = "en_US") -> str:
    if not seq:
        empty_lbl = get_text("no_neutral_objs", lang=lang)
        return f'<div class="empty-jungle-slot">{empty_lbl}</div>'
    items_html = []
    for item in seq:
        is_soul = item.get("is_soul", False)
        soul_class = "soul-dragon-badge" if is_soul else ""
        soul_title_tag = " • DRAGON SOUL!" if is_soul else ""
        items_html.append(
            f'<div class="jungle-badge-wrapper" title="[{item["time"]}] {item["name"]}{soul_title_tag}">'
            f'<img class="obj-badge-icon-lg {soul_class}" src="{AssetManager.get_asset_uri(item["asset_key"])}"/>'
            f'<span class="badge-time" style="{"color:#f59e0b; font-weight:800;" if is_soul else ""}">{item["time"]}</span>'
            f'</div>'
        )
    return "".join(items_html)
