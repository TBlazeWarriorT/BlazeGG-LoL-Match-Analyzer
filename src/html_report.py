import webbrowser
from pathlib import Path
from typing import Dict, Any, List
from .config import CACHE_DIR
from .asset_cache import AssetManager

REPORT_FILE = CACHE_DIR / "last_report.html"

def calculate_gold_bar_share(delta: int) -> float:
    fraction = delta / 5000.0
    val = 50.0 + (fraction * 50.0)
    return max(4.0, min(96.0, val))

def generate_html_report(data: Dict[str, Any], open_browser: bool = True) -> Path:
    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    matchups = data.get("matchups", [])
    jungle = data.get("jungle_stats", {})
    target_puuid = data.get("target_puuid", "")
    raw_summary = data.get("raw_summary_text", "")

    icon_gold = AssetManager.get_asset_uri("gold_icon")
    icon_xp = AssetManager.get_asset_uri("xp_icon")
    icon_cs = AssetManager.get_asset_uri("cs_icon")

    t100_win = team_100.get("win", False)
    t200_win = team_200.get("win", False)
    t100_status = '<span class="badge win-badge">VITÓRIA</span>' if t100_win else '<span class="badge loss-badge">DERROTA</span>'
    t200_status = '<span class="badge win-badge">VITÓRIA</span>' if t200_win else '<span class="badge loss-badge">DERROTA</span>'

    j100 = jungle.get(100, {})
    j200 = jungle.get(200, {})

    def render_jungle_chronological(seq):
        if not seq:
            return '<div class="empty-jungle-slot">Nenhum objetivo neutro feito</div>'
        return "".join([
            f'<div class="jungle-badge-wrapper" title="[{item["time"]}] {item["name"]}">'
            f'<img class="obj-badge-icon-lg" src="{AssetManager.get_asset_uri(item["asset_key"])}"/>'
            f'<span class="badge-time">{item["time"]}</span>'
            f'</div>'
            for item in seq
        ])

    def render_duel_row(p1, p2, role_title, stats_1=None, stats_2=None, gold_d=None, xp_d=None, is_bot_duo=False, extra_badges_1="", extra_badges_2=""):
        is_t1 = p1.get("puuid") == target_puuid
        is_t2 = p2.get("puuid") == target_puuid

        # Deltas finais (Dano e Ouro)
        dmg_delta = p1.get("damage_to_champions", 0) - p2.get("damage_to_champions", 0)
        gold_delta_final = p1.get("gold_total", 0) - p2.get("gold_total", 0)

        p1_share = calculate_gold_bar_share(gold_delta_final)
        p2_share = 100.0 - p1_share

        gap_badge_left = '<span class="gap-seal gap-left">GAP! 🔥</span>' if gold_delta_final >= 2000 else ""
        gap_badge_right = '<span class="gap-seal gap-right">GAP! 🔥</span>' if gold_delta_final <= -2000 else ""

        def p_card(p, is_target, is_left=True, badges_html="", is_dmg_leader=False, is_gold_leader=False, delta_dmg=0, delta_gold=0):
            align_class = "align-left" if is_left else "align-right"
            border_side = "border-blue" if is_left else "border-red"
            target_badge = '<span class="target-tag">VOCÊ</span>' if is_target else ""
            
            # Badges verdes de delta final
            dmg_delta_tag = f'<span class="lead-delta">+{delta_dmg:,}</span>' if is_dmg_leader and delta_dmg > 0 else ""
            gold_delta_tag = f'<span class="lead-delta">+{delta_gold:,}</span>' if is_gold_leader and delta_gold > 0 else ""

            kda_ratio_tag = f'<span class="kda-ratio">({p.get("kda_ratio", "")})</span>' if p.get("kda_ratio") else ""

            if is_bot_duo:
                return f"""
                <div class="player-card {align_class} {border_side} {'is-target' if is_target else ''}">
                    <div class="p-header">
                        <div class="duo-avatar-stack">
                            <img class="champ-icon duo-icon-1" src="{p['icon1']}" alt="{p['champ1']}"/>
                            <img class="champ-icon duo-icon-2" src="{p['icon2']}" alt="{p['champ2']}"/>
                        </div>
                        <div class="p-meta">
                            <div class="p-name">{p['champ1']} &amp; {p['champ2']}</div>
                            <div class="p-champ">Duo Bot Lane (Combined)</div>
                        </div>
                    </div>
                    <div class="p-kda">KDA: <b>{p['kda']}</b> {kda_ratio_tag} | <img class="mini-icon" src="{icon_cs}"/> <b>{p['cs']}</b></div>
                    <div class="stats-pills">
                        <div class="pill">Dano: <b>{p['damage_to_champions']:,}</b> {dmg_delta_tag}</div>
                        <div class="pill">Dano/Ouro: <b>{p['damage_per_gold']}</b></div>
                        <div class="pill">Tomado: <b>{p['damage_taken']:,}</b></div>
                        <div class="pill"><img class="mini-icon" src="{icon_gold}"/> <b>{p['gold_total']:,}</b> {gold_delta_tag}</div>
                    </div>
                </div>
                """

            items_html = "".join([
                f'<img class="item-icon" src="{it["icon"]}" title="{it["name"]}" alt="{it["name"]}"/>'
                for it in p.get("items", [])
            ])

            obj_strip_html = f'<div class="jungle-mini-strip">{badges_html}</div>' if badges_html else ""

            return f"""
            <div class="player-card {align_class} {border_side} {'is-target' if is_target else ''}">
                <div class="p-header">
                    <img class="champ-icon" src="{p['champion_icon']}" alt="{p['champion']}"/>
                    <div class="p-meta">
                        <div class="p-name">{p['riot_id']} {target_badge}</div>
                        <div class="p-champ">{p['champion']}</div>
                    </div>
                </div>
                <div class="p-kda">KDA: <b>{p['kda']}</b> {kda_ratio_tag} | <img class="mini-icon" src="{icon_cs}"/> <b>{p['cs']}</b></div>
                <div class="stats-pills">
                    <div class="pill">Dano: <b>{p['damage_to_champions']:,}</b> {dmg_delta_tag}</div>
                    <div class="pill">Dano/Ouro: <b>{p['damage_per_gold']}</b></div>
                    <div class="pill">Tomado: <b>{p['damage_taken']:,}</b></div>
                    <div class="pill"><img class="mini-icon" src="{icon_gold}"/> <b>{p['gold_total']:,}</b> {gold_delta_tag}</div>
                </div>
                <div class="items-flex">{items_html}</div>
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

            solo_kills_1 = stats_1.get("solo_kills", 0) if stats_1 else 0
            solo_kills_2 = stats_2.get("solo_kills", 0) if stats_2 else 0

            duel_info_box = ""
            if not is_bot_duo:
                ganks_1 = stats_1.get("other_deaths", 0) if stats_1 else 0
                ganks_2 = stats_2.get("other_deaths", 0) if stats_2 else 0
                duel_info_box = f"""
                <div class="duel-scores-wrapper">
                    <div class="duel-score-row">
                        <span class="score-label">Solo Kills:</span>
                        <div class="score-pill-lg">
                            <b class="score-blue-lg">{solo_kills_1}</b>
                            <span class="score-x-lg">x</span>
                            <b class="score-red-lg">{solo_kills_2}</b>
                        </div>
                    </div>
                    <div class="duel-score-row" style="margin-top: 3px;">
                        <span class="score-label">Mortes p/ Ganks / Outros:</span>
                        <div class="score-pill-sm">
                            <b class="score-blue-sm">{ganks_1}</b>
                            <span class="score-x-sm">x</span>
                            <b class="score-red-sm">{ganks_2}</b>
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
                    <div class="delta-title"><img class="mini-icon" src="{icon_gold}"/> Variação de Ouro (Azul - Vermelho):</div>
                    <div class="delta-flex">{gold_tags}</div>
                    {f'<div class="delta-title" style="margin-top:5px;"><img class="mini-icon" src="{icon_xp}"/> Variação de XP:</div><div class="delta-flex">{xp_tags}</div>' if xp_tags else ''}
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

        duo_p1 = {
            "champ1": p1_bot["champion"], "icon1": p1_bot["champion_icon"],
            "champ2": p1_sup["champion"], "icon2": p1_sup["champion_icon"],
            "kda": f"{d1_kills}/{d1_deaths}/{d1_assists}",
            "kda_ratio": f"{ratio_d1:.2f}:1" if d1_deaths > 0 else "Perfect",
            "cs": d1_cs,
            "damage_to_champions": d1_dmg,
            "damage_per_gold": round(d1_dmg / max(d1_gold, 1), 2),
            "damage_taken": d1_taken,
            "gold_total": d1_gold,
            "puuid": p1_bot["puuid"] if target_puuid in (p1_bot["puuid"], p1_sup["puuid"]) else ""
        }

        duo_p2 = {
            "champ1": p2_bot["champion"], "icon1": p2_bot["champion_icon"],
            "champ2": p2_sup["champion"], "icon2": p2_sup["champion_icon"],
            "kda": f"{d2_kills}/{d2_deaths}/{d2_assists}",
            "kda_ratio": f"{ratio_d2:.2f}:1" if d2_deaths > 0 else "Perfect",
            "cs": d2_cs,
            "damage_to_champions": d2_dmg,
            "damage_per_gold": round(d2_dmg / max(d2_gold, 1), 2),
            "damage_taken": d2_taken,
            "gold_total": d2_gold,
            "puuid": p2_bot["puuid"] if target_puuid in (p2_bot["puuid"], p2_sup["puuid"]) else ""
        }

        duo_delta_gold = {}
        duo_delta_xp = {}
        for k in m_bot["gold_delta"].keys():
            duo_delta_gold[k] = m_bot["gold_delta"].get(k, 0) + m_sup["gold_delta"].get(k, 0)
            duo_delta_xp[k] = m_bot["xp_delta"].get(k, 0) + m_sup["xp_delta"].get(k, 0)

        duels_html.append(render_duel_row(
            duo_p1, duo_p2, "BOT LANE (COMBINED 2v2)",
            gold_d=duo_delta_gold,
            xp_d=duo_delta_xp,
            is_bot_duo=True
        ))

    all_duels_rendered = "".join(duels_html)

    # Linha do tempo
    events_list_items = []
    for ev in data.get("key_events", []):
        t = ev.get("time", "00:00")
        ev_type = ev.get("type", "kill")
        
        if ev_type == "objective":
            icon_uri = AssetManager.get_asset_uri(ev.get("asset_key", ""))
            events_list_items.append(f"""
            <li class="event-item event-obj">
                <span class="event-time">{t}</span>
                <img class="event-avatar" src="{icon_uri}"/>
                <span class="event-desc"><b>{ev['desc']}</b> abatido por <b>{ev['killer_champ']}</b> ({ev['killer_name']})</span>
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

            assists_txt = f" (+{ev['assists_count']} assistência{'s' if ev['assists_count'] > 1 else ''})" if ev['assists_count'] > 0 else " <span class='tag-solokill'>SOLO</span>"

            events_list_items.append(f"""
            <li class="event-item event-kill {streak_class}">
                <span class="event-time">{t}</span>
                <div class="event-kill-duel">
                    <img class="event-avatar" src="{ev['killer_icon']}" title="{ev['killer_champ']}"/>
                    <span class="event-arrow">⚔️</span>
                    <img class="event-avatar" src="{ev['victim_icon']}" title="{ev['victim_champ']}"/>
                </div>
                <span class="event-desc">
                    <b>{ev['killer_champ']}</b> ({ev['killer_name']}) eliminou <b>{ev['victim_champ']}</b> ({ev['victim_name']}){assists_txt}
                </span>
                {streak_badge}
            </li>
            """)

    events_html = "".join(events_list_items)

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LoL Head-to-Head - {data.get('match_id')}</title>
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
        .kda-ratio {{ color: var(--accent); font-weight: 700; font-size: 0.82rem; }}
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
        .mini-icon {{ width: 14px; height: 14px; vertical-align: middle; }}
        .items-flex {{ display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }}
        .item-icon {{
            width: 26px;
            height: 26px;
            border-radius: 4px;
            border: 1px solid #334155;
            background: #0f172a;
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
            height: 150px;
            background: #090d16;
            color: #94a3b8;
            font-family: Consolas, Monaco, "Courier New", monospace;
            font-size: 0.82rem;
            padding: 12px;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            resize: vertical;
            white-space: pre;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 style="margin:0; font-size: 1.4rem;">LoL Head-to-Head Duel Analytics ({data.get('match_id')})</h1>
                <div style="color: var(--text-muted); margin-top: 4px;">Duração: {data.get('duration')} | Modo: {data.get('game_mode')}</div>
            </div>
        </div>

        <div class="team-titles">
            <div style="color: #60a5fa;">🔵 Time Azul {t100_status}</div>
            <div style="color: #f87171;">🔴 Time Vermelho {t200_status}</div>
        </div>

        <!-- CONFRONTOS LADO A LADO -->
        <div>
            {all_duels_rendered}
        </div>

        <!-- Momentos Chave -->
        <div class="card">
            <h3>🎯 Linha do Tempo & Momentos Chave</h3>
            <ul class="events-list">
                {events_html}
            </ul>
        </div>

        <!-- Resumo Bruto / LLM Prompt Box -->
        <div class="card">
            <div class="raw-summary-header">
                <h3 style="margin:0;">📋 Resumo Factual Bruto (Pronto para IA / Copiar)</h3>
                <button class="copy-btn" onclick="copyRawSummary()">Copiar Resumo</button>
            </div>
            <textarea id="rawSummaryText" class="raw-textarea" readonly>{raw_summary}</textarea>
        </div>
    </div>

    <script>
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
