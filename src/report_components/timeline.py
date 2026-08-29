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
            m_type = ev.get("monster_type", "")
            m_sub = ev.get("monster_sub_type", "")
            obj_desc = clean_monster_name(m_type, m_sub, lang=lang) if m_type else ev.get("desc", "")
            
            # Feminine objectives in PT-BR: Vastilarva
            is_fem = ("HORDE" in m_type.upper() or "GRUB" in m_type.upper())
            slain_key = "slain_by_f" if is_fem else "slain_by"
            slain_txt = get_text(slain_key, lang=lang)

            # Distinguish Void trio (grubs, herald, baron) from Dragon
            is_void = any(w in m_type.upper() for w in ["HORDE", "GRUB", "HERALD", "BARON"])
            obj_theme_class = "event-obj-void" if is_void else "event-obj-dragon"

            events_list_items.append(f"""
            <li class="event-item event-obj {obj_theme_class} {extra_class}">
                <span class="event-time">{t}</span>
                <div class="event-avatar-wrap"><img class="event-avatar" src="{icon_uri}"/></div>
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

            if ev.get("is_first_blood"):
                streak_badge = f'<span class="multi-badge badge-first-blood">FIRST BLOOD! 🩸</span> {streak_badge}'

            elim_txt = get_text("eliminated", lang=lang)
            c_ast = ev.get('assists_count', 0)
            is_exec = ev.get("is_execution", False)

            assists_html = ""
            if c_ast > 0:
                assister_icons = "".join([
                    f'<div class="event-assister-wrap"><img class="event-assister-avatar" src="{a["icon"]}" title="{a["champ"]} ({a["name"]})" alt="{a["champ"]}"/></div>'
                    for a in ev.get("assisters", [])
                ])
                ast_label = get_text("assists_plural", lang=lang) if c_ast > 1 else get_text("assists", lang=lang)
                assists_html = f'<span class="event-assisters-group" title="{c_ast} {ast_label}"><span class="event-assist-label">Assist:</span>{assister_icons}</span>'
            elif not is_exec:
                assists_html = f"<span class='tag-solokill'>{get_text('solo_tag', lang=lang)}</span>"

            if is_exec:
                exec_text = get_text("was_executed", lang=lang)
                events_list_items.append(f"""
                <li class="event-item event-kill event-execution {extra_class}">
                    <span class="event-time">{t}</span>
                    <div class="event-kill-duel">
                        <div class="event-avatar-wrap"><img class="event-avatar" src="{ev['victim_icon']}" title="{ev['victim_champ']}"/></div>
                        <span class="event-arrow">💀</span>
                    </div>
                    <span class="event-desc">
                        <b>{ev['victim_champ']}</b> ({ev['victim_name']}) {exec_text}
                    </span>
                </li>
                """)
            else:
                killer_str = f"<b>{ev['killer_champ']}</b> ({ev['killer_name']})"
                desc_html = f"{killer_str} {elim_txt} <b>{ev['victim_champ']}</b> ({ev['victim_name']}) {assists_html}"

                events_list_items.append(f"""
                <li class="event-item event-kill {streak_class} {extra_class}">
                    <span class="event-time">{t}</span>
                    <div class="event-kill-duel">
                        <div class="event-avatar-wrap"><img class="event-avatar" src="{ev['killer_icon']}" title="{ev['killer_champ']}"/></div>
                        <span class="event-arrow">⚔️</span>
                        <div class="event-avatar-wrap"><img class="event-avatar" src="{ev['victim_icon']}" title="{ev['victim_champ']}"/></div>
                    </div>
                    <span class="event-desc">
                        {desc_html}
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

