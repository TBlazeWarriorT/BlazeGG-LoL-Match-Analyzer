import webbrowser
from pathlib import Path
from typing import Dict, Any, List
from .config import CACHE_DIR
from .asset_cache import AssetManager
from .i18n import get_text

REPORT_FILE = CACHE_DIR / "last_report.html"

def calculate_gold_bar_share(delta: int, max_delta: float = 5000.0) -> float:
    fraction = delta / float(max_delta)
    val = 50.0 + (fraction * 50.0)
    return max(4.0, min(96.0, val))

def generate_html_report(data: Dict[str, Any], open_browser: bool = True, lang: str = "pt_BR") -> Path:
    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    matchups = data.get("matchups", [])
    jungle = data.get("jungle_stats", {})
    target_puuid = data.get("target_puuid", "")
    raw_summary = data.get("raw_summary_text", "")
    dur_s_game = data.get("duration_seconds", 0)
    if not dur_s_game:
        # Fallback parsing duration string 'Xm Ys'
        dur_str = data.get("duration", "0m 0s")
        try:
            m_part = int(dur_str.split("m")[0].strip()) if "m" in dur_str else 0
            s_part = int(dur_str.split("m")[1].replace("s", "").strip()) if "m" in dur_str and "s" in dur_str else 0
            dur_s_game = m_part * 60 + s_part
        except Exception:
            dur_s_game = 1800

    icon_gold = AssetManager.get_asset_uri("gold_icon")
    icon_xp = AssetManager.get_asset_uri("xp_icon")
    icon_cs = AssetManager.get_asset_uri("cs_icon")
    icon_pink = "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/2055.png"

    t100_win = team_100.get("win", False)
    t200_win = team_200.get("win", False)
    t100_txt = get_text("win", lang=lang) if t100_win else get_text("loss", lang=lang)
    t200_txt = get_text("win", lang=lang) if t200_win else get_text("loss", lang=lang)
    t100_class = "win-badge" if t100_win else "loss-badge"
    t200_class = "win-badge" if t200_win else "loss-badge"

    t100_status = f'<span class="badge {t100_class}">{t100_txt}</span>'
    t200_status = f'<span class="badge {t200_class}">{t200_txt}</span>'

    j100 = jungle.get(100, {})
    j200 = jungle.get(200, {})

    def render_jungle_chronological(seq):
        if not seq:
            return f'<div class="empty-jungle-slot">{"Nenhum objetivo neutro" if lang=="pt_BR" else "No neutral objectives"}</div>'
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

    def render_duel_row(p1, p2, role_title, stats_1=None, stats_2=None, gold_d=None, xp_d=None, is_bot_duo=False, extra_badges_1="", extra_badges_2=""):
        is_t1 = p1.get("puuid") == target_puuid
        is_t2 = p2.get("puuid") == target_puuid

        # Deltas finais (Dano e Ouro)
        dmg_delta = p1.get("damage_to_champions", 0) - p2.get("damage_to_champions", 0)
        gold_delta_final = p1.get("gold_total", 0) - p2.get("gold_total", 0)

        bar_threshold = 8000.0 if is_bot_duo else 5000.0
        p1_share = calculate_gold_bar_share(gold_delta_final, max_delta=bar_threshold)
        p2_share = 100.0 - p1_share

        gap_limit = 3500 if is_bot_duo else 2000
        gap_badge_left = '<span class="gap-seal gap-left">GAP! 🔥</span>' if gold_delta_final >= gap_limit else ""
        gap_badge_right = '<span class="gap-seal gap-right">GAP! 🔥</span>' if gold_delta_final <= -gap_limit else ""

        def p_card(p, is_target, is_left=True, badges_html="", is_dmg_leader=False, is_gold_leader=False, delta_dmg=0, delta_gold=0):
            align_class = "align-left" if is_left else "align-right"
            border_side = "border-blue" if is_left else "border-red"
            target_badge = f'<span class="target-tag">{get_text("you_tag", lang=lang)}</span>' if is_target else ""
            
            # Badges verdes de delta final
            dmg_delta_tag = f'<span class="lead-delta">+{delta_dmg:,}</span>' if is_dmg_leader and delta_dmg > 0 else ""
            gold_delta_tag = f'<span class="lead-delta">+{delta_gold:,}</span>' if is_gold_leader and delta_gold > 0 else ""

            kda_ratio_tag = f'<span class="kda-ratio">({p.get("kda_ratio", "")})</span>' if p.get("kda_ratio") else ""

            cs_val = p.get("cs", 0)
            cs_pm = p.get("cs_per_min", 0)
            cs_display = f"<b>{cs_val}</b> <span style='color:var(--text-muted); font-size:0.78rem;'>({cs_pm}/m)</span>"

            icon_pink = "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/2055.png"

            if is_bot_duo:
                header_html = f"""
                <div class="p-header">
                    <div class="duo-avatar-stack">
                        <img class="champ-icon duo-icon-1" src="{p['icon1']}" alt="{p['champ1']}"/>
                        <img class="champ-icon duo-icon-2" src="{p['icon2']}" alt="{p['champ2']}"/>
                    </div>
                    <div class="p-meta">
                        <div class="p-name">{p['champ1']} &amp; {p['champ2']} {target_badge}</div>
                        <div class="p-champ">{get_text("bot_duo_sub", lang=lang)}</div>
                    </div>
                </div>
                """
                spells_runes_strip = ""
                items_html = ""
            else:
                header_html = f"""
                <div class="p-header">
                    <img class="champ-icon" src="{p['champion_icon']}" alt="{p['champion']}"/>
                    <div class="p-meta">
                        <div class="p-name">{p['riot_id']} {target_badge}</div>
                        <div class="p-champ">{p['champion']}</div>
                    </div>
                </div>
                """
                spells_html = "".join([
                    f'<img class="spell-icon" src="{s["icon"]}" title="{s["name"]}" alt="{s["name"]}"/>'
                    for s in p.get("spells", []) if s.get("icon")
                ])
                rune_info = p.get("rune", {})
                rune_html = f'<img class="rune-icon" src="{rune_info["icon"]}" title="{rune_info["name"]}" alt="{rune_info["name"]}"/>' if rune_info.get("icon") else ""

                spells_runes_strip = f"""
                <div class="spells-runes-strip">
                    {rune_html}
                    <div class="spells-row">{spells_html}</div>
                </div>
                """ if (spells_html or rune_html) else ""

                items_html = "".join([
                    f'<img class="item-icon" src="{it["icon"]}" title="{it["name"]}" alt="{it["name"]}"/>'
                    for it in p.get("items", [])
                ])

            obj_strip_html = f'<div class="jungle-mini-strip">{badges_html}</div>' if badges_html else ""

            # Breakdown de dano causado
            dmg_tot = p.get("damage_to_champions", 0)
            dmg_phys = p.get("damage_physical", 0)
            dmg_mag = p.get("damage_magic", 0)
            dmg_tru = p.get("damage_true", 0)

            # Breakdown de dano sofrido, mitigado e curado
            dmg_tk = p.get("damage_taken", 0)
            dmg_mit = p.get("damage_mitigated", 0)
            dmg_hl = p.get("total_heal", 0)
            dmg_soaked_tot = dmg_tk + dmg_mit

            vis_val = p.get("vision_score", 0)
            pinks_val = p.get("detector_wards", 0)
            camps_stolen_val = p.get("enemy_jungle_monsters", 0)

            lbl_dmg = get_text("dmg_dealt", lang=lang)
            lbl_phys = get_text("dmg_physical", lang=lang)
            lbl_mag = get_text("dmg_magic", lang=lang)
            lbl_true = get_text("dmg_true", lang=lang)

            lbl_soaked = get_text("dmg_soaked", lang=lang)
            lbl_taken = get_text("damage_taken", lang=lang)
            lbl_mit = get_text("mitigated", lang=lang)
            lbl_hl = get_text("healed", lang=lang)

            # 4 linhas padronizadas
            line_1_dmg = f"""
            <div class="pill pill-wide" title="{lbl_phys}: {dmg_phys:,} | {lbl_mag}: {dmg_mag:,} | {lbl_true}: {dmg_tru:,}">
                <span>{lbl_dmg}: <b>{dmg_tot:,}</b> {dmg_delta_tag}</span>
                <span class="dmg-breakdown-sub"><span style="color:#475569;">|</span> {lbl_phys}: <b class="dmg-phys">{dmg_phys:,}</b> <span style="color:#475569;">|</span> {lbl_mag}: <b class="dmg-mag">{dmg_mag:,}</b> <span style="color:#475569;">|</span> {lbl_true}: <b class="dmg-true">{dmg_tru:,}</b></span>
            </div>
            """

            line_2_soaked = f"""
            <div class="pill pill-wide" title="{lbl_taken}: {dmg_tk:,} | {lbl_mit}: {dmg_mit:,} | {lbl_hl}: {dmg_hl:,}">
                <span>{lbl_soaked}: <b>{dmg_soaked_tot:,}</b></span>
                <span class="dmg-breakdown-sub"><span style="color:#475569;">|</span> {lbl_taken}: <b class="dmg-tk">{dmg_tk:,}</b> <span style="color:#475569;">|</span> {lbl_mit}: <b class="dmg-mit">{dmg_mit:,}</b> <span style="color:#475569;">|</span> {lbl_hl}: <b class="dmg-hl">{dmg_hl:,}</b></span>
            </div>
            """

            line_3_gold_cs = f"""
            <div class="pill pill-wide">
                <span><img class="mini-icon" src="{icon_gold}"/> <b>{p['gold_total']:,}</b> {gold_delta_tag} <span style="color:var(--text-muted); font-size:0.75rem;">(dmg/g: <b>{p['damage_per_gold']}</b>)</span></span>
                <span><img class="mini-icon" src="{icon_cs}"/> {cs_display}</span>
            </div>
            """

            pink_badge = f"<span style='display:inline-flex; align-items:center; gap:2px;'><img class='mini-icon mini-icon-round' src='{icon_pink}' title='Control Wards'/> <b>{pinks_val}</b></span>"
            vis_combined = f"{get_text('vision_score', lang=lang)}: <b>{vis_val}</b> ({pink_badge})"

            line_4_vision_camps = f"""
            <div class="pill pill-wide">
                <span>{vis_combined}</span>
                <span>🌲 {get_text('camps_stolen', lang=lang)}: <b>{camps_stolen_val}</b></span>
            </div>
            """

            footer_bottom = f"""
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-top:8px;">
                <div class="items-flex">{items_html}</div>
                {spells_runes_strip}
            </div>
            """ if (items_html or spells_runes_strip) else ""

            return f"""
            <div class="player-card {align_class} {border_side} {'is-target' if is_target else ''}">
                {header_html}
                <div class="p-kda">{get_text('champion', lang=lang) if is_bot_duo else p['champion']} - KDA: <b>{p['kda']}</b> {kda_ratio_tag}</div>
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

        delta_html = ""
        if gold_d:
            gold_tags = "".join([
                f'<span class="delta-tag">{k}: <b class="{"pos" if v>=0 else "neg"}">{"+" if v>=0 else ""}{v:,}</b></span>'
                for k, v in gold_d.items()
            ])
            xp_tags = "".join([
                f'<span class="delta-tag">{k}: <b class="{"pos" if v>=0 else "neg"}">{"+" if v>=0 else ""}{v:,}</b></span>'
                for k, v in xp_d.items()
            ]) if xp_d else ""

            solo_deaths_1 = stats_1.get("solo_deaths", 0) if stats_1 else 0
            solo_deaths_2 = stats_2.get("solo_deaths", 0) if stats_2 else 0

            duel_info_box = ""
            if not is_bot_duo:
                other_1 = stats_1.get("other_deaths", 0) if stats_1 else 0
                other_2 = stats_2.get("other_deaths", 0) if stats_2 else 0
                duel_info_box = f"""
                <div class="duel-scores-wrapper">
                    <div class="duel-score-row">
                        <span class="score-label">{get_text("solo_deaths", lang=lang)}</span>
                        <div class="score-pill-lg">
                            <b class="score-blue-lg">{solo_deaths_1}</b>
                            <span class="score-x-lg">x</span>
                            <b class="score-red-lg">{solo_deaths_2}</b>
                        </div>
                    </div>
                    <div class="duel-score-row" style="margin-top: 3px;">
                        <span class="score-label">{get_text("other_deaths", lang=lang)}</span>
                        <div class="score-pill-sm">
                            <b class="score-blue-sm">{other_1}</b>
                            <span class="score-x-sm">x</span>
                            <b class="score-red-sm">{other_2}</b>
                        </div>
                    </div>
                </div>
                """

            delta_html = f"""
            <div class="duel-center">
                <div class="role-badge-lg">{role_title}</div>
                
                <div class="lane-bar-wrapper">
                    {gap_badge_left}
                    <div class="lane-bar-container" title="Distribuição de Ouro (5000 delta = barra cheia)">
                        <div class="lane-bar-blue" style="width: {p1_share:.1f}%;"></div>
                        <div class="lane-bar-red" style="width: {p2_share:.1f}%;"></div>
                    </div>
                    {gap_badge_right}
                </div>

                {duel_info_box}

                <div class="delta-box">
                    <div class="delta-title"><img class="mini-icon" src="{icon_gold}"/> {get_text("gold_delta_title", lang=lang)}</div>
                    <div class="delta-flex">{gold_tags}</div>
                    {f'<div class="delta-title" style="margin-top:5px;"><img class="mini-icon" src="{icon_xp}"/> {get_text("xp_delta_title", lang=lang)}</div><div class="delta-flex">{xp_tags}</div>' if xp_tags else ''}
                </div>
            </div>
            """
        else:
            delta_html = f"""
            <div class="duel-center">
                <div class="role-badge-lg">{role_title}</div>
                <div class="vs-label">VS</div>
            </div>
            """

        return f"""
        <div class="duel-row {'bot-duo-row' if is_bot_duo else ''}">
            {p1_html}
            {delta_html}
            {p2_html}
        </div>
        """

    duels_html = []
    m_by_role = {m["role"]: m for m in matchups}

    # TOP
    if "TOP" in m_by_role:
        m = m_by_role["TOP"]
        duels_html.append(render_duel_row(
            m["player1"], m["player2"], "TOP LANE",
            m["p1_stats"], m["p2_stats"],
            m["gold_delta"], m["xp_delta"]
        ))

    # JUNGLE
    if "JUNGLE" in m_by_role:
        m = m_by_role["JUNGLE"]
        j1_badges = render_jungle_chronological(j100.get('timeline_sequence', []))
        j2_badges = render_jungle_chronological(j200.get('timeline_sequence', []))

        duels_html.append(render_duel_row(
            m["player1"], m["player2"], "JUNGLE",
            m["p1_stats"], m["p2_stats"],
            m["gold_delta"], m["xp_delta"],
            extra_badges_1=j1_badges,
            extra_badges_2=j2_badges
        ))

    # MIDDLE
    if "MIDDLE" in m_by_role:
        m = m_by_role["MIDDLE"]
        duels_html.append(render_duel_row(
            m["player1"], m["player2"], "MID LANE",
            m["p1_stats"], m["p2_stats"],
            m["gold_delta"], m["xp_delta"]
        ))

    # BOTTOM (ADC) e UTILITY (SUP)
    m_bot = m_by_role.get("BOTTOM")
    m_sup = m_by_role.get("UTILITY")

    if m_bot:
        duels_html.append(render_duel_row(
            m_bot["player1"], m_bot["player2"], "ADC (BOTTOM)",
            m_bot["p1_stats"], m_bot["p2_stats"],
            m_bot["gold_delta"], m_bot["xp_delta"]
        ))

    if m_sup:
        duels_html.append(render_duel_row(
            m_sup["player1"], m_sup["player2"], "SUPORTE (UTILITY)",
            m_sup["p1_stats"], m_sup["p2_stats"],
            m_sup["gold_delta"], m_sup["xp_delta"]
        ))

    # BOT LANE (COMBINED 2v2)
    if m_bot and m_sup:
        p1_bot, p2_bot = m_bot["player1"], m_bot["player2"]
        p1_sup, p2_sup = m_sup["player1"], m_sup["player2"]

        d1_dmg = p1_bot["damage_to_champions"] + p1_sup["damage_to_champions"]
        d2_dmg = p2_bot["damage_to_champions"] + p2_sup["damage_to_champions"]
        d1_gold = p1_bot["gold_total"] + p1_sup["gold_total"]
        d2_gold = p2_bot["gold_total"] + p2_sup["gold_total"]
        d1_taken = p1_bot["damage_taken"] + p1_sup["damage_taken"]
        d2_taken = p2_bot["damage_taken"] + p2_sup["damage_taken"]
        d1_cs = p1_bot["cs"] + p1_sup["cs"]
        d2_cs = p2_bot["cs"] + p2_sup["cs"]
        d1_kills = p1_bot["kills"] + p1_sup["kills"]
        d1_deaths = p1_bot["deaths"] + p1_sup["deaths"]
        d1_assists = p1_bot["assists"] + p1_sup["assists"]
        d2_kills = p2_bot["kills"] + p2_bot["kills"]
        d2_deaths = p2_bot["deaths"] + p2_sup["deaths"]
        d2_assists = p2_bot["assists"] + p2_sup["assists"]

        ratio_d1 = (d1_kills + d1_assists) / max(d1_deaths, 1)
        ratio_d2 = (d2_kills + d2_assists) / max(d2_deaths, 1)

        dur_min_calc = max(dur_s_game / 60.0, 1.0)
        csm_d1 = round(d1_cs / dur_min_calc, 1)
        csm_d2 = round(d2_cs / dur_min_calc, 1)

        duo_p1 = {
            "champ1": p1_bot["champion"], "icon1": p1_bot["champion_icon"],
            "champ2": p1_sup["champion"], "icon2": p1_sup["champion_icon"],
            "kda": f"{d1_kills}/{d1_deaths}/{d1_assists}",
            "kda_ratio": f"{ratio_d1:.2f}:1" if d1_deaths > 0 else "Perfect",
            "cs": d1_cs,
            "cs_per_min": csm_d1,
            "damage_to_champions": d1_dmg,
            "damage_physical": p1_bot.get("damage_physical", 0) + p1_sup.get("damage_physical", 0),
            "damage_magic": p1_bot.get("damage_magic", 0) + p1_sup.get("damage_magic", 0),
            "damage_true": p1_bot.get("damage_true", 0) + p1_sup.get("damage_true", 0),
            "damage_per_gold": round(d1_dmg / max(d1_gold, 1), 2),
            "damage_taken": d1_taken,
            "damage_mitigated": p1_bot.get("damage_mitigated", 0) + p1_sup.get("damage_mitigated", 0),
            "total_heal": p1_bot.get("total_heal", 0) + p1_sup.get("total_heal", 0),
            "vision_score": p1_bot.get("vision_score", 0) + p1_sup.get("vision_score", 0),
            "detector_wards": p1_bot.get("detector_wards", 0) + p1_sup.get("detector_wards", 0),
            "enemy_jungle_monsters": p1_bot.get("enemy_jungle_monsters", 0) + p1_sup.get("enemy_jungle_monsters", 0),
            "gold_total": d1_gold,
            "puuid": p1_bot["puuid"] if target_puuid in (p1_bot["puuid"], p1_sup["puuid"]) else ""
        }

        duo_p2 = {
            "champ1": p2_bot["champion"], "icon1": p2_bot["champion_icon"],
            "champ2": p2_sup["champion"], "icon2": p2_sup["champion_icon"],
            "kda": f"{d2_kills}/{d2_deaths}/{d2_assists}",
            "kda_ratio": f"{ratio_d2:.2f}:1" if d2_deaths > 0 else "Perfect",
            "cs": d2_cs,
            "cs_per_min": csm_d2,
            "damage_to_champions": d2_dmg,
            "damage_physical": p2_bot.get("damage_physical", 0) + p2_sup.get("damage_physical", 0),
            "damage_magic": p2_bot.get("damage_magic", 0) + p2_sup.get("damage_magic", 0),
            "damage_true": p2_bot.get("damage_true", 0) + p2_sup.get("damage_true", 0),
            "damage_per_gold": round(d2_dmg / max(d2_gold, 1), 2),
            "damage_taken": d2_taken,
            "damage_mitigated": p2_bot.get("damage_mitigated", 0) + p2_sup.get("damage_mitigated", 0),
            "total_heal": p2_bot.get("total_heal", 0) + p2_sup.get("total_heal", 0),
            "vision_score": p2_bot.get("vision_score", 0) + p2_sup.get("vision_score", 0),
            "detector_wards": p2_bot.get("detector_wards", 0) + p2_sup.get("detector_wards", 0),
            "enemy_jungle_monsters": p2_bot.get("enemy_jungle_monsters", 0) + p2_sup.get("enemy_jungle_monsters", 0),
            "gold_total": d2_gold,
            "puuid": p2_bot["puuid"] if target_puuid in (p2_bot["puuid"], p2_sup["puuid"]) else ""
        }

        duo_delta_gold = {}
        duo_delta_xp = {}
        for k in m_bot["gold_delta"].keys():
            duo_delta_gold[k] = m_bot["gold_delta"].get(k, 0) + m_sup["gold_delta"].get(k, 0)
            duo_delta_xp[k] = m_bot["xp_delta"].get(k, 0) + m_sup["xp_delta"].get(k, 0)

        duels_html.append(render_duel_row(
            duo_p1, duo_p2, get_text("bot_duo_title", lang=lang),
            gold_d=duo_delta_gold,
            xp_d=duo_delta_xp,
            is_bot_duo=True
        ))

    # TEAM COMBINED (5v5 TOTAL)
    t1_players = team_100.get("players", [])
    t2_players = team_200.get("players", [])
    if t1_players and t2_players:
        t1_dmg = sum(p.get("damage_to_champions", 0) for p in t1_players)
        t2_dmg = sum(p.get("damage_to_champions", 0) for p in t2_players)
        t1_gold = sum(p.get("gold_total", 0) for p in t1_players)
        t2_gold = sum(p.get("gold_total", 0) for p in t2_players)
        t1_taken = sum(p.get("damage_taken", 0) for p in t1_players)
        t2_taken = sum(p.get("damage_taken", 0) for p in t2_players)
        t1_cs = sum(p.get("cs", 0) for p in t1_players)
        t2_cs = sum(p.get("cs", 0) for p in t2_players)
        t1_kills = sum(p.get("kills", 0) for p in t1_players)
        t1_deaths = sum(p.get("deaths", 0) for p in t1_players)
        t1_assists = sum(p.get("assists", 0) for p in t1_players)
        t2_kills = sum(p.get("kills", 0) for p in t2_players)
        t2_deaths = sum(p.get("deaths", 0) for p in t2_players)
        t2_assists = sum(p.get("assists", 0) for p in t2_players)

        ratio_t1 = (t1_kills + t1_assists) / max(t1_deaths, 1)
        ratio_t2 = (t2_kills + t2_assists) / max(t2_deaths, 1)

        csm_t1 = round(t1_cs / dur_min_calc, 1)
        csm_t2 = round(t2_cs / dur_min_calc, 1)

        t1_icons_html = "".join([f'<img class="team-champ-mini" src="{p["champion_icon"]}" title="{p["champion"]}"/>' for p in t1_players])
        t2_icons_html = "".join([f'<img class="team-champ-mini" src="{p["champion_icon"]}" title="{p["champion"]}"/>' for p in t2_players])

        # Somar deltas de ouro ao longo do jogo de todos os confrontos
        team_delta_gold = {}
        for m in matchups:
            for k, v in m.get("gold_delta", {}).items():
                team_delta_gold[k] = team_delta_gold.get(k, 0) + v

        team_gold_tags = "".join([
            f'<span class="delta-tag">{k}: <b class="{"pos" if v>=0 else "neg"}">{"+" if v>=0 else ""}{v:,}</b></span>'
            for k, v in team_delta_gold.items()
        ]) if team_delta_gold else ""

        delta_gold_section = f"""
        <div class="delta-box" style="margin-top:6px;">
            <div class="delta-title"><img class="mini-icon" src="{icon_gold}"/> {get_text("gold_delta_title", lang=lang)}</div>
            <div class="delta-flex">{team_gold_tags}</div>
        </div>
        """ if team_gold_tags else ""

        t1_phys = sum(p.get("damage_physical", 0) for p in t1_players)
        t1_mag = sum(p.get("damage_magic", 0) for p in t1_players)
        t1_tru = sum(p.get("damage_true", 0) for p in t1_players)
        t1_mit = sum(p.get("damage_mitigated", 0) for p in t1_players)
        t1_hl = sum(p.get("total_heal", 0) for p in t1_players)
        t1_vis = sum(p.get("vision_score", 0) for p in t1_players)
        t1_pinks = sum(p.get("detector_wards", 0) for p in t1_players)
        t1_camps = sum(p.get("enemy_jungle_monsters", 0) for p in t1_players)

        t2_phys = sum(p.get("damage_physical", 0) for p in t2_players)
        t2_mag = sum(p.get("damage_magic", 0) for p in t2_players)
        t2_tru = sum(p.get("damage_true", 0) for p in t2_players)
        t2_mit = sum(p.get("damage_mitigated", 0) for p in t2_players)
        t2_hl = sum(p.get("total_heal", 0) for p in t2_players)
        t2_vis = sum(p.get("vision_score", 0) for p in t2_players)
        t2_pinks = sum(p.get("detector_wards", 0) for p in t2_players)
        t2_camps = sum(p.get("enemy_jungle_monsters", 0) for p in t2_players)

        lbl_dmg = get_text("dmg_dealt", lang=lang)
        lbl_phys = get_text("dmg_physical", lang=lang)
        lbl_mag = get_text("dmg_magic", lang=lang)
        lbl_true = get_text("dmg_true", lang=lang)
        lbl_soaked = get_text("dmg_soaked", lang=lang)
        lbl_taken = get_text("damage_taken", lang=lang)
        lbl_mit = get_text("mitigated", lang=lang)
        lbl_hl = get_text("healed", lang=lang)

        # Pills Blue Team 5v5
        t1_pink_badge = f"<span style='display:inline-flex; align-items:center; gap:2px;'><img class='mini-icon mini-icon-round' src='{icon_pink}' title='Control Wards'/> <b>{t1_pinks}</b></span>"
        t1_vis_combined = f"{get_text('vision_score', lang=lang)}: <b>{t1_vis}</b> ({t1_pink_badge})"

        t2_pink_badge = f"<span style='display:inline-flex; align-items:center; gap:2px;'><img class='mini-icon mini-icon-round' src='{icon_pink}' title='Control Wards'/> <b>{t2_pinks}</b></span>"
        t2_vis_combined = f"{get_text('vision_score', lang=lang)}: <b>{t2_vis}</b> ({t2_pink_badge})"

        duels_html.append(f"""
        <div class="duel-row team-combined-row">
            <div class="player-card border-blue">
                <div class="p-header">
                    <div class="team-avatar-stack">{t1_icons_html}</div>
                    <div class="p-meta">
                        <div class="p-name">{get_text("blue_team", lang=lang)}</div>
                        <div class="p-champ">{get_text("team_combined_sub", lang=lang)}</div>
                    </div>
                </div>
                <div class="p-kda">{get_text("blue_team", lang=lang)} - KDA: <b>{t1_kills}/{t1_deaths}/{t1_assists}</b> <span class="kda-ratio">({ratio_t1:.2f}:1)</span></div>
                <div class="stats-pills">
                    <div class="pill pill-wide" title="{lbl_phys}: {t1_phys:,} | {lbl_mag}: {t1_mag:,} | {lbl_true}: {t1_tru:,}">
                        <span>{lbl_dmg}: <b>{t1_dmg:,}</b></span>
                        <span class="dmg-breakdown-sub"><span style="color:#475569;">|</span> {lbl_phys}: <b class="dmg-phys">{t1_phys:,}</b> <span style="color:#475569;">|</span> {lbl_mag}: <b class="dmg-mag">{t1_mag:,}</b> <span style="color:#475569;">|</span> {lbl_true}: <b class="dmg-true">{t1_tru:,}</b></span>
                    </div>
                    <div class="pill pill-wide" title="{lbl_taken}: {t1_taken:,} | {lbl_mit}: {t1_mit:,} | {lbl_hl}: {t1_hl:,}">
                        <span>{lbl_soaked}: <b>{t1_taken + t1_mit:,}</b></span>
                        <span class="dmg-breakdown-sub"><span style="color:#475569;">|</span> {lbl_taken}: <b class="dmg-tk">{t1_taken:,}</b> <span style="color:#475569;">|</span> {lbl_mit}: <b class="dmg-mit">{t1_mit:,}</b> <span style="color:#475569;">|</span> {lbl_hl}: <b class="dmg-hl">{t1_hl:,}</b></span>
                    </div>
                    <div class="pill pill-wide">
                        <span><img class="mini-icon" src="{icon_gold}"/> <b>{t1_gold:,}</b> <span style="color:var(--text-muted); font-size:0.75rem;">(dmg/g: <b>{round(t1_dmg / max(t1_gold, 1), 2)}</b>)</span></span>
                        <span><img class="mini-icon" src="{icon_cs}"/> <b>{t1_cs}</b> <span style='color:var(--text-muted); font-size:0.78rem;'>({csm_t1}/m)</span></span>
                    </div>
                    <div class="pill pill-wide">
                        <span>{t1_vis_combined}</span>
                        <span>🌲 {get_text('camps_stolen', lang=lang)}: <b>{t1_camps}</b></span>
                    </div>
                </div>
            </div>

            <div class="duel-center">
                <div class="role-badge-lg" style="background:#3730a3; color:#c7d2fe;">{get_text("team_combined_title", lang=lang)}</div>
                <div class="lane-bar-wrapper">
                    <div class="lane-bar-container" title="Distribuição de Ouro da Equipe (15000 delta = barra cheia)">
                        <div class="lane-bar-blue" style="width: {calculate_gold_bar_share(t1_gold - t2_gold, max_delta=15000.0):.1f}%;"></div>
                        <div class="lane-bar-red" style="width: {100.0 - calculate_gold_bar_share(t1_gold - t2_gold, max_delta=15000.0):.1f}%;"></div>
                    </div>
                </div>
                <div style="font-size:0.8rem; color:#cbd5e1; font-weight:700;">
                    {get_text("gold", lang=lang)}: <b class="{'pos' if t1_gold >= t2_gold else 'neg'}">{'+' if t1_gold >= t2_gold else ''}{t1_gold - t2_gold:,}</b>
                </div>
                {delta_gold_section}
            </div>

            <div class="player-card border-red">
                <div class="p-header" style="justify-content: flex-end;">
                    <div class="p-meta" style="text-align: right;">
                        <div class="p-name">{get_text("red_team", lang=lang)}</div>
                        <div class="p-champ">{get_text("team_combined_sub", lang=lang)}</div>
                    </div>
                    <div class="team-avatar-stack">{t2_icons_html}</div>
                </div>
                <div class="p-kda" style="justify-content: flex-end;">{get_text("red_team", lang=lang)} - KDA: <b>{t2_kills}/{t2_deaths}/{t2_assists}</b> <span class="kda-ratio">({ratio_t2:.2f}:1)</span></div>
                <div class="stats-pills">
                    <div class="pill pill-wide" title="{lbl_phys}: {t2_phys:,} | {lbl_mag}: {t2_mag:,} | {lbl_true}: {t2_tru:,}">
                        <span>{lbl_dmg}: <b>{t2_dmg:,}</b></span>
                        <span class="dmg-breakdown-sub"><span style="color:#475569;">|</span> {lbl_phys}: <b class="dmg-phys">{t2_phys:,}</b> <span style="color:#475569;">|</span> {lbl_mag}: <b class="dmg-mag">{t2_mag:,}</b> <span style="color:#475569;">|</span> {lbl_true}: <b class="dmg-true">{t2_tru:,}</b></span>
                    </div>
                    <div class="pill pill-wide" title="{lbl_taken}: {t2_taken:,} | {lbl_mit}: {t2_mit:,} | {lbl_hl}: {t2_hl:,}">
                        <span>{lbl_soaked}: <b>{t2_taken + t2_mit:,}</b></span>
                        <span class="dmg-breakdown-sub"><span style="color:#475569;">|</span> {lbl_taken}: <b class="dmg-tk">{t2_taken:,}</b> <span style="color:#475569;">|</span> {lbl_mit}: <b class="dmg-mit">{t2_mit:,}</b> <span style="color:#475569;">|</span> {lbl_hl}: <b class="dmg-hl">{t2_hl:,}</b></span>
                    </div>
                    <div class="pill pill-wide">
                        <span><img class="mini-icon" src="{icon_gold}"/> <b>{t2_gold:,}</b> <span style="color:var(--text-muted); font-size:0.75rem;">(dmg/g: <b>{round(t2_dmg / max(t2_gold, 1), 2)}</b>)</span></span>
                        <span><img class="mini-icon" src="{icon_cs}"/> <b>{t2_cs}</b> <span style='color:var(--text-muted); font-size:0.78rem;'>({csm_t2}/m)</span></span>
                    </div>
                    <div class="pill pill-wide">
                        <span>{t2_vis_combined}</span>
                        <span>🌲 {get_text('camps_stolen', lang=lang)}: <b>{t2_camps}</b></span>
                    </div>
                </div>
            </div>
        </div>
        """)

    all_duels_rendered = "".join(duels_html)

    # PÓDIOS DA PARTIDA (MATCH AWARDS - 6 PÓDIOS EM GRID 3x2)
    all_players = t1_players + t2_players
    rank_classes = ["rank-gold", "rank-silver", "rank-bronze"]

    # 1. Jungle (Smite Master / Neutral Objectives)
    jungle_obj_counts = {}
    objs_source = data.get("all_objectives", [])
    if not objs_source:
        objs_source = [
            {"killer_champ": ev.get("killer_champ"), "killer_name": ev.get("killer_name")}
            for ev in data.get("key_events", []) if ev.get("type") == "objective"
        ]

    for ev in objs_source:
        k_champ = ev.get("killer_champ", "")
        k_name = ev.get("killer_name", "")
        if k_champ:
            key = (k_name, k_champ)
            jungle_obj_counts[key] = jungle_obj_counts.get(key, 0) + 1

    top_jungle_sorted = sorted(jungle_obj_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    jungle_items_list = []
    for idx, ((k_name, k_champ), count) in enumerate(top_jungle_sorted):
        found_p = next((p for p in all_players if p.get("champion") == k_champ), None)
        icon_src = found_p.get("champion_icon", "") if found_p else ""
        jungle_items_list.append(f"""
        <div class="award-item {rank_classes[idx]}">
            <div class="award-champ-info">
                <img class="award-avatar" src="{icon_src}" alt="{k_champ}"/>
                <span class="award-name">{k_name} ({k_champ})</span>
            </div>
            <span class="award-val">{count} obj{'s' if count > 1 else ''}</span>
        </div>
        """)
    jungle_items = "".join(jungle_items_list) if jungle_items_list else f"<div style='color:var(--text-muted); font-size:0.82rem; font-style:italic;'>{get_text('no_data', lang=lang)}</div>"

    # 2. Mayhem (Damage)
    top_damage = sorted(all_players, key=lambda x: x.get("damage_to_champions", 0), reverse=True)[:3]
    mayhem_items = "".join([
        f"""
        <div class="award-item {rank_classes[idx]}">
            <div class="award-champ-info">
                <img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/>
                <span class="award-name">{p['riot_id']} ({p['champion']})</span>
            </div>
            <span class="award-val">{p.get('damage_to_champions', 0):,} DMG</span>
        </div>
        """ for idx, p in enumerate(top_damage)
    ])

    # 3. Greed (Gold)
    top_gold = sorted(all_players, key=lambda x: x.get("gold_total", 0), reverse=True)[:3]
    greed_items = "".join([
        f"""
        <div class="award-item {rank_classes[idx]}">
            <div class="award-champ-info">
                <img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/>
                <span class="award-name">{p['riot_id']} ({p['champion']})</span>
            </div>
            <span class="award-val">{p.get('gold_total', 0):,} <img class="mini-icon" src="{icon_gold}"/></span>
        </div>
        """ for idx, p in enumerate(top_gold)
    ])

    # 4. Might (Damage Taken + Mitigated)
    top_might = sorted(all_players, key=lambda x: x.get("damage_taken", 0) + x.get("damage_mitigated", 0), reverse=True)[:3]
    might_items = "".join([
        f"""
        <div class="award-item {rank_classes[idx]}">
            <div class="award-champ-info">
                <img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/>
                <span class="award-name">{p['riot_id']} ({p['champion']})</span>
            </div>
            <span class="award-val">{(p.get('damage_taken', 0) + p.get('damage_mitigated', 0)):,}</span>
        </div>
        """ for idx, p in enumerate(top_might)
    ])

    # 5. Visionary (Vision Score)
    top_vision = sorted(all_players, key=lambda x: x.get("vision_score", 0), reverse=True)[:3]
    visionary_items = "".join([
        f"""
        <div class="award-item {rank_classes[idx]}">
            <div class="award-champ-info">
                <img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/>
                <span class="award-name">{p['riot_id']} ({p['champion']})</span>
            </div>
            <span class="award-val">{p.get('vision_score', 0)} score ({p.get('detector_wards', 0)} <img class='mini-icon mini-icon-round' src='https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/2055.png' title='Control Wards'/>)</span>
        </div>
        """ for idx, p in enumerate(top_vision)
    ])

    # 6. Demolisher (Turret Damage)
    top_turret = sorted(all_players, key=lambda x: x.get("damage_to_turrets", 0), reverse=True)[:3]
    demolisher_items = "".join([
        f"""
        <div class="award-item {rank_classes[idx]}">
            <div class="award-champ-info">
                <img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/>
                <span class="award-name">{p['riot_id']} ({p['champion']})</span>
            </div>
            <span class="award-val">{p.get('damage_to_turrets', 0):,} DMG</span>
        </div>
        """ for idx, p in enumerate(top_turret)
    ])

    awards_html = f"""
    <div class="card">
        <h3>{get_text('match_awards_title', lang=lang)}</h3>
        <div class="awards-grid">
            <div class="award-card">
                <div>
                    <div class="award-header">{get_text('award_jungle_title', lang=lang)}</div>
                    <div class="award-desc">{get_text('award_jungle_desc', lang=lang)}</div>
                </div>
                <div class="award-list">{jungle_items}</div>
            </div>
            <div class="award-card">
                <div>
                    <div class="award-header">{get_text('award_mayhem_title', lang=lang)}</div>
                    <div class="award-desc">{get_text('award_mayhem_desc', lang=lang)}</div>
                </div>
                <div class="award-list">{mayhem_items}</div>
            </div>
            <div class="award-card">
                <div>
                    <div class="award-header">{get_text('award_greed_title', lang=lang)}</div>
                    <div class="award-desc">{get_text('award_greed_desc', lang=lang)}</div>
                </div>
                <div class="award-list">{greed_items}</div>
            </div>
            <div class="award-card">
                <div>
                    <div class="award-header">{get_text('award_might_title', lang=lang)}</div>
                    <div class="award-desc">{get_text('award_might_desc', lang=lang)}</div>
                </div>
                <div class="award-list">{might_items}</div>
            </div>
            <div class="award-card">
                <div>
                    <div class="award-header">{get_text('award_visionary_title', lang=lang)}</div>
                    <div class="award-desc">{get_text('award_visionary_desc', lang=lang)}</div>
                </div>
                <div class="award-list">{visionary_items}</div>
            </div>
            <div class="award-card">
                <div>
                    <div class="award-header">{get_text('award_demolisher_title', lang=lang)}</div>
                    <div class="award-desc">{get_text('award_demolisher_desc', lang=lang)}</div>
                </div>
                <div class="award-list">{demolisher_items}</div>
            </div>
        </div>
    </div>
    """

    # Linha do tempo
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
            from .event_engine import clean_monster_name
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
            elif streak == "multi":
                streak_class = "event-multi"
                streak_badge = '<span class="multi-badge badge-multi">MULTI KILL! ⚔️</span>'

            elim_txt = get_text("eliminated", lang=lang)
            c_ast = ev.get('assists_count', 0)
            ast_label = get_text("assists_plural", lang=lang) if c_ast > 1 else get_text("assists", lang=lang)
            assists_txt = f" (+{c_ast} {ast_label})" if c_ast > 0 else f" <span class='tag-solokill'>{get_text('solo_tag', lang=lang)}</span>"

            extra_class = "timeline-hidden" if idx >= 20 else ""
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
    if remaining_events > 0:
        btn_text = get_text("show_more_events", lang=lang, count=remaining_events)
        timeline_toggle_btn = f"""
        <div style="text-align:center; margin-top:14px;">
            <button id="toggleTimelineBtn" class="btn" style="background:#1e293b; border:1px solid var(--card-border); color:#38bdf8; font-weight:700; font-size:0.85rem; padding:8px 18px; border-radius:8px; cursor:pointer;" onclick="toggleTimeline()">{btn_text}</button>
        </div>
        """

    events_html = "".join(events_list_items)

    def clean_mode_name(mode_str: str) -> str:
        m = str(mode_str).upper()
        if m == "CLASSIC":
            return "Summoner's Rift"
        elif m == "ARAM":
            return "ARAM"
        elif m == "CHERRY":
            return "Arena"
        elif m == "URF":
            return "URF"
        return m.capitalize()

    match_mode = clean_mode_name(data.get('game_mode', 'CLASSIC'))

    # Queue name lookup
    queue_map = {
        420: "queue_ranked_solo",
        440: "queue_ranked_flex",
        400: "queue_normal_draft",
        430: "queue_normal_blind",
        450: "queue_aram",
        1700: "queue_arena",
        900: "queue_urf",
        1010: "queue_urf",
        1900: "queue_urf"
    }
    q_key = queue_map.get(data.get("queue_id", 0), "")
    queue_name = get_text(q_key, lang=lang) if q_key else ""
    full_mode_display = f"{match_mode} ({queue_name})" if queue_name else match_mode
    # Identificar jogador alvo (Host) para Favicon e Título da Aba
    all_players = t1_players + t2_players
    target_player = None
    if target_puuid:
        for p in all_players:
            if p.get("puuid") == target_puuid:
                target_player = p
                break
    if not target_player and all_players:
        target_player = all_players[0]

    favicon_url = target_player.get("champion_icon", "") if target_player else ""
    target_nick = target_player.get("riot_id", "") if target_player else ""
    target_kda = target_player.get("kda", "") if target_player else ""
    match_id_str = data.get('match_id', '')

    tab_title_parts = []
    if target_nick:
        tab_title_parts.append(target_nick)
    if target_kda:
        tab_title_parts.append(f"({target_kda})")
    if match_mode:
        tab_title_parts.append(match_mode)
    tab_title_parts.append(f"LoL Head-to-Head Duel Analytics ({match_id_str})")
    browser_tab_title = " • ".join(tab_title_parts)

    favicon_link = f'<link rel="icon" type="image/png" href="{favicon_url}"/>' if favicon_url else ''

    header_avatar_html = f'<img src="{favicon_url}" alt="{target_nick}" style="width: 52px; height: 52px; border-radius: 50%; border: 2px solid var(--accent); box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);"/>' if favicon_url else ''

    html_content = f"""<!DOCTYPE html>
