from typing import Dict, Any, Tuple
from ..asset_cache import AssetManager
from ..i18n import get_text
from ..event_engine import clean_monster_name

def render_timeline_section(data: Dict[str, Any], lang: str = "pt_BR") -> Tuple[str, str, str]:
    # 1. ABA 1: KILLS & OBJECTIVES
    kills_list_items = []
    for idx, ev in enumerate(data.get("key_events", [])):
        t = ev.get("time", "00:00")
        ev_type = ev.get("type", "kill")
        
        # Phase calculation (0-14m = early, 14-25m = mid, 25m+ = late)
        try:
            p_parts = t.split(":")
            ev_min = int(p_parts[0])
        except Exception:
            ev_min = 0

        if ev_min < 14:
            ev_phase = "early"
        elif ev_min < 25:
            ev_phase = "mid"
        else:
            ev_phase = "late"
        
        if ev_type == "objective":
            icon_uri = AssetManager.get_asset_uri(ev.get("asset_key", ""))
            m_type = ev.get("monster_type", "")
            m_sub = ev.get("monster_sub_type", "")
            obj_desc = clean_monster_name(m_type, m_sub, lang=lang) if m_type else ev.get("desc", "")
            
            is_fem = ("HORDE" in m_type.upper() or "GRUB" in m_type.upper())
            slain_key = "slain_by_f" if is_fem else "slain_by"
            slain_txt = get_text(slain_key, lang=lang)

            is_void = any(w in m_type.upper() for w in ["HORDE", "GRUB", "HERALD", "BARON"])
            obj_theme_class = "event-obj-void" if is_void else "event-obj-dragon"

            kills_list_items.append(f"""
            <li class="event-item event-obj {obj_theme_class}" data-phase="{ev_phase}">
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

            def render_stat_tooltip(champ_name, stats, items_snapshot=None, is_killer=True):
                if not stats:
                    return f'<div class="event-avatar-wrap"><img class="event-avatar" src="{ev["killer_icon" if is_killer else "victim_icon"]}" alt="{champ_name}"/></div>'
                
                hp_max = stats.get("healthMax", stats.get("health", 0))
                hp_regen = stats.get("healthRegen", 0)
                ad = stats.get("attackDamage", 0)
                ap = stats.get("abilityPower", 0)
                armor = stats.get("armor", 0)
                mr = stats.get("magicResist", 0)
                as_val = stats.get("attackSpeed", 100) / 100.0 if stats.get("attackSpeed", 0) > 10 else stats.get("attackSpeed", 0)
                ah = stats.get("abilityHaste", 0)
                ms = stats.get("movementSpeed", 0)
                lifesteal = stats.get("lifesteal", 0)
                omnivamp = stats.get("omnivamp", 0) or stats.get("physicalVamp", 0)
                
                arm_pen_flat = stats.get("armorPen", 0)
                arm_pen_pct = stats.get("armorPenPercent", 0) or stats.get("bonusArmorPenPercent", 0)
                mag_pen_flat = stats.get("magicPen", 0)
                mag_pen_pct = stats.get("magicPenPercent", 0) or stats.get("bonusMagicPenPercent", 0)
                tenacity = stats.get("ccReduction", 0)
                champ_range = dd.get_champion_attack_range(champ_name) if 'dd' in locals() else 125

                avatar_src = ev["killer_icon"] if is_killer else ev["victim_icon"]
                role_label = get_text("killer", lang=lang) if is_killer else get_text("victim", lang=lang)
                border_color = "#38bdf8" if is_killer else "#ef4444"

                # Items row inside tooltip: 6 main slots | Role Quest Slot (ADC / Special) | Trinket
                items_row_html = ""
                if items_snapshot:
                    TRINKET_IDS = {3340, 3363, 3364, 3513, 2055, 3330, 3400}
                    BOOT_IDS = {1001, 2422, 3006, 3009, 3020, 3047, 3111, 3117, 3158, 223006, 223009, 223020, 223047, 223111, 223158, 773006, 773009, 773020, 773047, 773111, 773158}
                    CONSUMABLE_STACKS = {2003, 2010, 2031, 2033, 2140, 2138, 2139, 2150, 2151, 2152}
                    
                    trinket_item = None
                    boot_item = None
                    raw_normal_items = []
                    item_counts = {}
                    item_objs = {}
                    
                    # Detect role from ev dictionary
                    p_role = str(ev.get("killer_role" if is_killer else "victim_role", "")).upper()
                    has_adc_role_slot = (p_role == "BOTTOM")
                    
                    for it in items_snapshot:
                        iid = it.get("id", 0)
                        if iid in TRINKET_IDS and not trinket_item:
                            trinket_item = it
                        elif has_adc_role_slot and iid in BOOT_IDS and not boot_item:
                            boot_item = it
                        else:
                            if iid in CONSUMABLE_STACKS:
                                item_counts[iid] = item_counts.get(iid, 0) + 1
                                item_objs[iid] = it
                            else:
                                raw_normal_items.append((it, 1))

                    for iid, count in item_counts.items():
                        raw_normal_items.append((item_objs[iid], count))
                    
                    main_slots = []
                    for it, count in raw_normal_items[:6]:
                        if it.get("icon"):
                            count_badge = f'<span class="slot-stack-badge">{count}</span>' if count > 1 else ""
                            main_slots.append(f'<div class="slot-wrap"><img class="stat-item-slot" src="{it["icon"]}" title="{it.get("name", "")}" />{count_badge}</div>')
                    while len(main_slots) < 6:
                        main_slots.append('<div class="stat-item-slot-empty"></div>')
                    
                    # 7th Slot: Only rendered if ADC role has dedicated boot slot or extra quest item
                    boot_slot_html = ""
                    if has_adc_role_slot:
                        if boot_item:
                            boot_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-boot" src="{boot_item["icon"]}" title="{boot_item.get("name", "")} (Role Quest Boot)"/></div>'
                        else:
                            boot_slot_html = '<div class="stat-item-slot-empty stat-item-slot-boot" title="Role Quest Boot Slot"></div>'
                    elif len(raw_normal_items) > 6:
                        extra_it, extra_count = raw_normal_items[6]
                        count_badge = f'<span class="slot-stack-badge">{extra_count}</span>' if extra_count > 1 else ""
                        boot_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-boot" src="{extra_it["icon"]}" title="{extra_it.get("name", "")} (Quest/Extra)"/>{count_badge}</div>'

                    # Trinket Slot
                    trinket_slot_html = ""
                    if trinket_item:
                        trinket_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-trinket" src="{trinket_item["icon"]}" title="{trinket_item.get("name", "")} (Trinket)"/></div>'
                    else:
                        trinket_slot_html = '<div class="stat-item-slot-empty stat-item-slot-trinket" title="Trinket"></div>'
                    
                    items_row_html = f"""
                    <div class="stat-divider"></div>
                    <div class="stat-items-row">
                        {''.join(main_slots)}
                        {boot_slot_html}
                        {trinket_slot_html}
                    </div>
                    """

                try:
                    parts = t.split(":")
                    kill_min = int(parts[0])
                except Exception:
                    kill_min = 0

                return f"""
                <div class="event-avatar-wrap stat-tooltip-trigger">
                    <img class="event-avatar" src="{avatar_src}" alt="{champ_name}"/>
                    <div class="stat-popup-card">
                        <div class="stat-popup-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:800; color:{border_color};">{champ_name}</span>
                            <span style="font-size:0.68rem; color:var(--text-muted); font-weight:600;" title="Lance aos {t} • Snapshot do frame aos {kill_min}m">@ {kill_min}:00 <span style="opacity:0.6;">({t})</span></span>
                        </div>
                        <div class="stat-grid-2col">
                            <div class="stat-cell"><i class="stat-ico ico-hp"></i> <span>{hp_max}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-hpregen"></i> <span>{hp_regen}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-ad"></i> <span>{ad}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-ap"></i> <span>{ap}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-armor"></i> <span>{armor}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-mr"></i> <span>{mr}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-as"></i> <span>{as_val:.2f}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-ah"></i> <span>{ah}</span></div>
                        </div>
                        <div class="stat-divider"></div>
                        <div class="stat-grid-2col">
                            <div class="stat-cell"><i class="stat-ico ico-armpen"></i> <span>{arm_pen_flat} | {arm_pen_pct}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-mpen"></i> <span>{mag_pen_flat} | {mag_pen_pct}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-lifesteal"></i> <span>{lifesteal}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-omnivamp"></i> <span>{omnivamp}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-ms"></i> <span>{ms}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-range"></i> <span>{champ_range}</span></div>
                            <div class="stat-cell" style="grid-column: span 2;"><i class="stat-ico ico-tenacity"></i> <span>{tenacity}%</span></div>
                        </div>
                        {items_row_html}
                    </div>
                </div>
                """

            # Phase calculation (0-14m = early, 14-25m = mid, 25m+ = late)
            try:
                p_parts = t.split(":")
                ev_min = int(p_parts[0])
            except Exception:
                ev_min = 0

            if ev_min < 14:
                ev_phase = "early"
            elif ev_min < 25:
                ev_phase = "mid"
            else:
                ev_phase = "late"

            extra_class = "timeline-hidden" if idx >= 10 else ""

            if is_exec:
                exec_text = get_text("was_executed", lang=lang)
                v_avatar = render_stat_tooltip(ev['victim_champ'], ev.get('victim_stats', {}), ev.get('victim_items', []), is_killer=False)
                kills_list_items.append(f"""
                <li class="event-item event-kill event-execution {extra_class}" data-phase="{ev_phase}">
                    <span class="event-time">{t}</span>
                    <div class="event-kill-duel">
                        {v_avatar}
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
                k_avatar = render_stat_tooltip(ev['killer_champ'], ev.get('killer_stats', {}), ev.get('killer_items', []), is_killer=True)
                v_avatar = render_stat_tooltip(ev['victim_champ'], ev.get('victim_stats', {}), ev.get('victim_items', []), is_killer=False)

                kills_list_items.append(f"""
                <li class="event-item event-kill {streak_class} {extra_class}" data-phase="{ev_phase}">
                    <span class="event-time">{t}</span>
                    <div class="event-kill-duel">
                        {k_avatar}
                        <span class="event-arrow">⚔️</span>
                        {v_avatar}
                    </div>
                    <span class="event-desc">
                        {desc_html}
                    </span>
                    {streak_badge}
                </li>
                """)

    # 2. ABA 2: ITEM PURCHASES
    items_list_items = []
    purchased_lbl = get_text("purchased_item", lang=lang)
    for idx, ev in enumerate(data.get("item_events", [])):
        t = ev.get("time", "00:00")
        try:
            p_parts = t.split(":")
            ev_min = int(p_parts[0])
        except Exception:
            ev_min = 0

        if ev_min < 14:
            ev_phase = "early"
        elif ev_min < 25:
            ev_phase = "mid"
        else:
            ev_phase = "late"

        extra_class = "timeline-hidden" if idx >= 10 else ""
        c_name = ev.get("champ", "")
        c_icon = ev.get("champ_icon", "")
        s_name = ev.get("summoner_name", "")
        i_name = ev.get("item_name", "")
        i_icon = ev.get("item_icon", "")
        snapshot = ev.get("items_snapshot", [])

        # Build snapshot slots on hover
        TRINKET_IDS = {3340, 3363, 3364, 3513, 2055, 3330, 3400}
        BOOT_IDS = {1001, 2422, 3006, 3009, 3020, 3047, 3111, 3117, 3158, 223006, 223009, 223020, 223047, 223111, 223158, 773006, 773009, 773020, 773047, 773111, 773158}
        CONSUMABLE_STACKS = {2003, 2010, 2031, 2033, 2140, 2138, 2139, 2150, 2151, 2152}
        
        trinket_item = None
        boot_item = None
        raw_normal_items = []
        item_counts = {}
        item_objs = {}
        
        p_role = str(ev.get("role", "")).upper()
        has_adc_role_slot = (p_role == "BOTTOM")

        for it in snapshot:
            iid = it.get("id", 0)
            if iid in TRINKET_IDS and not trinket_item:
                trinket_item = it
            elif has_adc_role_slot and iid in BOOT_IDS and not boot_item:
                boot_item = it
            else:
                if iid in CONSUMABLE_STACKS:
                    item_counts[iid] = item_counts.get(iid, 0) + 1
                    item_objs[iid] = it
                else:
                    raw_normal_items.append((it, 1))

        for iid, count in item_counts.items():
            raw_normal_items.append((item_objs[iid], count))

        main_slots = []
        for it, count in raw_normal_items[:6]:
            if it.get("icon"):
                count_badge = f'<span class="slot-stack-badge">{count}</span>' if count > 1 else ""
                main_slots.append(f'<div class="slot-wrap"><img class="stat-item-slot" src="{it["icon"]}" title="{it.get("name", "")}" />{count_badge}</div>')
        while len(main_slots) < 6:
            main_slots.append('<div class="stat-item-slot-empty"></div>')

        # 7th Slot: Only rendered if ADC role has dedicated boot slot or extra quest item
        boot_slot_html = ""
        if has_adc_role_slot:
            if boot_item:
                boot_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-boot" src="{boot_item["icon"]}" title="{boot_item.get("name", "")} (Role Quest Boot)"/></div>'
            else:
                boot_slot_html = '<div class="stat-item-slot-empty stat-item-slot-boot" title="Role Quest Boot Slot"></div>'
        elif len(raw_normal_items) > 6:
            extra_it, extra_count = raw_normal_items[6]
            count_badge = f'<span class="slot-stack-badge">{extra_count}</span>' if extra_count > 1 else ""
            boot_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-boot" src="{extra_it["icon"]}" title="{extra_it.get("name", "")} (Quest/Extra)"/>{count_badge}</div>'

        # Trinket Slot
        trinket_slot_html = ""
        if trinket_item:
            trinket_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-trinket" src="{trinket_item["icon"]}" title="{trinket_item.get("name", "")} (Trinket)"/></div>'
        else:
            trinket_slot_html = '<div class="stat-item-slot-empty stat-item-slot-trinket" title="Trinket"></div>'

        items_row = f'<div class="stat-items-row" style="margin-top:4px;">{"".join(main_slots)}{boot_slot_html}{trinket_slot_html}</div>'

        avatar_html = f"""
        <div class="event-avatar-wrap stat-tooltip-trigger">
            <img class="event-avatar" src="{c_icon}" alt="{c_name}"/>
            <div class="stat-popup-card">
                <div class="stat-popup-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:800; color:#38bdf8;">{c_name}</span>
                    <span style="font-size:0.68rem; color:var(--text-muted); font-weight:600;">@ {t}</span>
                </div>
                <div style="font-size:0.72rem; color:var(--text-muted); font-weight:700; margin-bottom:4px;">Build @ {t}:</div>
                {items_row}
            </div>
        </div>
        """

        items_list_items.append(f"""
        <li class="event-item event-item-purchase {extra_class}" data-phase="{ev_phase}">
            <span class="event-time">{t}</span>
            <div class="event-kill-duel">
                {avatar_html}
            </div>
            <span class="event-desc" style="display:flex; align-items:center; gap:8px;">
                <span><b>{c_name}</b> ({s_name}) {purchased_lbl}</span>
                <img class="item-icon" src="{i_icon}" alt="{i_name}" title="{i_name}"/>
                <b>{i_name}</b>
            </span>
        </li>
        """)

    tab_kills_txt = get_text("tab_kills_objectives", lang=lang)
    tab_items_txt = get_text("tab_item_purchases", lang=lang)
    f_early_txt = get_text("filter_early", lang=lang)
    f_mid_txt = get_text("filter_mid", lang=lang)
    f_late_txt = get_text("filter_late", lang=lang)

    combined_html = f"""
    <div class="timeline-controls-bar">
        <div class="timeline-tabs-header">
            <button class="timeline-tab-btn active" onclick="switchTimelineTab('kills', this)">
                <span>{tab_kills_txt}</span>
                <span class="timeline-tab-count">{len(kills_list_items)}</span>
            </button>
            <button class="timeline-tab-btn" onclick="switchTimelineTab('items', this)">
                <span>{tab_items_txt}</span>
                <span class="timeline-tab-count">{len(items_list_items)}</span>
            </button>
        </div>
        <div class="timeline-phase-filters">
            <button class="phase-filter-btn active" onclick="filterTimelinePhase('early', this)">{f_early_txt}</button>
            <button class="phase-filter-btn" onclick="filterTimelinePhase('mid', this)">{f_mid_txt}</button>
            <button class="phase-filter-btn" onclick="filterTimelinePhase('late', this)">{f_late_txt}</button>
        </div>
    </div>
    <div id="timelinePaneKills" class="timeline-pane active">
        <ul class="events-list">
            {''.join(kills_list_items)}
        </ul>
    </div>
    <div id="timelinePaneItems" class="timeline-pane">
        <ul class="events-list">
            {''.join(items_list_items)}
        </ul>
    </div>
    <div class="timeline-phase-nav-footer" style="display:flex; justify-content:center; gap:10px; margin-top:14px;">
        <button id="timelinePrevPhaseBtn" class="phase-nav-btn" style="display:none;" onclick="navigateTimelinePhase(-1, this)">{get_text('nav_prev_early', lang=lang)}</button>
        <button id="timelineNextPhaseBtn" class="phase-nav-btn" onclick="navigateTimelinePhase(1, this)">{get_text('nav_next_mid', lang=lang)}</button>
    </div>
    """

    timeline_top_toggle_btn = ""
    timeline_toggle_btn = ""

    return combined_html, timeline_top_toggle_btn, timeline_toggle_btn

