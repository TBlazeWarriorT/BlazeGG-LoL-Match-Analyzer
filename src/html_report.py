import webbrowser
from pathlib import Path
from typing import Dict, Any, List
from .config import CACHE_DIR
from .asset_cache import AssetManager

REPORT_FILE = CACHE_DIR / "last_report.html"

def get_dragon_asset_key(sub_type: str = "") -> str:
    sub = sub_type.upper()
    if "AIR" in sub:
        return "dragon_circle_air"
    elif "CHEMTECH" in sub:
        return "dragon_circle_chemtech"
    elif "EARTH" in sub:
        return "dragon_circle_earth"
    elif "FIRE" in sub:
        return "dragon_circle_fire"
    elif "HEXTECH" in sub:
        return "dragon_circle_hextech"
    elif "WATER" in sub:
        return "dragon_circle_water"
    return "dragon_circle"

def calculate_bar_share(val1: int, val2: int) -> float:
    tot = val1 + val2
    if tot == 0:
        return 50.0
    ratio = val1 / tot
    adjusted = 50.0 + (ratio - 0.5) * 200.0
    return max(5.0, min(95.0, adjusted))

def generate_html_report(data: Dict[str, Any], open_browser: bool = True) -> Path:
    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    matchups = data.get("matchups", [])
    jungle = data.get("jungle_stats", {})
    target_puuid = data.get("target_puuid", "")

    # Assets individuais pixel-perfect em Base64
    icon_dragon = AssetManager.get_asset_uri("dragon_circle")
    icon_grubs = AssetManager.get_asset_uri("sru_voidgrub_circle")
    icon_herald = AssetManager.get_asset_uri("sruriftherald_circle")
    icon_baron = AssetManager.get_asset_uri("baron_circle")
    icon_gold = AssetManager.get_asset_uri("gold_icon")
    icon_xp = AssetManager.get_asset_uri("xp_icon")
    icon_cs = AssetManager.get_asset_uri("cs_icon")

    t100_win = team_100.get("win", False)
    t200_win = team_200.get("win", False)
    t100_status = '<span class="badge win-badge">VITÓRIA</span>' if t100_win else '<span class="badge loss-badge">DERROTA</span>'
    t200_status = '<span class="badge win-badge">VITÓRIA</span>' if t200_win else '<span class="badge loss-badge">DERROTA</span>'

    j100 = jungle.get(100, {})
    j200 = jungle.get(200, {})
    jungle_html = f"""
    <div class="card jungle-card">
        <h3><img class="header-icon" src="{icon_baron}"/> Disputa de Objetivos Neutros</h3>
        <div class="jungle-grid">
            <div class="team-jungle">
                <h4>🔵 Time Azul {t100_status}</h4>
                <div class="obj-stat"><img class="obj-icon" src="{icon_dragon}"/> Dragões: <b>{j100.get('dragons', 0)}</b></div>
                <div class="obj-stat"><img class="obj-icon" src="{icon_grubs}"/> Vastilarvas: <b>{j100.get('grubs', 0)}</b></div>
                <div class="obj-stat"><img class="obj-icon" src="{icon_herald}"/> Arauto: <b>{j100.get('herald', 0)}</b></div>
                <div class="obj-stat"><img class="obj-icon" src="{icon_baron}"/> Barão: <b>{j100.get('baron', 0)}</b></div>
            </div>
            <div class="team-jungle">
                <h4>🔴 Time Vermelho {t200_status}</h4>
                <div class="obj-stat"><img class="obj-icon" src="{icon_dragon}"/> Dragões: <b>{j200.get('dragons', 0)}</b></div>
                <div class="obj-stat"><img class="obj-icon" src="{icon_grubs}"/> Vastilarvas: <b>{j200.get('grubs', 0)}</b></div>
                <div class="obj-stat"><img class="obj-icon" src="{icon_herald}"/> Arauto: <b>{j200.get('herald', 0)}</b></div>
                <div class="obj-stat"><img class="obj-icon" src="{icon_baron}"/> Barão: <b>{j200.get('baron', 0)}</b></div>
            </div>
        </div>
    </div>
    """

    def render_duel_row(p1, p2, role_title, stats_1=None, stats_2=None, gold_d=None, xp_d=None):
        is_t1 = p1.get("puuid") == target_puuid
        is_t2 = p2.get("puuid") == target_puuid

        g1 = p1.get("gold_total", 0)
        g2 = p2.get("gold_total", 0)
        p1_share = calculate_bar_share(g1, g2)
        p2_share = 100.0 - p1_share

        def p_card(p, is_target, is_left=True):
            items_html = "".join([
                f'<img class="item-icon" src="{it["icon"]}" title="{it["name"]}" alt="{it["name"]}"/>'
                for it in p.get("items", [])
            ])
            target_badge = '<span class="target-tag">VOCÊ</span>' if is_target else ""
            align_class = "align-left" if is_left else "align-right"
            border_side = "border-blue" if is_left else "border-red"
            
            return f"""
            <div class="player-card {align_class} {border_side} {'is-target' if is_target else ''}">
                <div class="p-header">
                    <img class="champ-icon" src="{p['champion_icon']}" alt="{p['champion']}"/>
                    <div class="p-meta">
                        <div class="p-name">{p['riot_id']} {target_badge}</div>
                        <div class="p-champ">{p['champion']}</div>
                    </div>
                </div>
                <div class="p-kda">KDA: <b>{p['kda']}</b> | <img class="mini-icon" src="{icon_cs}"/> <b>{p['cs']}</b></div>
                <div class="stats-pills">
                    <div class="pill">Dano: <b>{p['damage_to_champions']:,}</b></div>
                    <div class="pill">Dano/Ouro: <b>{p['damage_per_gold']}</b></div>
                    <div class="pill">Tomado: <b>{p['damage_taken']:,}</b></div>
                    <div class="pill"><img class="mini-icon" src="{icon_gold}"/> <b>{p['gold_total']:,}</b></div>
                </div>
                <div class="items-flex">{items_html}</div>
            </div>
            """

        p1_html = p_card(p1, is_t1, is_left=True)
        p2_html = p_card(p2, is_t2, is_left=False)

        delta_html = ""
        if gold_d:
            gold_tags = "".join([
                f'<span class="delta-tag">@{k}: <b class="{"pos" if v>=0 else "neg"}">{"+" if v>=0 else ""}{v:,}</b></span>'
                for k, v in gold_d.items()
            ])
            xp_tags = "".join([
                f'<span class="delta-tag">@{k}: <b class="{"pos" if v>=0 else "neg"}">{"+" if v>=0 else ""}{v:,}</b></span>'
                for k, v in xp_d.items()
            ]) if xp_d else ""

            solo_kills_1 = stats_1.get("solo_kills", 0) if stats_1 else 0
            solo_deaths_1 = stats_1.get("solo_deaths", 0) if stats_1 else 0
            ganks_1 = stats_1.get("other_deaths", 0) if stats_1 else 0

            solo_kills_2 = stats_2.get("solo_kills", 0) if stats_2 else 0
            solo_deaths_2 = stats_2.get("solo_deaths", 0) if stats_2 else 0
            ganks_2 = stats_2.get("other_deaths", 0) if stats_2 else 0

            delta_html = f"""
            <div class="duel-center">
                <div class="role-badge-lg">{role_title}</div>
                
                <div class="lane-bar-container" title="Distribuição de Vantagem de Ouro na Lane">
                    <div class="lane-bar-blue" style="width: {p1_share:.1f}%;"></div>
                    <div class="lane-bar-red" style="width: {p2_share:.1f}%;"></div>
                </div>

                <div class="duel-duels">
                    <div class="duel-sub-stats">
                        <span>Solo Kills: <b class="pos">{solo_kills_1}</b></span> |
                        <span>Mortes Solo: <b class="neg">{solo_deaths_1}</b></span> |
                        <span>Mortes p/ Gank: <b>{ganks_1}</b></span>
                    </div>
                    <div class="duel-sub-stats" style="margin-top:2px;">
                        <span>Solo Kills: <b class="pos">{solo_kills_2}</b></span> |
                        <span>Mortes Solo: <b class="neg">{solo_deaths_2}</b></span> |
                        <span>Mortes p/ Gank: <b>{ganks_2}</b></span>
                    </div>
                </div>
                <div class="delta-box">
                    <div class="delta-title"><img class="mini-icon" src="{icon_gold}"/> Diferença de Ouro (Azul - Vermelho):</div>
                    <div class="delta-flex">{gold_tags}</div>
                    {f'<div class="delta-title" style="margin-top:4px;"><img class="mini-icon" src="{icon_xp}"/> Diferença de XP:</div><div class="delta-flex">{xp_tags}</div>' if xp_tags else ''}
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
        <div class="duel-row">
            {p1_html}
            {delta_html}
            {p2_html}
        </div>
        """

    duels_html = []
    m_by_role = {m["role"]: m for m in matchups}

    for r in ["TOP", "JUNGLE", "MIDDLE"]:
        if r in m_by_role:
            m = m_by_role[r]
            duels_html.append(render_duel_row(
                m["player1"], m["player2"], r,
                m["p1_stats"], m["p2_stats"],
                m["gold_delta"], m["xp_delta"]
            ))

    m_bot = m_by_role.get("BOTTOM")
    m_sup = m_by_role.get("UTILITY")

    if m_bot and m_sup:
        p1_bot, p2_bot = m_bot["player1"], m_bot["player2"]
        p1_sup, p2_sup = m_sup["player1"], m_sup["player2"]

        t1_dmg = p1_bot["damage_to_champions"] + p1_sup["damage_to_champions"]
        t2_dmg = p2_bot["damage_to_champions"] + p2_sup["damage_to_champions"]
        t1_gold = p1_bot["gold_total"] + p1_sup["gold_total"]
        t2_gold = p2_bot["gold_total"] + p2_sup["gold_total"]
        t1_cs = p1_bot["cs"] + p1_sup["cs"]
        t2_cs = p2_bot["cs"] + p2_sup["cs"]
        t1_kills = p1_bot["kills"] + p1_sup["kills"]
        t1_deaths = p1_bot["deaths"] + p1_sup["deaths"]
        t1_assists = p1_bot["assists"] + p1_sup["assists"]
        t2_kills = p2_bot["kills"] + p2_bot["kills"]
        t2_deaths = p2_bot["deaths"] + p2_sup["deaths"]
        t2_assists = p2_bot["assists"] + p2_sup["assists"]

        duo_share = calculate_bar_share(t1_gold, t2_gold)

        duo_delta_gold = {}
        for k in m_bot["gold_delta"].keys():
            duo_delta_gold[k] = m_bot["gold_delta"].get(k, 0) + m_sup["gold_delta"].get(k, 0)

        duo_gold_tags = "".join([
            f'<span class="delta-tag">@{k}: <b class="{"pos" if v>=0 else "neg"}">{"+" if v>=0 else ""}{v:,}</b></span>'
            for k, v in duo_delta_gold.items()
        ])

        bot_duo_summary_html = f"""
        <div class="card bot-duo-card">
            <div class="bot-duo-header">
                <h3>👥 BOT LANE 2v2 (Duo Somado: ADC + SUP)</h3>
            </div>
            <div class="bot-duo-grid">
                <div class="duo-team-stat align-left">
                    <h4>🔵 Duo Azul ({p1_bot['champion']} + {p1_sup['champion']})</h4>
                    <div>Abates Duo: <b>{t1_kills}/{t1_deaths}/{t1_assists}</b> | <img class="mini-icon" src="{icon_cs}"/> Total: <b>{t1_cs}</b></div>
                    <div>Dano Somado: <b>{t1_dmg:,}</b> | <img class="mini-icon" src="{icon_gold}"/> Total: <b>{t1_gold:,}</b></div>
                </div>
                <div class="duo-delta-box">
                    <div class="lane-bar-container" style="margin-bottom: 8px;">
                        <div class="lane-bar-blue" style="width: {duo_share:.1f}%;"></div>
                        <div class="lane-bar-red" style="width: {100.0 - duo_share:.1f}%;"></div>
                    </div>
                    <div class="delta-title" style="margin-bottom:4px;"><img class="mini-icon" src="{icon_gold}"/> Diferença de Ouro 2v2:</div>
                    <div class="delta-flex" style="justify-content:center;">{duo_gold_tags}</div>
                </div>
                <div class="duo-team-stat align-right">
                    <h4>🔴 Duo Vermelho ({p2_bot['champion']} + {p2_sup['champion']})</h4>
                    <div>Abates Duo: <b>{t2_kills}/{t2_deaths}/{t2_assists}</b> | <img class="mini-icon" src="{icon_cs}"/> Total: <b>{t2_cs}</b></div>
                    <div>Dano Somado: <b>{t2_dmg:,}</b> | <img class="mini-icon" src="{icon_gold}"/> Total: <b>{t2_gold:,}</b></div>
                </div>
            </div>
        </div>
        """

        duels_html.append(render_duel_row(
            p1_bot, p2_bot, "ADC (BOTTOM)",
            m_bot["p1_stats"], m_bot["p2_stats"],
            m_bot["gold_delta"], m_bot["xp_delta"]
        ))
        duels_html.append(render_duel_row(
            p1_sup, p2_sup, "SUPORTE (UTILITY)",
            m_sup["p1_stats"], m_sup["p2_stats"],
            m_sup["gold_delta"], m_sup["xp_delta"]
        ))
    else:
        bot_duo_summary_html = ""

    all_duels_rendered = "".join(duels_html)

    events_list_items = []
    for ev in data.get("key_events", []):
        raw_text = ev.get("text") if isinstance(ev, dict) else str(ev)
        asset_key = ev.get("asset_key") if isinstance(ev, dict) else None
        
        icon_uri = AssetManager.get_asset_uri(asset_key) if asset_key else ""
        icon_html = f'<img class="event-icon" src="{icon_uri}"/> ' if icon_uri else ""
        events_list_items.append(f'<li class="event-item">{icon_html}{raw_text}</li>')

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
            max-width: 1320px;
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
            grid-template-columns: 1fr 340px 1fr;
            gap: 16px;
            align-items: center;
            background: #0d1322;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 14px;
        }}
        @media (max-width: 1050px) {{
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
        .duel-center {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 6px;
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
        
        .lane-bar-container {{
            width: 100%;
            height: 8px;
            background: #1e293b;
            border-radius: 4px;
            display: flex;
            overflow: hidden;
            border: 1px solid var(--card-border);
            margin: 4px 0;
        }}
        .lane-bar-blue {{
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
            transition: width 0.3s ease;
        }}
        .lane-bar-red {{
            background: linear-gradient(90deg, #f87171, #ef4444);
            transition: width 0.3s ease;
        }}

        .duel-duels {{
            font-size: 0.76rem;
            color: var(--text-muted);
            background: #151d30;
            padding: 8px 10px;
            border-radius: 6px;
            width: 100%;
        }}
        .delta-box {{
            background: #151d30;
            padding: 8px 10px;
            border-radius: 6px;
            width: 100%;
            font-size: 0.76rem;
        }}
        .delta-title {{ color: var(--text-muted); margin-bottom: 4px; font-weight: 600; display: flex; align-items: center; justify-content: center; gap: 4px; }}
        .delta-flex {{ display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }}
        .delta-tag {{ background: #080c14; padding: 2px 6px; border-radius: 4px; }}
        .pos {{ color: var(--green); }}
        .neg {{ color: var(--red); }}
        .badge {{ padding: 4px 10px; border-radius: 14px; font-size: 0.8rem; font-weight: 700; }}
        .win-badge {{ background: #166534; color: #86efac; }}
        .loss-badge {{ background: #991b1b; color: #fca5a5; }}
        .align-left {{ text-align: left; }}
        .align-right {{ text-align: left; }}
        
        .bot-duo-card {{
            background: linear-gradient(180deg, #131c31 0%, #0d1322 100%);
            border: 1px solid #2a3a5e;
            margin-bottom: 14px;
        }}
        .bot-duo-grid {{
            display: grid;
            grid-template-columns: 1fr 340px 1fr;
            gap: 16px;
            align-items: center;
        }}
        @media (max-width: 1050px) {{
            .bot-duo-grid {{ grid-template-columns: 1fr; }}
        }}
        .duo-team-stat h4 {{ margin: 0 0 6px 0; }}
        .duo-team-stat {{ font-size: 0.88rem; line-height: 1.5; }}
        .duo-delta-box {{
            background: #0a0e1a;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--card-border);
        }}
        
        .header-icon {{ width: 22px; height: 22px; vertical-align: middle; margin-right: 6px; }}
        .obj-icon {{ width: 24px; height: 24px; vertical-align: middle; margin-right: 6px; border-radius: 50%; }}
        .event-icon {{ width: 20px; height: 20px; vertical-align: middle; margin-right: 8px; border-radius: 50%; }}
        .jungle-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .team-jungle {{ background: #0d1322; padding: 14px; border-radius: 8px; border: 1px solid var(--card-border); }}
        .obj-stat {{ display: flex; align-items: center; margin: 6px 0; font-size: 0.92rem; }}
        .events-list {{ list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }}
        .event-item {{
            background: #0d1322;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.88rem;
            display: flex;
            align-items: center;
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

        <!-- BOT LANE DUO 2v2 SOMADO -->
        {bot_duo_summary_html}

        <!-- CONFRONTOS LADO A LADO -->
        <div>
            {all_duels_rendered}
        </div>

        <!-- Objetivos da Selva -->
        {jungle_html}

        <!-- Momentos Chave -->
        <div class="card">
            <h3>🎯 Linha do Tempo & Momentos Chave</h3>
            <ul class="events-list">
                {events_html}
            </ul>
        </div>
    </div>
</body>
</html>
"""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    if open_browser:
        webbrowser.open(REPORT_FILE.as_uri())

    return REPORT_FILE
