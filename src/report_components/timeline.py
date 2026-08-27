from typing import Dict, Any, Tuple
from ..asset_cache import AssetManager
from ..i18n import get_text
from ..event_engine import clean_monster_name

def render_timeline_section(data: Dict[str, Any], lang: str = "pt_BR") -> Tuple[str, str, str]:
    events_list_items = []
    for idx, ev in enumerate(data.get("key_events", [])):
        t = ev.get("time", "00:00")
        ev_type = ev.get("type", "kill")
        extra_class = "timeline-hidden" if idx >= 20 else ""
        
        if ev_type == "objective":
            icon_uri = AssetManager.get_asset_uri(ev.get("asset_key", ""))
            slain_txt = get_text("slain_by", lang=lang)
            m_type = ev.get("monster_type", "")
            m_sub = ev.get("monster_sub_type", "")
            obj_desc = clean_monster_name(m_type, m_sub, lang=lang) if m_type else ev.get("desc", "")
            events_list_items.append(f"""
            <li class="event-item event-obj {extra_class}">
                <span class="event-time">{t}</span>
                <img class="event-avatar" src="{icon_uri}"/>
                <span class="event-desc"><b>{obj_desc}</b> {slain_txt} <b>{ev['killer_champ']}</b> ({ev['killer_name']})</span>
            </li>
            """)
        else:
            streak = ev.get("streak", "normal")
            streak_class = ""
            streak_badge = ""
            if streak == "penta":
                streak_class = "event-penta"
                streak_badge = '<span class="multi-badge badge-penta">PENTAKILL! 👑</span>'
            elif streak == "quadra":
                streak_class = "event-quadra"
                streak_badge = '<span class="multi-badge badge-penta" style="background:linear-gradient(90deg, #c026d3, #db2777); box-shadow: 0 0 10px rgba(192, 38, 211, 0.5);">QUADRA KILL! 🔥</span>'

            elif streak == "triple":
                streak_class = "event-multi"
                streak_badge = '<span class="multi-badge badge-multi" style="background:linear-gradient(90deg, #ea580c, #f59e0b);">TRIPLE KILL! ⚔️</span>'
            elif streak == "double":
                streak_class = "event-multi"
                streak_badge = '<span class="multi-badge badge-multi">DOUBLE KILL! ⚔️</span>'

            elim_txt = get_text("eliminated", lang=lang)
            c_ast = ev.get('assists_count', 0)
            ast_label = get_text("assists_plural", lang=lang) if c_ast > 1 else get_text("assists", lang=lang)
            assists_txt = f" (+{c_ast} {ast_label})" if c_ast > 0 else f" <span class='tag-solokill'>{get_text('solo_tag', lang=lang)}</span>"

            events_list_items.append(f"""
            <li class="event-item event-kill {streak_class} {extra_class}">
                <span class="event-time">{t}</span>
                <div class="event-kill-duel">
                    <img class="event-avatar" src="{ev['killer_icon']}" title="{ev['killer_champ']}"/>
                    <span class="event-arrow">⚔️</span>
                    <img class="event-avatar" src="{ev['victim_icon']}" title="{ev['victim_champ']}"/>
                </div>
                <span class="event-desc">
                    <b>{ev['killer_champ']}</b> ({ev['killer_name']}) {elim_txt} <b>{ev['victim_champ']}</b> ({ev['victim_name']}){assists_txt}
                </span>
                {streak_badge}
            </li>
            """)

    total_events_count = len(events_list_items)
    remaining_events = total_events_count - 20
    timeline_toggle_btn = ""
    timeline_top_toggle_btn = ""
    if remaining_events > 0:
        btn_text = get_text("show_more_events", lang=lang, count=remaining_events)
        timeline_top_toggle_btn = f"""
        <button id="toggleTimelineTopBtn" class="btn" style="background:#1e293b; border:1px solid var(--card-border); color:#38bdf8; font-weight:700; font-size:0.78rem; padding:4px 12px; border-radius:6px; cursor:pointer;" onclick="toggleTimeline()">{btn_text}</button>
        """
        timeline_toggle_btn = f"""
        <div style="text-align:center; margin-top:14px;">
            <button id="toggleTimelineBtn" class="btn" style="background:#1e293b; border:1px solid var(--card-border); color:#38bdf8; font-weight:700; font-size:0.85rem; padding:8px 18px; border-radius:8px; cursor:pointer;" onclick="toggleTimeline()">{btn_text}</button>
        </div>
        """

    events_html = "".join(events_list_items)
    return events_html, timeline_top_toggle_btn, timeline_toggle_btn

