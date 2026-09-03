from typing import Dict, Any, List
from ..asset_cache import AssetManager
from ..i18n import get_text
from .utils import calculate_gold_bar_share
from .jungle_strip import render_jungle_chronological

def render_duel_row(p1, p2, role_title, stats_1=None, stats_2=None, gold_d=None, xp_d=None, 
                    is_bot_duo=False, extra_badges_1="", extra_badges_2="", target_puuid="", lang="pt_BR",
                    is_aram=False, is_arena=False) -> str:
    is_t1 = p1.get("puuid") == target_puuid
    is_t2 = p2.get("puuid") == target_puuid

    is_team_comb = p1.get("is_team_combined", False) or p2.get("is_team_combined", False)

    dmg_delta = p1.get("damage_to_champions", 0) - p2.get("damage_to_champions", 0)
    gold_delta_final = p1.get("gold_total", 0) - p2.get("gold_total", 0)

    bar_threshold = 15000.0 if is_team_comb else (8000.0 if is_bot_duo else 5000.0)
    p1_share = calculate_gold_bar_share(gold_delta_final, max_delta=bar_threshold)
    p2_share = 100.0 - p1_share

    gap_limit = 3500 if is_bot_duo else 2000
    gap_badge_left = "" if is_team_comb else ('<span class="gap-seal gap-left">GAP! 🔥</span>' if gold_delta_final >= gap_limit else "")
    gap_badge_right = "" if is_team_comb else ('<span class="gap-seal gap-right">GAP! 🔥</span>' if gold_delta_final <= -gap_limit else "")

    icon_pink = "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/2055.png"

    def p_card(p, is_target, is_left=True, badges_html="", is_dmg_leader=False, is_gold_leader=False, delta_dmg=0, delta_gold=0):
        align_class = "align-left" if is_left else "align-right"
        border_side = "border-blue" if is_left else "border-red"
        target_badge = f'<span class="target-tag">{get_text("you_tag", lang=lang)}</span>' if is_target else ""
        
        dmg_delta_tag = f'<span class="lead-delta">+{delta_dmg:,}</span>' if is_dmg_leader and delta_dmg > 0 else ""
        gold_delta_tag = f'<span class="lead-delta">+{delta_gold:,}</span>' if is_gold_leader and delta_gold > 0 else ""

        kda_ratio_tag = f'<span class="kda-ratio">({p.get("kda_ratio", "")})</span>' if p.get("kda_ratio") else ""

        cs_val = p.get("cs", 0)
        cs_pm = p.get("cs_per_min", 0)
        cs_display = f"<b>{cs_val}</b> <span style='color:var(--text-muted); font-size:0.78rem;'>({cs_pm}/m)</span>"
        spells_runes_strip = ""
        items_html = ""
        augments_strip = ""

        if p.get("is_team_combined"):
            icons_render = p.get("team_icons_html", "")
            if is_left:
                header_html = f"""
                <div class="p-header">
                    <div class="team-avatar-stack">
                        {icons_render}
                    </div>
                    <div class="p-meta">
                        <div class="p-name">{p.get('summoner_name', '')} {target_badge}</div>
                        <div class="p-champ">KDA: <b>{p.get('kda', '')}</b> {kda_ratio_tag}</div>
                    </div>
                </div>
                """
            else:
                header_html = f"""
                <div class="p-header" style="justify-content: flex-end;">
                    <div class="p-meta" style="text-align: right;">
                        <div class="p-name">{p.get('summoner_name', '')} {target_badge}</div>
                        <div class="p-champ">KDA: <b>{p.get('kda', '')}</b> {kda_ratio_tag}</div>
                    </div>
                    <div class="team-avatar-stack">
                        {icons_render}
                    </div>
                </div>
                """
        elif is_bot_duo:
            lvl1 = p.get("lvl1", "")
            lvl2 = p.get("lvl2", "")
            lvl_display = f" • <span class='champ-level-badge'>Lv {lvl1} &amp; {lvl2}</span>" if lvl1 and lvl2 else ""
            if is_left:
                header_html = f"""
                <div class="p-header">
                    <div class="duo-avatar-stack">
                        <div class="avatar-glint-wrapper" style="width:34px; height:34px;" title="{p['champ1']}">
                            <img class="champ-icon duo-icon-1" src="{p['icon1']}" alt="{p['champ1']}"/>
                        </div>
                        <div class="avatar-glint-wrapper" style="width:34px; height:34px;" title="{p['champ2']}">
                            <img class="champ-icon duo-icon-2" src="{p['icon2']}" alt="{p['champ2']}"/>
                        </div>
                    </div>
                    <div class="p-meta">
                        <div class="p-name">{p['champ1']} &amp; {p['champ2']} {target_badge}</div>
                        <div class="p-champ">KDA: <b>{p['kda']}</b> {kda_ratio_tag}{lvl_display}</div>
                    </div>
                </div>
                """
            else:
                header_html = f"""
                <div class="p-header" style="justify-content: flex-end;">
                    <div class="p-meta" style="text-align: right;">
                        <div class="p-name">{p['champ1']} &amp; {p['champ2']} {target_badge}</div>
                        <div class="p-champ">KDA: <b>{p['kda']}</b> {kda_ratio_tag}{lvl_display}</div>
                    </div>
                    <div class="duo-avatar-stack">
                        <div class="avatar-glint-wrapper" style="width:34px; height:34px;" title="{p['champ1']}">
                            <img class="champ-icon duo-icon-1" src="{p['icon1']}" alt="{p['champ1']}"/>
                        </div>
                        <div class="avatar-glint-wrapper" style="width:34px; height:34px;" title="{p['champ2']}">
                            <img class="champ-icon duo-icon-2" src="{p['icon2']}" alt="{p['champ2']}"/>
                        </div>
                    </div>
                </div>
                """
        else:
            lvl_val = p.get("champ_level", 1)
            lvl_display = f" • <span class='champ-level-badge'>Lv {lvl_val}</span>" if lvl_val else ""
            
            penta_tag = '<span class="badge-multikill-card badge-penta-glow">👑 PENTAKILL</span>' if p.get("penta_kills", 0) > 0 else ""
            quadra_tag = '<span class="badge-multikill-card badge-quadra-glow">🔥 QUADRAKILL</span>' if (p.get("quadra_kills", 0) > 0 and not penta_tag) else ""
            
            # Header Tooltip (Champion / KDA / CC / Multi-Kill / Crit)
            cc_val = p.get("time_ccing_others", 0)
            largest_multi = p.get("largest_multikill", 1)
            multi_names = {2: "Double Kill", 3: "Triple Kill", 4: "Quadra Kill", 5: "Penta Kill"}
            crit_val = p.get("largest_critical_strike", 0)
            spree_val = p.get("largest_killing_spree", 0)

            ratio_str = f" ({p.get('kda_ratio', '')})" if p.get("kda_ratio") else ""
            header_tooltip_lines = [
                f"<b>{p.get('champion', '')} ({p.get('riot_id', '')})</b>",
                f"• KDA: <b>{p.get('kda', '')}</b>{ratio_str}",
                f"• {get_text('cc_score', lang=lang)}: <b>{cc_val}s</b>"
            ]
            if largest_multi > 1:
                header_tooltip_lines.append(f"• {get_text('largest_multikill', lang=lang)}: <b style='color:#f59e0b;'>{multi_names.get(largest_multi, str(largest_multi))}</b>")
            if spree_val > 2:
                header_tooltip_lines.append(f"• Killing Spree: <b>{spree_val}</b>")
            if crit_val > 0:
                header_tooltip_lines.append(f"• {get_text('largest_crit', lang=lang)}: <b>{crit_val:,}</b>")
            header_tooltip_html = "<br/>".join(header_tooltip_lines)
            header_tooltip_safe = header_tooltip_html.replace('"', '&quot;')

            # Parse riot_id for search prompt
            r_name = p.get("game_name") or (p.get("riot_id", "").split("#")[0] if "#" in p.get("riot_id", "") else p.get("riot_id", ""))
            r_tag = p.get("tag_line") or (p.get("riot_id", "").split("#")[1] if "#" in p.get("riot_id", "") else "")
            
            if r_name and r_tag:
                name_clickable_html = f'<span class="summoner-link" onclick="event.stopPropagation(); promptSearchSummoner(\'{r_name}\', \'{r_tag}\')" title="{r_name}#{r_tag}">{p["riot_id"]}</span>'
            else:
                name_clickable_html = f'<span>{p["riot_id"]}</span>'

            header_html = f"""
            <div class="p-header" data-tooltip="{header_tooltip_safe}">
                <div class="avatar-glint-wrapper {'penta-avatar-glow' if penta_tag else ('quadra-avatar-glow' if quadra_tag else '')}">
                    <img class="champ-icon" src="{p['champion_icon']}" alt="{p['champion']}"/>
                    <span class="avatar-glint-sweep"></span>
                </div>
                <div class="p-meta">
                    <div class="p-name">{name_clickable_html} {target_badge} {penta_tag} {quadra_tag}</div>
                    <div class="p-champ">{p['champion']} • KDA: <b>{p['kda']}</b> {kda_ratio_tag}{lvl_display}</div>
                </div>
            </div>
            """


            spells_html = "".join([
                f'<img class="spell-icon" src="{s["icon"]}" data-tooltip="{s.get("tooltip") or s.get("name", "")}" alt="{s.get("name", "")}"/>'
                for s in p.get("spells", []) if s.get("icon")
            ])
            rune_info = p.get("rune", {})
            sub_rune_info = p.get("sub_rune", {})
            full_tree_tt = p.get("full_rune_tree_tooltip") or rune_info.get("tooltip") or rune_info.get("name", "")
            rune_html = f'<img class="rune-icon" src="{rune_info["icon"]}" data-tooltip="{full_tree_tt}" alt="{rune_info.get("name", "")}"/>' if rune_info.get("icon") else ""
            sub_rune_html = f'<img class="sub-rune-icon" src="{sub_rune_info["icon"]}" data-tooltip="{full_tree_tt}" alt="{sub_rune_info.get("name", "")}"/>' if sub_rune_info.get("icon") else ""

            spells_runes_strip = f"""
            <div class="spells-runes-strip">
                <div class="runes-col" data-tooltip="{full_tree_tt}">
                    {rune_html}
                    {sub_rune_html}
                </div>
                <div class="spells-row">{spells_html}</div>
            </div>
            """ if (spells_html or rune_html or sub_rune_html) else ""

            # Arena Augments Strip
            augments_list = p.get("augments", [])
            aug_items_html = []
            for aug in augments_list:
                a_icon = aug.get("icon")
                a_name = aug.get("name", "")
                a_tooltip = aug.get("tooltip", a_name)
                a_border = aug.get("rarity_border", "#94a3b8")
                a_color = aug.get("rarity_color", "#cbd5e1")
                aug_items_html.append(f"""
                <div class="slot-wrap" style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:radial-gradient(circle, {a_color}25 0%, rgba(15,23,42,0.9) 80%); border:1.5px solid {a_border}; box-shadow:0 0 6px {a_color}55;">
                    <img class="augment-icon" src="{a_icon}" data-tooltip="{a_tooltip}" alt="{a_name}" style="width:20px; height:20px; object-fit:contain; filter:drop-shadow(0 0 2px {a_color}); display:block;"/>
                </div>
                """)
            lbl_augs = get_text("lbl_augments", lang=lang)

            # Purchased Stat Anvils Badge
            purchased_anvils_cnt = p.get("purchased_anvils", 0)
            anvil_badge_html = ""
            if is_arena or purchased_anvils_cnt > 0:
                anvil_tt = get_text("purchased_stat_anvils", lang=lang)
                anvil_icon_url = "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/220000.png"
                anvil_badge_html = f"""
                <div class="anvil-purchased-badge" data-tooltip="{anvil_tt}" style="display:inline-flex; align-items:center; gap:4px; padding:2px 7px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:12px; font-size:0.72rem; font-weight:700; color:#f8fafc; cursor:help;">
                    <img src="{anvil_icon_url}" style="width:16px; height:16px; border-radius:50%; display:block;" alt="Anvil"/>
                    <span style="color:#f8fafc;">{purchased_anvils_cnt}</span>
                    <i class="stat-ico ico-gold" style="width:11px; height:11px; display:inline-block;"></i>
                </div>
                """

            augments_strip = f"""
            <div class="arena-augments-strip" style="display:flex; align-items:center; gap:6px; margin-top:6px; padding:3px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.06); border-radius:6px; flex-wrap:wrap;">
                <span style="font-size:0.65rem; font-weight:800; color:var(--text-muted); text-transform:uppercase; margin-right:2px;">{lbl_augs}:</span>
                {''.join(aug_items_html)}
                {anvil_badge_html}
            </div>
            """ if (aug_items_html or anvil_badge_html) else ""

            items_html = "".join([
                f'<img class="item-icon{" item-role-bound" if it.get("is_role_bound") else ""}" src="{it["icon"]}" data-tooltip="{it.get("tooltip") or it.get("name", "")}" alt="{it.get("name", "")}"/>'
                for it in p.get("items", [])
            ])

        obj_strip_html = f'<div class="jungle-mini-strip">{badges_html}</div>' if badges_html else ""

        dmg_tot = p.get("damage_to_champions", 0)
        dmg_phys = p.get("damage_physical", 0)
        dmg_mag = p.get("damage_magic", 0)
        dmg_tru = p.get("damage_true", 0)

        dmg_tk = p.get("damage_taken", 0)
        dmg_mit = p.get("damage_mitigated", 0)
        dmg_hl = p.get("total_heal", 0)
        dmg_soaked_tot = dmg_tk + dmg_mit

        vis_val = p.get("vision_score", 0)
        pinks_val = p.get("detector_wards", 0)
        camps_stolen_val = p.get("enemy_jungle_monsters", 0)

        lbl_dmg = get_text("dmg_dealt", lang=lang)
        lbl_dmg_champs = get_text("damage_dealt_label", lang=lang)
        lbl_phys = get_text("dmg_physical", lang=lang)
        lbl_mag = get_text("dmg_magic", lang=lang)
        lbl_true = get_text("dmg_true", lang=lang)

        lbl_soaked = get_text("dmg_soaked", lang=lang)
        lbl_taken = get_text("damage_taken", lang=lang)
        lbl_mit = get_text("mitigated", lang=lang)
        lbl_hl = get_text("healed", lang=lang)

        lbl_dmg_turrets = get_text("turret_damage", lang=lang)
        lbl_turrets_k = get_text("turrets_destroyed", lang=lang)
        lbl_inhibs_k = get_text("inhibs_destroyed", lang=lang)
        turret_dmg_val = p.get("damage_to_turrets", 0) or p.get("damage_to_buildings", 0)
        turret_kills_val = p.get("turret_kills", 0)
        inhib_kills_val = p.get("inhibitor_kills", 0)
        wards_killed_val = p.get("wards_killed", 0)
        wards_placed_val = p.get("wards_placed", 0)
        pinks_bought_val = p.get("vision_wards_bought", 0)

        # 2. Clean multi-line HTML tooltip for Damage Pill
        dmg_tot_all = p.get("damage_total_all", 0)
        dmg_obj = p.get("damage_to_objectives", 0)
        dmg_tooltip_lines = [
            f"<b>💥 {lbl_dmg_champs}: {dmg_tot:,}</b>",
            f"  &nbsp; ↳ {lbl_phys}: <b class='dmg-phys'>{dmg_phys:,}</b>",
            f"  &nbsp; ↳ {lbl_mag}: <b class='dmg-mag'>{dmg_mag:,}</b>",
            f"  &nbsp; ↳ {lbl_true}: <b class='dmg-true'>{dmg_tru:,}</b>",
            f"<hr style='border:0; border-top:1px solid #334155; margin:4px 0;'/>",
            f"• {get_text('damage_total_all', lang=lang)}: <b>{dmg_tot_all:,}</b>",
            f"• {get_text('damage_objectives', lang=lang)}: <b>{dmg_obj:,}</b>",
            f"• {lbl_dmg_turrets}: <b>{turret_dmg_val:,}</b>",
            f"• {lbl_turrets_k}: <b>{turret_kills_val}</b>",
            f"• {lbl_inhibs_k}: <b>{inhib_kills_val}</b>"
        ]
        dmg_tooltip_html = "<br/>".join(dmg_tooltip_lines).replace('"', '&quot;')

        line_1_dmg = f"""
        <div class="pill pill-wide pill-interactive" onclick="this.classList.toggle('is-pinned')" data-tooltip="{dmg_tooltip_html}">
            <div class="pill-content-main">
                <span>{lbl_dmg}: <b>{dmg_tot:,}</b> {dmg_delta_tag}</span>
            </div>
            <div class="pill-content-detail">
                <span class="dmg-breakdown-sub">{lbl_phys}: <b class="dmg-phys">{dmg_phys:,}</b> <span class="breakdown-dot">•</span> {lbl_mag}: <b class="dmg-mag">{dmg_mag:,}</b> <span class="breakdown-dot">•</span> {lbl_true}: <b class="dmg-true">{dmg_tru:,}</b></span>
            </div>
        </div>
        """

        # 3. Clean multi-line HTML tooltip for Soaked/Tanked Pill
        tk_phys = p.get("damage_taken_physical", 0)
        tk_mag = p.get("damage_taken_magic", 0)
        tk_tru = p.get("damage_taken_true", 0)
        soaked_tooltip_lines = [
            f"<b>🛡️ {lbl_soaked}: {dmg_soaked_tot:,}</b>",
            f"• {lbl_taken}: <b>{dmg_tk:,}</b>",
            f"  &nbsp; ↳ {get_text('damage_taken_phys', lang=lang)}: <b class='dmg-phys'>{tk_phys:,}</b>",
            f"  &nbsp; ↳ {get_text('damage_taken_mag', lang=lang)}: <b class='dmg-mag'>{tk_mag:,}</b>",
            f"  &nbsp; ↳ {get_text('damage_taken_tru', lang=lang)}: <b class='dmg-true'>{tk_tru:,}</b>",
            f"<hr style='border:0; border-top:1px solid #334155; margin:4px 0;'/>",
            f"• {lbl_mit}: <b class='dmg-mit'>{dmg_mit:,}</b>",
            f"• {lbl_hl}: <b class='dmg-hl'>{dmg_hl:,}</b>"
        ]
        soaked_tooltip_html = "<br/>".join(soaked_tooltip_lines).replace('"', '&quot;')

        line_2_soaked = f"""
        <div class="pill pill-wide pill-interactive" onclick="this.classList.toggle('is-pinned')" data-tooltip="{soaked_tooltip_html}">
            <div class="pill-content-main">
                <span>{lbl_soaked}: <b>{dmg_soaked_tot:,}</b></span>
            </div>
            <div class="pill-content-detail">
                <span class="dmg-breakdown-sub">{lbl_taken}: <b class="dmg-tk">{dmg_tk:,}</b> <span class="breakdown-dot">•</span> {lbl_mit}: <b class="dmg-mit">{dmg_mit:,}</b> <span class="breakdown-dot">•</span> {lbl_hl}: <b class="dmg-hl">{dmg_hl:,}</b></span>
            </div>
        </div>
        """

        # 4. Clean multi-line HTML tooltip for Gold & CS Pill with official icons
        gold_spent_val = p.get("gold_spent", 0)
        minions_val = p.get("minions_killed", 0)
        neutral_val = p.get("neutral_minions_killed", 0)
        ally_jg_val = p.get("ally_jungle_monsters", 0)
        enemy_jg_val = p.get("enemy_jungle_monsters", 0)

        gold_lbl = get_text('gold', lang=lang)
        if p.get("is_team_combined") and is_arena:
            anvils_cnt = p.get("purchased_anvils", 0)
            anvil_lbl = get_text("purchased_stat_anvils", lang=lang)
            anvil_icon_url = "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/220000.png"
            gold_cs_tooltip_lines = [
                f"<b><i class='mini-icon icon-bg ico-gold'></i> {gold_lbl}: {p['gold_total']:,}</b>",
                f"• {get_text('gold_spent', lang=lang)}: <b>{gold_spent_val:,}</b>",
                f"• {get_text('efficiency', lang=lang)}: <b>{p['damage_per_gold']} dmg/g</b>",
                f"<hr style='border:0; border-top:1px solid #334155; margin:4px 0;'/>",
                f"<b><img class='mini-icon mini-icon-round' src='{anvil_icon_url}'/> {anvil_lbl}: {anvils_cnt}</b>"
            ]
            gold_cs_tooltip_html = "<br/>".join(gold_cs_tooltip_lines).replace('"', '&quot;')
            cs_or_anvils_slot = f"""
            <div class="anvil-purchased-badge" style="display:inline-flex; align-items:center; gap:4px; padding:1px 6px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:12px; font-size:0.72rem; font-weight:700; color:#f8fafc;">
                <img src="{anvil_icon_url}" style="width:14px; height:14px; border-radius:50%; display:block;" alt="Anvil"/>
                <span style="color:#f8fafc;">{anvils_cnt}</span>
                <i class="stat-ico ico-gold" style="width:11px; height:11px; display:inline-block;"></i>
            </div>
            """
        else:
            gold_cs_tooltip_lines = [
                f"<b><i class='mini-icon icon-bg ico-gold'></i> {gold_lbl}: {p['gold_total']:,}</b>",
                f"• {get_text('gold_spent', lang=lang)}: <b>{gold_spent_val:,}</b>",
                f"• {get_text('efficiency', lang=lang)}: <b>{p['damage_per_gold']} dmg/g</b>",
                f"<hr style='border:0; border-top:1px solid #334155; margin:4px 0;'/>",
                f"<b><i class='mini-icon icon-bg ico-cs'></i> CS Total: {p['cs']} ({p['cs_per_min']}/min)</b>",
                f"• {get_text('lane_minions', lang=lang)}: <b>{minions_val}</b>"
            ]
            if neutral_val > 0 or ally_jg_val > 0 or enemy_jg_val > 0:
                gold_cs_tooltip_lines.append(f"• {get_text('neutral_minions', lang=lang)}: <b>{neutral_val}</b> (<i class='mini-icon mini-icon-round icon-bg aico-gromp_icon'></i> {get_text('ally_jungle', lang=lang)}: {ally_jg_val} • ⚔️ {get_text('enemy_jungle', lang=lang)}: {enemy_jg_val})")
            gold_cs_tooltip_html = "<br/>".join(gold_cs_tooltip_lines).replace('"', '&quot;')
            cs_or_anvils_slot = f"""<span><i class="mini-icon icon-bg ico-cs"></i> {cs_display}</span>"""

        line_3_gold_cs = f"""
        <div class="pill pill-wide" data-tooltip="{gold_cs_tooltip_html}">
            <span><i class="mini-icon icon-bg ico-gold"></i> <b>{p['gold_total']:,}</b> {gold_delta_tag} <span style="color:var(--text-muted); font-size:0.75rem;">({p['damage_per_gold']} dmg/g)</span></span>
            {cs_or_anvils_slot}
        </div>
        """

        # 5. Clean multi-line HTML tooltip for Vision Pill
        vis_tooltip_lines = [
            f"<div style='margin-bottom:4px;'><b><i class='mini-icon-gromp icon-bg aico-award_visionary'></i> {get_text('vision_score', lang=lang)}: {vis_val}</b></div>",
            f"• <i class='mini-icon mini-icon-round icon-bg aico-stealth_ward'></i> {get_text('wards_placed', lang=lang)}: <b>{wards_placed_val}</b>",
            f"• <img class='mini-icon mini-icon-round' src='{icon_pink}'/> {get_text('control_wards_placed', lang=lang)}: <b>{pinks_val}</b>",
            f"• <img class='mini-icon mini-icon-round' src='{icon_pink}'/> {get_text('control_wards_bought', lang=lang)}: <b>{pinks_bought_val}</b>",
            f"• <i class='mini-icon mini-icon-round icon-bg aico-oracle_lens'></i> {get_text('wards_killed', lang=lang)}: <b>{wards_killed_val}</b>"
        ]
        if camps_stolen_val > 0:
            vis_tooltip_lines.append(f"<hr style='border:0; border-top:1px solid #334155; margin:4px 0;'/>")
            vis_tooltip_lines.append(f"<i class='mini-icon-gromp icon-bg aico-gromp_icon'></i> {get_text('camps_stolen', lang=lang)}: <b>{camps_stolen_val}</b>")
        vis_tooltip_html = "<br/>".join(vis_tooltip_lines).replace('"', '&quot;')

        pink_badge = f"<img class='mini-icon mini-icon-round' src='{icon_pink}'/> <b>{pinks_val}</b>"
        ward_kill_badge = f"<span style='color:#cbd5e1;'><i class='mini-icon mini-icon-round icon-bg aico-oracle_lens'></i> <b>{wards_killed_val}</b></span>" if wards_killed_val > 0 else ""
        vis_badges = f"({pink_badge}{(' • ' + ward_kill_badge) if ward_kill_badge else ''})"
        vis_combined = f"{get_text('vision_score', lang=lang)}: <b>{vis_val}</b> {vis_badges}"

        # Hide jungle stolen in ARAM/Arena
        camps_item = f"<span><i class='mini-icon-gromp icon-bg aico-gromp_icon' title='Gromp'></i> {get_text('camps_stolen', lang=lang)}: <b>{camps_stolen_val}</b></span>" if (not is_aram and not is_arena) else ""

        line_4_vision_camps = f"""
        <div class="pill pill-wide" data-tooltip="{vis_tooltip_html}">
            <span>{vis_combined}</span>
            {camps_item}
        </div>
        """ if (not is_arena or camps_stolen_val > 0) else ""


        footer_bottom = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-top:8px;">
            <div class="items-flex">{items_html}</div>
            {spells_runes_strip}
        </div>
        {augments_strip}
        """ if (items_html or spells_runes_strip or augments_strip) else ""

        return f"""
        <div class="player-card {align_class} {border_side} {'is-target' if is_target else ''}">
            {header_html}
            <div class="stats-pills">
                {line_1_dmg}
                {line_2_soaked}
                {line_3_gold_cs}
                {line_4_vision_camps}
            </div>
            {footer_bottom}
            {obj_strip_html}
        </div>
        """

    p1_html = p_card(p1, is_t1, is_left=True, badges_html=extra_badges_1,
                     is_dmg_leader=(dmg_delta > 0), is_gold_leader=(gold_delta_final > 0),
                     delta_dmg=abs(dmg_delta), delta_gold=abs(gold_delta_final))

    p2_html = p_card(p2, is_t2, is_left=False, badges_html=extra_badges_2,
                     is_dmg_leader=(dmg_delta < 0), is_gold_leader=(gold_delta_final < 0),
                     delta_dmg=abs(dmg_delta), delta_gold=abs(gold_delta_final))

    def format_delta_badge(time_label: str, delta_item: Any, is_xp: bool = False) -> str:
        unit = "XP" if is_xp else "gold"
        c1 = p1.get("champion", "Blue")
        c2 = p2.get("champion", "Red")
        
        if isinstance(delta_item, dict):
            diff = delta_item.get("diff", 0)
            v1 = delta_item.get("p1_val", 0)
            v2 = delta_item.get("p2_val", 0)
        else:
            diff = int(delta_item)
            v1, v2 = None, None

        lead_lbl = get_text("lead_label", lang=lang)
        even_lbl = get_text("even_label", lang=lang)

        if diff > 0:
            lead_txt = f"<b style='color:#60a5fa;'>+{diff:,} {unit} ({c1})</b>"
            cls_name = "delta-blue"
            display_val = f"{diff:,}"
        elif diff < 0:
            lead_txt = f"<b style='color:#f87171;'>+{abs(diff):,} {unit} ({c2})</b>"
            cls_name = "delta-red"
            display_val = f"{abs(diff):,}"
        else:
            lead_txt = f"<b style='color:#94a3b8;'>{even_lbl} (0 {unit})</b>"
            cls_name = "delta-even"
            display_val = "0"

        if v1 is not None and v2 is not None:
            tt_html = f"<div style='text-align:left; font-size:0.75rem; line-height:1.4;'><span style='color:#60a5fa;'>🔵 {c1}:</span> <b>{v1:,}</b> {unit}<br/><span style='color:#f87171;'>🔴 {c2}:</span> <b>{v2:,}</b> {unit}<br/><hr style='border:0; border-top:1px solid #334155; margin:3px 0;'/>{lead_lbl} {lead_txt}</div>"
        else:
            tt_html = f"{lead_lbl} {lead_txt}"

        return f'<span class="delta-tag" title="{tt_html}">{time_label}: <b class="{cls_name}">{display_val}</b></span>'


    delta_html = ""
    if gold_d:
        gold_tags = "".join([format_delta_badge(k, v, is_xp=False) for k, v in gold_d.items()])
        xp_tags = "".join([format_delta_badge(k, v, is_xp=True) for k, v in xp_d.items()]) if xp_d else ""



        solo_deaths_1 = stats_1.get("solo_deaths", 0) if stats_1 else 0
        solo_deaths_2 = stats_2.get("solo_deaths", 0) if stats_2 else 0

        duel_info_box = ""
        if is_team_comb:
            exec_1 = p1.get("executions", 0)
            exec_2 = p2.get("executions", 0)
            if exec_1 > 0 or exec_2 > 0:
                duel_info_box = f"""
                <div class="duel-scores-wrapper" style="margin-top: 6px;">
                    <div class="duel-score-row" title="{get_text('executions_tt_title', lang=lang)}">
                        <span class="score-label" style="color:#94a3b8; cursor:help;">💀 {get_text("executions", lang=lang)}</span>
                        <div class="score-pill-sm" style="background:#1e293b; border-color:#334155; cursor:help;">
                            <b class="score-blue-sm" style="color:#cbd5e1;">{exec_1}</b>
                            <span class="score-x-sm">x</span>
                            <b class="score-red-sm" style="color:#cbd5e1;">{exec_2}</b>
                        </div>
                    </div>
                </div>
                """
        elif not is_bot_duo:
            other_1 = stats_1.get("other_deaths", 0) if stats_1 else 0
            other_2 = stats_2.get("other_deaths", 0) if stats_2 else 0
            exec_1 = stats_1.get("executions", 0) if stats_1 else 0
            exec_2 = stats_2.get("executions", 0) if stats_2 else 0
            exec_html = ""
            if exec_1 > 0 or exec_2 > 0:
                exec_html = f"""
                <div class="duel-score-row" style="margin-top: 3px;">
                    <span class="score-label" style="color:#94a3b8;">💀 {get_text("executions", lang=lang)}</span>
                    <div class="score-pill-sm" style="background:#1e293b; border-color:#334155;">
                        <b class="score-blue-sm" style="color:#cbd5e1;">{exec_1}</b>
                        <span class="score-x-sm">x</span>
                        <b class="score-red-sm" style="color:#cbd5e1;">{exec_2}</b>
                    </div>
                </div>
                """
            duel_info_box = f"""
            <div class="duel-scores-wrapper">
                <div class="duel-score-row" title="{get_text('deaths_to_laners_tt', lang=lang)}">
                    <span class="score-label">{get_text("solo_deaths", lang=lang)}</span>
                    <div class="score-pill-lg">
                        <b class="score-blue-lg">{solo_deaths_1}</b>
                        <span class="score-x-lg">x</span>
                        <b class="score-red-lg">{solo_deaths_2}</b>
                    </div>
                </div>
                <div class="duel-score-row" style="margin-top: 3px;" title="{get_text('deaths_to_others_tt', lang=lang)}">
                    <span class="score-label">{get_text("other_deaths", lang=lang)}</span>
                    <div class="score-pill-sm">
                        <b class="score-blue-sm">{other_1}</b>
                        <span class="score-x-sm">x</span>
                        <b class="score-red-sm">{other_2}</b>
                    </div>
                </div>
                {exec_html}
            </div>
            """
        else:
            lane_d1 = stats_1.get("d1_lane_deaths", 0) if stats_1 else 0
            lane_d2 = stats_1.get("d2_lane_deaths", 0) if stats_1 else 0
            other_d1 = stats_1.get("d1_other_deaths", 0) if stats_1 else 0
            other_d2 = stats_1.get("d2_other_deaths", 0) if stats_1 else 0
            exec_d1 = stats_1.get("d1_executions", 0) if stats_1 else 0
            exec_d2 = stats_1.get("d2_executions", 0) if stats_1 else 0
            exec_html = ""
            if exec_d1 > 0 or exec_d2 > 0:
                exec_html = f"""
                <div class="duel-score-row" style="margin-top: 3px;">
                    <span class="score-label" style="color:#94a3b8;">💀 {get_text("executions", lang=lang)}</span>
                    <div class="score-pill-sm" style="background:#1e293b; border-color:#334155;">
                        <b class="score-blue-sm" style="color:#cbd5e1;">{exec_d1}</b>
                        <span class="score-x-sm">x</span>
                        <b class="score-red-sm" style="color:#cbd5e1;">{exec_d2}</b>
                    </div>
                </div>
                """
            duel_info_box = f"""
            <div class="duel-scores-wrapper">
                <div class="duel-score-row" title="{get_text('deaths_to_laners_tt', lang=lang)}">
                    <span class="score-label">{get_text("lane_deaths", lang=lang)}</span>
                    <div class="score-pill-lg">
                        <b class="score-blue-lg">{lane_d1}</b>
                        <span class="score-x-lg">x</span>
                        <b class="score-red-lg">{lane_d2}</b>
                    </div>
                </div>
                <div class="duel-score-row" style="margin-top: 3px;" title="{get_text('deaths_to_others_tt', lang=lang)}">
                    <span class="score-label">{get_text("other_deaths", lang=lang)}</span>
                    <div class="score-pill-sm">
                        <b class="score-blue-sm">{other_d1}</b>
                        <span class="score-x-sm">x</span>
                        <b class="score-red-sm">{other_d2}</b>
                    </div>
                </div>
                {exec_html}
            </div>
            """




        badge_style = 'background:#3730a3; color:#c7d2fe;' if is_team_comb else ''
        badge_html = f'<div class="role-badge-lg" style="{badge_style}">{role_title}</div>' if badge_style else f'<div class="role-badge-lg">{role_title}</div>'
        bar_tt = get_text("gold_dist_team_tt", lang=lang) if is_team_comb else (get_text("gold_dist_duo_tt", lang=lang) if is_bot_duo else get_text("gold_dist_duel_tt", lang=lang))

        delta_html = f"""
        <div class="duel-center">
            {badge_html}
            
            <div class="lane-bar-wrapper">
                {gap_badge_left}
                <div class="lane-bar-container" title="{bar_tt}">
                    <div class="lane-bar-blue" style="width: {p1_share:.1f}%;"></div>
                    <div class="lane-bar-red" style="width: {p2_share:.1f}%;"></div>
                </div>
                {gap_badge_right}
            </div>

            {duel_info_box}

            <div class="delta-box">
                <div class="delta-title"><i class="mini-icon icon-bg ico-gold"></i> {get_text("gold_delta_title", lang=lang)}</div>
                <div class="delta-flex">{gold_tags}</div>
                {f'<div class="delta-title" style="margin-top:5px;"><i class="mini-icon icon-bg ico-xp"></i> {get_text("xp_delta_title", lang=lang)}</div><div class="delta-flex">{xp_tags}</div>' if xp_tags else ''}
            </div>
        </div>
        """
    else:
        exec_1 = stats_1.get("executions", 0) if stats_1 else 0
        exec_2 = stats_2.get("executions", 0) if stats_2 else 0
        aram_exec_html = ""
        if exec_1 > 0 or exec_2 > 0:
            aram_exec_html = f"""
            <div class="duel-scores-wrapper" style="margin: 0;">
                <div class="duel-score-row">
                    <span class="score-label" style="color:#94a3b8;">💀 {get_text("executions", lang=lang)}</span>
                    <div class="score-pill-sm" style="background:#1e293b; border-color:#334155;">
                        <b class="score-blue-sm" style="color:#cbd5e1;">{exec_1}</b>
                        <span class="score-x-sm">x</span>
                        <b class="score-red-sm" style="color:#cbd5e1;">{exec_2}</b>
                    </div>
                </div>
            </div>
            """

        # In Arena Team Combined: Show Damage Distribution Bar & Kill Ratio
        if is_arena and is_bot_duo:
            d1 = p1.get("damage_to_champions", 0)
            d2 = p2.get("damage_to_champions", 0)
            tot_d = max(d1 + d2, 1)
            pct1 = (d1 / tot_d) * 100.0
            pct2 = (d2 / tot_d) * 100.0
            
            d_diff = d1 - d2
            if d_diff > 0:
                lead_txt = f"<b style='color:#60a5fa;'>+{d_diff:,} ({pct1:.1f}%)</b>"
            elif d_diff < 0:
                lead_txt = f"<b style='color:#f87171;'>+{abs(d_diff):,} ({pct2:.1f}%)</b>"
            else:
                lead_txt = "<b style='color:#94a3b8;'>50% / 50%</b>"

            bar_tt = get_text("dmg_share_tt", lang=lang, pct1=pct1, d1=d1, pct2=pct2, d2=d2)
            
            delta_html = f"""
            <div class="duel-center" style="justify-content:center; gap:6px;">
                <div class="role-badge-lg" style="background:#1e293b; color:#a5b4fc; border: 1px solid #4338ca;">{role_title}</div>
                <div class="lane-bar-wrapper" style="margin-top:4px;">
                    <div class="dmg-bar-container" title="{bar_tt}" style="cursor:help;">
                        <div class="dmg-bar-blue" style="width: {pct1:.1f}%;"></div>
                        <div class="dmg-bar-red" style="width: {pct2:.1f}%;"></div>
                    </div>
                </div>
                <div style="font-size:0.75rem; color:#94a3b8; font-weight:700; text-align:center; cursor:help;" title="{bar_tt}">
                    ⚔️ {lead_txt}
                </div>
            </div>
            """

        else:
            badge_html = f'<div class="role-badge-lg" style="background:#1e293b; color:#94a3b8; border: 1px solid #334155;">{role_title}</div>' if role_title else ''
            delta_html = f"""
            <div class="duel-center" style="{'justify-content:center;' if not badge_html else ''}">
                {badge_html}
                {aram_exec_html}
            </div>
            """




    return f"""
    <div class="duel-row {'bot-duo-row' if is_bot_duo else ''} {'team-combined-row' if is_team_comb else ''}">
        {p1_html}
        {delta_html}
        {p2_html}
    </div>
    """