<html lang="{ 'pt-BR' if lang == 'pt_BR' else 'en' }">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{browser_tab_title}</title>
    {favicon_link}
    <style>
        :root {{
            --bg-color: #080c14;
            --card-bg: #111827;
            --card-border: #1f293d;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --accent: #38bdf8;
            --blue-team: #2563eb;
            --red-team: #dc2626;
            --green: #22c55e;
            --red: #ef4444;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 24px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 1340px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--card-border);
            padding: 18px 24px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .team-titles {{
            display: flex;
            justify-content: space-between;
            padding: 10px 16px;
            font-weight: 800;
            font-size: 1.1rem;
            letter-spacing: 0.5px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 18px;
        }}
        .duel-row {{
            display: grid;
            grid-template-columns: 1fr 370px 1fr;
            gap: 16px;
            align-items: center;
            background: #0d1322;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 14px;
        }}
        .bot-duo-row {{
            background: linear-gradient(180deg, #131c31 0%, #0d1322 100%);
            border: 1px solid #2a3a5e;
            margin-top: 22px;
        }}
        @media (max-width: 1100px) {{
            .duel-row {{ grid-template-columns: 1fr; }}
        }}
        .player-card {{
            background: #151d30;
            padding: 14px;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            border-top: 3px solid transparent;
        }}
        .border-blue {{ border-color: var(--blue-team); }}
        .border-red {{ border-color: var(--red-team); }}
        .is-target {{
            background: rgba(56, 189, 248, 0.12);
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
            border: 1px solid var(--accent);
            border-top: 3px solid var(--accent);
        }}
        .p-header {{ display: flex; align-items: center; gap: 12px; }}
        .champ-icon {{
            width: 44px;
            height: 44px;
            border-radius: 50%;
            border: 2px solid var(--card-border);
        }}
        .duo-avatar-stack {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .p-meta {{ display: flex; flex-direction: column; }}
        .p-name {{ font-weight: 700; color: #fff; font-size: 0.95rem; }}
        .p-champ {{ font-size: 0.8rem; color: var(--text-muted); }}
        .target-tag {{
            background: var(--accent);
            color: #0f172a;
            font-size: 0.65rem;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 6px;
        }}
        .p-kda {{ font-size: 0.88rem; color: #e2e8f0; display: flex; align-items: center; gap: 6px; }}
        .kda-ratio {{ color: var(--text-muted); font-weight: 600; font-size: 0.80rem; }}
        .lead-delta {{
            color: #4ade80;
            font-size: 0.75rem;
            font-weight: 800;
            background: rgba(74, 222, 128, 0.12);
            padding: 1px 5px;
            border-radius: 3px;
            margin-left: 4px;
        }}
        .stats-pills {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            font-size: 0.8rem;
        }}
        .pill {{
            background: #0a0e1a;
            padding: 5px 8px;
            border-radius: 4px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .pill b {{ color: #f3f4f6; }}
        .pill-wide {{
            grid-column: 1 / -1;
            justify-content: space-between;
            font-size: 0.78rem;
        }}
        .dmg-breakdown-sub {{
            font-size: 0.72rem;
            color: #64748b;
        }}
        .dmg-phys {{ color: #f87171 !important; }}
        .dmg-mag {{ color: #60a5fa !important; }}
        .dmg-true {{ color: #f8fafc !important; }}
        .dmg-tk {{ color: #ef4444 !important; }}
        .dmg-mit {{ color: #f1f5f9 !important; }}
        .dmg-hl {{ color: #4ade80 !important; }}
        .timeline-hidden {{
            display: none !important;
        }}
        .mini-icon {{ width: 14px; height: 14px; vertical-align: middle; }}
        .items-flex {{ display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }}
        .item-icon {{
            width: 26px;
            height: 26px;
            border-radius: 4px;
            border: 1px solid #334155;
            background: #0f172a;
        }}
        .spells-runes-strip {{
            display: flex;
            align-items: center;
            gap: 5px;
            background: #0a0e1a;
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid var(--card-border);
        }}
        .spells-row {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .spell-icon {{
            width: 26px;
            height: 26px;
            border-radius: 4px;
            border: 1px solid #334155;
        }}
        .rune-icon {{
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: #0f172a;
            border: 1px solid #334155;
            padding: 1px;
        }}
        .team-combined-row {{
            background: linear-gradient(180deg, #1e1b4b 0%, #0d1322 100%);
            border: 2px solid #3730a3;
            margin-top: 18px;
        }}
        .team-avatar-stack {{
            display: flex;
            align-items: center;
            gap: -6px;
        }}
        .team-champ-mini {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 1px solid #334155;
            margin-right: -6px;
        }}
        .awards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 14px;
            margin-top: 14px;
        }}
        .award-card {{
            background: #0d1322;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .award-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 800;
            font-size: 1rem;
            color: #f59e0b;
            margin-bottom: 6px;
        }}
        .award-desc {{
            font-size: 0.75rem;
            color: var(--text-muted);
            border-bottom: 1px solid #1e293b;
            padding-bottom: 8px;
            line-height: 1.4;
        }}
        .award-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .award-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #151d30;
            padding: 7px 12px;
            border-radius: 6px;
            border-left: 3px solid transparent;
            gap: 8px;
            transition: all 0.2s ease;
        }}
        .rank-gold {{
            border-left-color: #fbbf24;
            background: linear-gradient(90deg, rgba(251, 191, 36, 0.15) 0%, rgba(21, 29, 48, 0.9) 100%);
            padding: 9px 14px;
            border-left-width: 4px;
            box-shadow: 0 0 10px rgba(251, 191, 36, 0.1);
        }}
        .rank-gold .award-avatar {{
            width: 32px;
            height: 32px;
            border: 2px solid #fbbf24;
        }}
        .rank-gold .award-name {{
            font-size: 0.92rem;
            font-weight: 800;
            color: #fff;
        }}
        .rank-gold .award-val {{
            font-size: 0.95rem;
            font-weight: 800;
            color: #fef08a;
        }}
        
        .rank-silver {{
            border-left-color: #94a3b8;
            background: rgba(148, 163, 184, 0.08);
            padding: 7px 12px;
        }}
        .rank-silver .award-avatar {{
            width: 28px;
            height: 28px;
            border: 1px solid #94a3b8;
        }}
        .rank-silver .award-name {{
            font-size: 0.85rem;
            font-weight: 700;
            color: #e2e8f0;
        }}
        .rank-silver .award-val {{
            font-size: 0.88rem;
            font-weight: 800;
            color: #cbd5e1;
        }}

        .rank-bronze {{
            border-left-color: #d97706;
            background: rgba(217, 119, 6, 0.06);
            padding: 6px 10px;
            opacity: 0.9;
        }}
        .rank-bronze .award-avatar {{
            width: 24px;
            height: 24px;
            border: 1px solid #d97706;
        }}
        .rank-bronze .award-name {{
            font-size: 0.8rem;
            font-weight: 600;
            color: #94a3b8;
        }}
        .rank-bronze .award-val {{
            font-size: 0.82rem;
            font-weight: 700;
            color: #d97706;
        }}

        .award-champ-info {{
            display: flex;
            align-items: center;
            gap: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .award-name {{
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .award-val {{
            white-space: nowrap;
            flex-shrink: 0;
        }}
        
        .jungle-mini-strip {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
            background: #0a0e1a;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px dashed var(--card-border);
            overflow-x: auto;
        }}
        .jungle-badge-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2px;
        }}
        .obj-badge-icon-lg {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 1px solid #38bdf8;
            background: #0f172a;
            transition: all 0.2s ease;
        }}
        .soul-dragon-badge {{
            border-color: #f59e0b !important;
            box-shadow: 0 0 10px rgba(245, 158, 11, 0.7) !important;
            transform: scale(1.1);
        }}
        .mini-icon-round {{
            border-radius: 50% !important;
            border: 1px solid #334155;
        }}
        .badge-time {{
            font-size: 0.65rem;
            color: var(--text-muted);
            font-weight: 600;
        }}
        .empty-jungle-slot {{
            font-size: 0.8rem;
            color: var(--text-muted);
            font-style: italic;
        }}

        .duel-center {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 6px;
            position: relative;
        }}
        .role-badge-lg {{
            background: #1e293b;
            color: var(--accent);
            font-weight: 800;
            font-size: 0.8rem;
            padding: 4px 12px;
            border-radius: 20px;
            letter-spacing: 0.5px;
        }}
        
        .lane-bar-wrapper {{
            position: relative;
            width: 100%;
            margin: 4px 0;
        }}
        .lane-bar-container {{
            width: 100%;
            height: 9px;
            background: #1e293b;
            border-radius: 4px;
            display: flex;
            overflow: hidden;
            border: 1px solid var(--card-border);
        }}
        .lane-bar-blue {{
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
            transition: width 0.3s ease;
        }}
        .lane-bar-red {{
            background: linear-gradient(90deg, #f87171, #ef4444);
            transition: width 0.3s ease;
        }}
        .gap-seal {{
            position: absolute;
            top: -16px;
            font-size: 0.68rem;
            font-weight: 900;
            letter-spacing: 0.5px;
            padding: 1px 6px;
            border-radius: 4px;
            animation: pulse 1.5s infinite;
        }}
        .gap-left {{ left: 0; background: #2563eb; color: #fff; }}
        .gap-right {{ right: 0; background: #dc2626; color: #fff; }}
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.08); }}
        }}

        /* Placar Unificado com Solo Kills Grande e Mortes p/ Ganks */
        .duel-scores-wrapper {{
            background: #151d30;
            padding: 6px 12px;
            border-radius: 6px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        .duel-score-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .score-label {{ color: var(--text-muted); font-size: 0.76rem; font-weight: 600; }}
        
        .score-pill-lg {{
            background: #090d16;
            padding: 2px 10px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .score-blue-lg {{ color: #60a5fa; font-size: 1.05rem; font-weight: 800; }}
        .score-red-lg {{ color: #f87171; font-size: 1.05rem; font-weight: 800; }}
        .score-x-lg {{ color: #64748b; font-size: 0.8rem; font-weight: 700; }}

        .score-pill-sm {{
            background: #090d16;
            padding: 1px 8px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .score-blue-sm {{ color: #60a5fa; font-size: 0.82rem; font-weight: 700; }}
        .score-red-sm {{ color: #f87171; font-size: 0.82rem; font-weight: 700; }}
        .score-x-sm {{ color: #64748b; font-size: 0.7rem; }}

        .delta-box {{
            background: #151d30;
            padding: 8px 10px;
            border-radius: 6px;
            width: 100%;
            font-size: 0.76rem;
        }}
        .delta-title {{ color: var(--text-muted); margin-bottom: 4px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 4px; }}
        .delta-flex {{
            display: flex;
            flex-wrap: nowrap;
            justify-content: space-between;
            gap: 4px;
            overflow-x: auto;
        }}
        .delta-tag {{
            background: #080c14;
            padding: 3px 6px;
            border-radius: 4px;
            white-space: nowrap;
            font-size: 0.72rem;
            flex: 1;
            text-align: center;
        }}
        .pos {{ color: var(--green); }}
        .neg {{ color: var(--red); }}
        .badge {{ padding: 4px 10px; border-radius: 14px; font-size: 0.8rem; font-weight: 700; }}
        .win-badge {{ background: #166534; color: #86efac; }}
        .loss-badge {{ background: #991b1b; color: #fca5a5; }}
        .align-left {{ text-align: left; }}
        .align-right {{ text-align: left; }}

        .events-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .event-item {{
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 0.88rem;
            display: flex;
            align-items: center;
            gap: 12px;
            border-left: 3px solid transparent;
        }}
        .event-time {{
            font-family: Consolas, Monaco, monospace;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--accent);
            background: #090d16;
            padding: 3px 6px;
            border-radius: 4px;
            flex-shrink: 0;
        }}
        .event-avatar {{
            width: 26px;
            height: 26px;
            border-radius: 50%;
            border: 1px solid var(--card-border);
            vertical-align: middle;
            flex-shrink: 0;
        }}
        .event-kill-duel {{
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
        }}
        .event-arrow {{ font-size: 0.75rem; }}
        .event-desc {{ flex-grow: 1; }}
        .tag-solokill {{
            background: #eab308;
            color: #0f172a;
            font-weight: 800;
            font-size: 0.65rem;
            padding: 1px 5px;
            border-radius: 3px;
            margin-left: 4px;
        }}
        .event-kill {{
            background: #0d1322;
            border-left-color: #3b82f6;
        }}
        .event-obj {{
            background: #141b2b;
            border-left-color: #eab308;
        }}
        .event-multi {{
            background: linear-gradient(90deg, rgba(234, 179, 8, 0.15) 0%, #0d1322 100%);
            border-left-color: #eab308;
            border: 1px solid rgba(234, 179, 8, 0.3);
        }}
        .event-penta {{
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.25) 0%, #0d1322 100%);
            border-left-color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.5);
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.2);
        }}
        .multi-badge {{
            font-size: 0.72rem;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}
        .badge-multi {{ background: #eab308; color: #000; }}
        .badge-penta {{ background: #ef4444; color: #fff; }}

        .raw-summary-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .copy-btn {{
            background: #2563eb;
            color: #fff;
            border: none;
            padding: 8px 14px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .copy-btn:hover {{ background: #1d4ed8; }}
        .raw-textarea {{
            width: 100%;
            background: #090d16;
            color: #cbd5e1;
            font-family: Consolas, Monaco, "Courier New", monospace;
            font-size: 0.82rem;
            line-height: 1.45;
            padding: 14px;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            resize: none;
            overflow: hidden;
            white-space: pre-wrap;
            box-sizing: border-box;
            display: block;
        }}
        .lang-picker {{
            position: fixed;
            top: 16px;
            right: 20px;
            display: flex;
            gap: 4px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            padding: 4px 6px;
            border-radius: 20px;
            border: 1px solid var(--card-border);
            z-index: 999;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        }}
        .lang-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 0.82rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 14px;
            cursor: pointer;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }}
        .lang-btn:hover {{
            color: #fff;
        }}
        .lang-btn.active {{
            background: #2563eb;
            color: #fff;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
        }}
        .flag-icon {{
            width: 16px;
            height: 12px;
            border-radius: 2px;
            display: inline-block;
            vertical-align: middle;
        }}
        .legal-footer {{
            text-align: center;
            color: #475569;
            font-size: 0.75rem;
            line-height: 1.5;
            padding: 20px 0 10px 0;
            border-top: 1px solid #1e293b;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="lang-picker">
        <a href="/analyze?match_id={data.get('match_id')}&puuid={target_puuid}&lang=en_US" class="{'lang-btn active' if lang=='en_US' else 'lang-btn'}" title="English (US)">
            <img class="flag-icon" src="https://flagcdn.com/w40/us.png" alt="US Flag"/> EN
        </a>
        <a href="/analyze?match_id={data.get('match_id')}&puuid={target_puuid}&lang=pt_BR" class="{'lang-btn active' if lang=='pt_BR' else 'lang-btn'}" title="Português (Brasil)">
            <img class="flag-icon" src="https://flagcdn.com/w40/br.png" alt="BR Flag"/> PT
        </a>
    </div>

    <div class="container">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 2px;">
            <a href="/?lang={lang}" style="color:#38bdf8; text-decoration:none; font-weight:700; font-size:0.9rem; background:#111827; padding:8px 14px; border-radius:8px; border:1px solid var(--card-border); transition:background 0.2s;" onmouseover="this.style.background='#1f293d'" onmouseout="this.style.background='#111827'">{get_text('back_to_hub', lang=lang)}</a>
            <span style="color:#94a3b8; font-weight:800; font-size:1.05rem; letter-spacing:0.5px;">🔥 <span style="background:linear-gradient(90deg, #fb923c, #f97316, #ef4444); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Blaze GG</span></span>
        </div>

        <div class="header" style="display:flex; align-items:center; gap:16px;">
            {header_avatar_html}
            <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <h1 style="margin:0; font-size: 1.45rem; font-weight:800; color:#fff;">{target_nick}</h1>
                    <span style="background:#1e293b; color:var(--accent); font-weight:800; font-size:0.9rem; padding:3px 10px; border-radius:6px; border:1px solid #334155;">KDA: {target_kda}</span>
                </div>
                <div style="color: var(--text-muted); margin-top: 5px; font-size:0.88rem;">
                    <span style="color:#94a3b8; font-family:monospace;">{data.get('match_id')}</span> • <b>{full_mode_display}</b> • {get_text('duration', lang=lang)}: <b>{data.get('duration')}</b>
                </div>
            </div>
        </div>

        <div class="team-titles">
            <div style="color: #60a5fa;">{get_text('blue_team', lang=lang)} {t100_status}</div>
            <div style="color: #f87171;">{get_text('red_team', lang=lang)} {t200_status}</div>
        </div>

        <!-- CONFRONTOS LADO A LADO -->
        <div>
            {all_duels_rendered}
        </div>

        <!-- Pódios da Partida -->
        {awards_html}

        <!-- Momentos Chave -->
        <div class="card">
            <h3>{get_text('timeline_title', lang=lang)}</h3>
            <ul class="events-list">
                {events_html}
            </ul>
            {timeline_toggle_btn}
        </div>

        <!-- Resumo Bruto / LLM Prompt Box -->
        <div class="card">
            <div class="raw-summary-header">
                <h3 style="margin:0;">{get_text('raw_summary_title', lang=lang)}</h3>
                <button class="copy-btn" onclick="copyRawSummary()">{get_text('copy_summary_btn', lang=lang)}</button>
            </div>
            <textarea id="rawSummaryText" class="raw-textarea" readonly>{raw_summary}</textarea>
        </div>

        <div class="legal-footer">
            Blaze.gg isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
        </div>
    </div>

    <script>
        var timelineExpanded = false;
        function toggleTimeline() {{
            var hiddenItems = document.querySelectorAll(".events-list .timeline-hidden, .events-list .timeline-visible-expanded");
            var btn = document.getElementById("toggleTimelineBtn");
            if (!timelineExpanded) {{
                hiddenItems.forEach(function(el) {{
                    el.classList.remove("timeline-hidden");
                    el.classList.add("timeline-visible-expanded");
                }});
                timelineExpanded = true;
                if (btn) btn.innerText = "{get_text('show_less_events', lang=lang)}";
            }} else {{
                hiddenItems.forEach(function(el) {{
                    el.classList.add("timeline-hidden");
                    el.classList.remove("timeline-visible-expanded");
                }});
                timelineExpanded = false;
                if (btn) btn.innerText = "{get_text('show_more_events', lang=lang, count=remaining_events)}";
            }}
        }}

        function autoResizeTextarea() {{
            var ta = document.getElementById("rawSummaryText");
            if (ta) {{
                ta.style.height = "auto";
                ta.style.height = (ta.scrollHeight + 10) + "px";
            }}
        }}
        window.addEventListener("load", autoResizeTextarea);

        function copyRawSummary() {{
            var copyText = document.getElementById("rawSummaryText");
            copyText.select();
            copyText.setSelectionRange(0, 99999);
            navigator.clipboard.writeText(copyText.value);
            
            var btn = document.querySelector(".copy-btn");
            btn.innerText = "Copiado! ✓";
            btn.style.background = "#16a34a";
            setTimeout(function() {{
                btn.innerText = "Copiar Resumo";
                btn.style.background = "#2563eb";
            }}, 2000);
        }}
    </script>
</body>
</html>
"""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    if open_browser:
        webbrowser.open(REPORT_FILE.as_uri())

    return REPORT_FILE
