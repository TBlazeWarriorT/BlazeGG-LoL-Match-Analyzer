from typing import Dict, Any, List
from ..i18n import get_text

def render_multikills_section(multikills_data: List[Dict[str, Any]], lang: str = "pt_BR") -> str:
    if not multikills_data:
        return ""
    
    mk_cards = []
    for mk in multikills_data:
        streak_type = mk.get("streak_type", "double")
        title = mk.get("title", "MULTIKILL")
        badge_icon = mk.get("badge_icon", "⚔️")
        k_icon = mk.get("killer_icon", "")
        k_champ = mk.get("killer_champ", "")
        k_name = mk.get("killer_name", "")
        start_time = mk.get("start_time", "00:00")
        victims = mk.get("victims", [])

        if streak_type == "penta":
            card_border = "border: 1px solid rgba(239, 68, 68, 0.7); box-shadow: 0 0 14px rgba(239, 68, 68, 0.25);"
            badge_bg = "background: linear-gradient(90deg, #ef4444, #dc2626); color: #fff;"
        elif streak_type == "quadra":
            card_border = "border: 1px solid rgba(192, 38, 211, 0.6); box-shadow: 0 0 12px rgba(192, 38, 211, 0.2);"
            badge_bg = "background: linear-gradient(90deg, #c026d3, #db2777); color: #fff;"
        elif streak_type == "triple":
            card_border = "border: 1px solid rgba(234, 88, 12, 0.5);"
            badge_bg = "background: linear-gradient(90deg, #ea580c, #f59e0b); color: #fff;"
        else:
            card_border = "border: 1px solid #1f293d;"
            badge_bg = "background: #1e293b; color: #94a3b8;"

        victims_html = "".join([
            f'<img class="multikill-victim-icon" src="{v.get("icon", "")}" title="{v.get("champ", "")} ({v.get("name", "")})"/>'
            for v in victims
        ])

        mk_cards.append(f"""
        <div class="multikill-card" style="{card_border}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="multikill-badge" style="{badge_bg}">{title}! {badge_icon}</span>
                <span class="multikill-time">⏱️ {start_time}</span>
            </div>
            
            <div class="multikill-killer-info">
                <img class="multikill-avatar" src="{k_icon}" alt="{k_champ}"/>
                <div style="overflow:hidden;">
                    <div class="multikill-killer-champ">{k_champ}</div>
                    <div class="multikill-killer-name">{k_name}</div>
                </div>
            </div>

            <div style="margin-top:auto; padding-top:10px; border-top:1px solid #1e293b;">
                <div style="font-size:0.72rem; color:var(--text-muted); margin-bottom:6px; font-weight:600;">{get_text('eliminated', lang=lang).capitalize()} ({len(victims)}):</div>
                <div class="multikill-victims-flex">
                    {victims_html}
                </div>
            </div>
        </div>
        """)

    return f"""
    <div class="card">
        <h3 style="margin:0 0 14px 0;">{get_text('multikills_title', lang=lang)}</h3>
        <div class="multikills-scroll-container">
            {"".join(mk_cards)}
        </div>
    </div>
    """

