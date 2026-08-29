from typing import Dict, Any, Tuple
from ..asset_cache import AssetManager
from ..i18n import get_text
from ..event_engine import clean_monster_name
from ..ddragon import DataDragon

def render_timeline_section(data: Dict[str, Any], lang: str = "pt_BR") -> Tuple[str, str, str]:
    dd = DataDragon(language=lang)
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
            is_soul = ev.get("is_soul", False)
            asset_key = str(ev.get("asset_key", ""))
            name_str = str(m_type + "_" + m_sub).upper()

            glow_class = ""
            if is_soul:
                glow_class = "soul-dragon-badge"
            elif "BARON" in asset_key.upper() or "BARON" in name_str:
                glow_class = "baron-badge"
            elif "ELDER" in asset_key.upper() or "ELDER" in name_str or "ANCIÃO" in name_str:
                glow_class = "elder-badge"

            obj_desc = clean_monster_name(m_type, m_sub, lang=lang) if m_type else ev.get("desc", "")
            if is_soul:
                obj_desc = f"{obj_desc} (SOUL 🐉)"
            
            is_fem = ("HORDE" in m_type.upper() or "GRUB" in m_type.upper())
            slain_key = "slain_by_f" if is_fem else "slain_by"
            slain_txt = get_text(slain_key, lang=lang)

            is_void = any(w in m_type.upper() for w in ["HORDE", "GRUB", "HERALD", "BARON"])
            obj_theme_class = "event-obj-void" if is_void else "event-obj-dragon"

            kills_list_items.append(f"""
            <li class="event-item event-obj {obj_theme_class}" data-phase="{ev_phase}">
                <span class="event-time">{t}</span>
                <img class="event-obj-icon {glow_class}" src="{icon_uri}" alt="{obj_desc}"/>
                <span class="event-desc"><b>{obj_desc}</b> {slain_txt} <b>{ev['killer_champ']}</b> ({ev['killer_name']})</span>
            </li>
            """)
        else:
            streak = ev.get("streak", "normal")
            life_streak = ev.get("life_streak", "none")
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

            # Life kill streaks (Outline + text only, perfectly distinct from solid multikills)
            life_badge = ""
            if life_streak == "legendary":
                life_badge = '<span class="multi-badge" style="background:transparent; color:#fbbf24; border:1px solid #fbbf24; font-weight:800;">LENDÁRIO</span>'
            elif life_streak == "godlike":
                life_badge = '<span class="multi-badge" style="background:transparent; color:#f87171; border:1px solid #ef4444; font-weight:800;">INVENCÍVEL</span>'
            elif life_streak == "dominating":
                life_badge = '<span class="multi-badge" style="background:transparent; color:#c084fc; border:1px solid #a855f7; font-weight:700;">DOMINANDO</span>'
            elif life_streak == "unstoppable":
                life_badge = '<span class="multi-badge" style="background:transparent; color:#60a5fa; border:1px solid #3b82f6; font-weight:700;">IMPLACÁVEL</span>'
            elif life_streak == "rampage":
                life_badge = '<span class="multi-badge" style="background:transparent; color:#38bdf8; border:1px solid #06b6d4; font-weight:700;">ENFURECIDO</span>'
            elif life_streak == "spree":
                life_badge = '<span class="multi-badge" style="background:transparent; color:#94a3b8; border:1px solid #475569; font-weight:600;">KILLING SPREE</span>'

            # Multikills always take precedence on the right
            if life_badge:
                streak_badge = f"{life_badge} {streak_badge}" if streak_badge else life_badge

            if ev.get("is_first_blood"):
                streak_badge = f'<span class="multi-badge badge-first-blood">FIRST BLOOD! 🩸</span> {streak_badge}'

            elim_txt = get_text("eliminated", lang=lang)
            c_ast = ev.get('assists_count', 0)
            is_exec = ev.get("is_execution", False)

            k_team = ev.get("killer_team", 100)
            v_team = ev.get("victim_team", 200)

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
                    return f'<div class="team-champ-mini-wrap" style="margin-right:0;"><img class="team-champ-mini" src="{ev["killer_icon" if is_killer else "victim_icon"]}" alt="{champ_name}"/></div>'
                
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
                p_team = k_team if is_killer else v_team
                title_color = "#60a5fa" if p_team == 100 else "#f87171"

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

                # Estimated Critical Strike Chance calculation from items snapshot
                crit_est = 0
                if items_snapshot:
                    for it in items_snapshot:
                        iid = it.get("id", 0)
                        if 'dd' in locals():
                            crit_est += dd.get_item_crit_chance(iid)
                clean_lower = champ_name.lower()
                if "yasuo" in clean_lower or "yone" in clean_lower:
                    crit_est *= 2
                crit_est = min(crit_est, 100)
                crit_label = "(itens)" if lang == "pt_BR" else "(items)"
                crit_str = f'<span title="Estimativa via itens">{crit_est}% <small style="opacity:0.7; font-size:0.7em;">{crit_label}</small></span>' if crit_est > 0 else "0%"

                return f"""
                <div class="stat-tooltip-trigger" style="position:relative; display:inline-flex; cursor:pointer;">
                    <div class="team-champ-mini-wrap" style="margin-right:0;">
                        <img class="team-champ-mini" src="{avatar_src}" alt="{champ_name}"/>
                    </div>
                    <div class="stat-popup-card">
                        <div class="stat-popup-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:800; color:{title_color};">{champ_name}</span>
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
                            <div class="stat-cell"><i class="stat-ico ico-crit"></i> <span>{crit_str}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-ms"></i> <span>{ms}</span></div>
                        </div>
                        <div class="stat-divider"></div>
                        <div class="stat-grid-2col">
                            <div class="stat-cell"><i class="stat-ico ico-armpen"></i> <span>{arm_pen_flat} | {arm_pen_pct}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-mpen"></i> <span>{mag_pen_flat} | {mag_pen_pct}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-lifesteal"></i> <span>{lifesteal}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-omnivamp"></i> <span>{omnivamp}%</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-range"></i> <span>{champ_range}</span></div>
                            <div class="stat-cell"><i class="stat-ico ico-tenacity"></i> <span>{tenacity}%</span></div>
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

            if is_exec:
                exec_text = get_text("was_executed", lang=lang)
                v_avatar = render_stat_tooltip(ev['victim_champ'], ev.get('victim_stats', {}), ev.get('victim_items', []), is_killer=False)
                kills_list_items.append(f"""
                <li class="event-item event-kill event-execution" data-phase="{ev_phase}">
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
                team_border_class = "event-kill-blue" if k_team == 100 else "event-kill-red"
                killer_str = f"<b>{ev['killer_champ']}</b> ({ev['killer_name']})"
                desc_html = f"{killer_str} {elim_txt} <b>{ev['victim_champ']}</b> ({ev['victim_name']}) {assists_html}"
                k_avatar = render_stat_tooltip(ev['killer_champ'], ev.get('killer_stats', {}), ev.get('killer_items', []), is_killer=True)
                v_avatar = render_stat_tooltip(ev['victim_champ'], ev.get('victim_stats', {}), ev.get('victim_items', []), is_killer=False)

                kills_list_items.append(f"""
                <li class="event-item event-kill {team_border_class} {streak_class}" data-phase="{ev_phase}">
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
        <div class="stat-tooltip-trigger" style="position:relative; display:inline-flex; cursor:pointer;">
            <div class="team-champ-mini-wrap" style="border-color:#38bdf8; margin-right:0;">
                <img class="team-champ-mini" src="{c_icon}" alt="{c_name}"/>
            </div>
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
        <li class="event-item event-item-purchase" data-phase="{ev_phase}">
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

    # 3. GAME END MILESTONE EVENT
    raw_dur = data.get("duration", "00:00")
    # Parse format like "24m 45s" or "24:45"
    end_min = 0
    end_sec = 0
    if "m" in raw_dur:
        try:
            parts = raw_dur.replace("s", "").split("m")
            end_min = int(parts[0].strip())
            end_sec = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else 0
        except Exception:
            end_min = 0
            end_sec = 0
    elif ":" in raw_dur:
        try:
            parts = raw_dur.split(":")
            end_min = int(parts[0])
            end_sec = int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            end_min = 0
            end_sec = 0

    match_dur_formatted = f"{end_min:02d}:{end_sec:02d}"

    if end_min < 14:
        end_phase = "early"
    elif end_min < 25:
        end_phase = "mid"
    else:
        end_phase = "late"

    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    t100_win = team_100.get("win", False)
    t200_win = team_200.get("win", False)
    
    winning_team_name = get_text("blue_team", lang=lang) if t100_win else get_text("red_team", lang=lang)
    win_announcement = get_text("victory_announcement", lang=lang, team=f"<b style='color:{'#60a5fa' if t100_win else '#f87171'};'>{winning_team_name}</b>")
    game_ended_title = get_text("game_ended", lang=lang)

    # Render avatars grouped by team/subteam with vs divider matching search cards
    raw_game_mode = str(data.get("game_mode", "")).upper()
    is_arena = "CHERRY" in raw_game_mode or "ARENA" in raw_game_mode
    
    def render_end_avatar(p, border_c):
        raw_c = p.get("champion_raw", "")
        c_name = p.get("champion", "")
        c_icon = p.get("champion_icon", "")
        stats = p.get("final_stats", {})
        
        # Build snapshot items
        p_items = p.get("items", [])
        p_role = str(p.get("role", "")).upper()
        has_adc_role = (p_role == "BOTTOM")
        
        TRINKET_IDS = {3340, 3363, 3364, 3513, 2055, 3330, 3400}
        BOOT_IDS = {1001, 2422, 3006, 3009, 3020, 3047, 3111, 3117, 3158, 223006, 223009, 223020, 223047, 223111, 223158, 773006, 773009, 773020, 773047, 773111, 773158}
        CONSUMABLE_STACKS = {2003, 2010, 2031, 2033, 2140, 2138, 2139, 2150, 2151, 2152}

        trinket_it = None
        boot_it = None
        norm_its = []
        c_counts = {}
        c_objs = {}
        for it in p_items:
            iid = it.get("id", 0)
            if iid in TRINKET_IDS and not trinket_it:
                trinket_it = it
            elif has_adc_role and iid in BOOT_IDS and not boot_it:
                boot_it = it
            else:
                if iid in CONSUMABLE_STACKS:
                    c_counts[iid] = c_counts.get(iid, 0) + 1
                    c_objs[iid] = it
                else:
                    norm_its.append((it, 1))

        for iid, count in c_counts.items():
            norm_its.append((c_objs[iid], count))

        m_slots = []
        for it, count in norm_its[:6]:
            if it.get("icon"):
                b_tag = f'<span class="slot-stack-badge">{count}</span>' if count > 1 else ""
                m_slots.append(f'<div class="slot-wrap"><img class="stat-item-slot" src="{it["icon"]}" title="{it.get("name", "")}" />{b_tag}</div>')
        while len(m_slots) < 6:
            m_slots.append('<div class="stat-item-slot-empty"></div>')

        b_slot_html = ""
        if has_adc_role:
            if boot_it:
                b_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-boot" src="{boot_it["icon"]}" title="{boot_it.get("name", "")} (Role Quest Boot)"/></div>'
            else:
                b_slot_html = '<div class="stat-item-slot-empty stat-item-slot-boot" title="Role Quest Boot Slot"></div>'
        elif len(norm_its) > 6:
            extra_it, extra_count = norm_its[6]
            b_tag = f'<span class="slot-stack-badge">{extra_count}</span>' if extra_count > 1 else ""
            b_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-boot" src="{extra_it["icon"]}" title="{extra_it.get("name", "")} (Quest/Extra)"/>{b_tag}</div>'

        t_slot_html = f'<div class="slot-wrap"><img class="stat-item-slot stat-item-slot-trinket" src="{trinket_it["icon"]}" title="{trinket_it.get("name", "")} (Trinket)"/></div>' if trinket_it else '<div class="stat-item-slot-empty stat-item-slot-trinket" title="Trinket"></div>'
        
        items_row_html = f"""
        <div class="stat-divider"></div>
        <div class="stat-items-row">
            {''.join(m_slots)}
            {b_slot_html}
            {t_slot_html}
        </div>
        """

        if not stats:
            return f"""
            <div class="stat-tooltip-trigger" style="position:relative; display:inline-flex; cursor:pointer;">
                <div class="team-champ-mini-wrap" style="border-color:{border_c}; margin-right:0;">
                    <img class="team-champ-mini" src="{c_icon}" alt="{c_name}"/>
                </div>
                <div class="stat-popup-card">
                    <div class="stat-popup-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
                        <span style="font-weight:800; color:{border_c}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{c_name} ({p.get('riot_id', '')})">{c_name}</span>
                        <span style="font-size:0.68rem; color:var(--text-muted); font-weight:600; white-space:nowrap; flex-shrink:0;">@ {match_dur_formatted} (End)</span>
                    </div>
                    {items_row_html}
                </div>
            </div>
            """

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
        champ_range = stats.get("attackRange", 125)

        # Estimated Critical Strike Chance calculation from items snapshot
        crit_est = 0
        for it in (p_items or []):
            iid = it.get("id", 0)
            if 'dd' in locals():
                crit_est += dd.get_item_crit_chance(iid)
        clean_lower = c_name.lower()
        if "yasuo" in clean_lower or "yone" in clean_lower:
            crit_est *= 2
        crit_est = min(crit_est, 100)
        crit_label = "(itens)" if lang == "pt_BR" else "(items)"
        crit_str = f'<span title="Estimativa via itens">{crit_est}% <small style="opacity:0.7; font-size:0.7em;">{crit_label}</small></span>' if crit_est > 0 else "0%"

        return f"""
        <div class="stat-tooltip-trigger" style="position:relative; display:inline-flex; cursor:pointer;">
            <div class="team-champ-mini-wrap" style="border-color:{border_c}; margin-right:0;">
                <img class="team-champ-mini" src="{c_icon}" alt="{c_name}"/>
            </div>
            <div class="stat-popup-card">
                <div class="stat-popup-header" style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center; gap:8px;">
                    <span style="font-weight:800; color:{border_c}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{c_name} ({p.get('riot_id', '')})">{c_name}</span>
                    <span style="font-size:0.68rem; color:var(--text-muted); font-weight:600; white-space:nowrap; flex-shrink:0;">@ {match_dur_formatted} (End)</span>
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
                    <div class="stat-cell"><i class="stat-ico ico-crit"></i> <span>{crit_str}</span></div>
                    <div class="stat-cell"><i class="stat-ico ico-ms"></i> <span>{ms}</span></div>
                </div>
                <div class="stat-divider"></div>
                <div class="stat-grid-2col">
                    <div class="stat-cell"><i class="stat-ico ico-armpen"></i> <span>{arm_pen_flat} | {arm_pen_pct}%</span></div>
                    <div class="stat-cell"><i class="stat-ico ico-mpen"></i> <span>{mag_pen_flat} | {mag_pen_pct}%</span></div>
                    <div class="stat-cell"><i class="stat-ico ico-lifesteal"></i> <span>{lifesteal}%</span></div>
                    <div class="stat-cell"><i class="stat-ico ico-omnivamp"></i> <span>{omnivamp}%</span></div>
                    <div class="stat-cell"><i class="stat-ico ico-range"></i> <span>{champ_range}</span></div>
                    <div class="stat-cell"><i class="stat-ico ico-tenacity"></i> <span>{tenacity}%</span></div>
                </div>
                {items_row_html}
            </div>
        </div>
        """

    if is_arena:
        all_arena_players = team_100.get("players", []) + team_200.get("players", [])
        subteams = {}
        for p in all_arena_players:
            place = p.get("placement") or p.get("subteam_id", 0)
            subteams.setdefault(place, []).append(p)
        sorted_subteams = sorted(subteams.items(), key=lambda x: x[0] if isinstance(x[0], int) and x[0] > 0 else 99)
        
        team_groups_html = []
        for pl, p_list in sorted_subteams:
            b_col = "#22c55e" if pl == 1 else ("#38bdf8" if pl <= 2 else "#94a3b8")
            avatars = "".join([render_end_avatar(p, b_col) for p in p_list])
            team_groups_html.append(f'<div class="game-end-team-group" style="display:flex; align-items:center; gap:3px; background:#090d16; padding:2px 6px; border-radius:12px; border:1px solid rgba(255,255,255,0.1);">{avatars}</div>')
        strip_content = ' <span class="m-vs-text" style="color:#64748b; font-weight:800; font-size:0.75rem;">vs</span> '.join(team_groups_html)
    else:
        t1_avatars = "".join([render_end_avatar(p, "#60a5fa") for p in team_100.get("players", [])])
        t2_avatars = "".join([render_end_avatar(p, "#f87171") for p in team_200.get("players", [])])
        strip_content = f"""
        <div class="m-team-group m-team-blue">{t1_avatars}</div>
        <span class="m-vs-text" style="color:#64748b; font-weight:800; font-size:0.75rem;">vs</span>
        <div class="m-team-group m-team-red">{t2_avatars}</div>
        """

    game_end_li_kills = f"""
    <li class="event-item event-game-end" data-phase="{end_phase}">
        <div class="event-game-end-glint"></div>
        <span class="event-time">{match_dur_formatted}</span>
        <span class="event-desc" style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; width:100%;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1.15rem;">🏆</span>
                <span><b>{game_ended_title}</b> • {win_announcement}</span>
            </div>
            <div class="game-end-avatars-strip">
                {strip_content}
            </div>
        </span>
    </li>
    """

    kills_list_items.append(game_end_li_kills)
    items_list_items.append(game_end_li_kills)

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
        <button id="timelineTogglePhaseBtn" class="phase-nav-btn" style="background:#1e293b; border-color:#475569;" onclick="togglePhaseExpansion()">{get_text('expand_timeline', lang=lang)}</button>
        <button id="timelineNextPhaseBtn" class="phase-nav-btn" onclick="navigateTimelinePhase(1, this)">{get_text('nav_next_mid', lang=lang)}</button>
    </div>
    """

    expand_top_txt = get_text("expand_timeline", lang=lang)
    timeline_top_toggle_btn = f"""
    <button id="toggleTimelineTopBtn" class="btn" style="background:#1e293b; border:1px solid var(--card-border); color:#38bdf8; font-weight:700; font-size:0.78rem; padding:4px 12px; border-radius:6px; cursor:pointer;" onclick="togglePhaseExpansion()">{expand_top_txt}</button>
    """
    timeline_toggle_btn = ""

    return combined_html, timeline_top_toggle_btn, timeline_toggle_btn

