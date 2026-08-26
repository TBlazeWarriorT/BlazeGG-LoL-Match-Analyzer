import webbrowser
from pathlib import Path
from typing import Dict, Any, List
from .config import CACHE_DIR
from .asset_cache import AssetManager

REPORT_FILE = CACHE_DIR / "last_report.html"

def calculate_gold_bar_share(delta: int) -> float:
    # 5000 de diferença de ouro = 100% (ou 0%)
    # +2500 = 75%
    # 0 = 50%
    # -2500 = 25%
    fraction = delta / 5000.0
    val = 50.0 + (fraction * 50.0)
    return max(4.0, min(96.0, val))

def generate_html_report(data: Dict[str, Any], open_browser: bool = True) -> Path:
    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    matchups = data.get("matchups", [])
    jungle = data.get("jungle_stats", {})
    target_puuid = data.get("target_puuid", "")

    # Assets individuais pixel-perfect em Base64
    icon_dragon_default = AssetManager.get_asset_uri("dragon_circle")
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

    def render_dragon_badges(drag_list):
        if not drag_list:
            return '<span style="color:var(--text-muted); font-size:0.85rem;">Nenhum</span>'
        return "".join([
            f'<img class="obj-badge-icon" src="{AssetManager.get_asset_uri(d["asset_key"])}" title="{d["name"]}"/>'
            for d in drag_list
        ])

    def render_grub_badges(count):
        if count == 0:
            return '<span style="color:var(--text-muted); font-size:0.85rem;">0</span>'
        return "".join([f'<img class="obj-badge-icon" src="{icon_grubs}" title="Vastilarva"/>' for _ in range(count)])

    def render_obj_badges(count, icon_uri, title):
        if count == 0:
            return '<span style="color:var(--text-muted); font-size:0.85rem;">0</span>'
        return "".join([f'<img class="obj-badge-icon" src="{icon_uri}" title="{title}"/>' for _ in range(count)])

    jungle_html = f"""
    <div class="card jungle-card">
        <h3><img class="header-icon" src="{icon_baron}"/> Disputa de Objetivos Neutros</h3>
        <div class="jungle-grid">
            <div class="team-jungle">
                <h4>🔵 Time Azul {t100_status}</h4>
                <div class="obj-stat"><span class="obj-label">Dragões:</span> <div class="obj-badges">{render_dragon_badges(j100.get('dragons', []))}</div></div>
                <div class="obj-stat"><span class="obj-label">Vastilarvas:</span> <div class="obj-badges">{render_grub_badges(j100.get('grubs', 0))}</div></div>
                <div class="obj-stat"><span class="obj-label">Arauto:</span> <div class="obj-badges">{render_obj_badges(j100.get('herald', 0), icon_herald, 'Arauto')}</div></div>
                <div class="obj-stat"><span class="obj-label">Barão:</span> <div class="obj-badges">{render_obj_badges(j100.get('baron', 0), icon_baron, 'Barão')}</div></div>
            </div>
            <div class="team-jungle">
                <h4>🔴 Time Vermelho {t200_status}</h4>
                <div class="obj-stat"><span class="obj-label">Dragões:</span> <div class="obj-badges">{render_dragon_badges(j200.get('dragons', []))}</div></div>
                <div class="obj-stat"><span class="obj-label">Vastilarvas:</span> <div class="obj-badges">{render_grub_badges(j200.get('grubs', 0))}</div></div>
                <div class="obj-stat"><span class="obj-label">Arauto:</span> <div class="obj-badges">{render_obj_badges(j200.get('herald', 0), icon_herald, 'Arauto')}</div></div>
                <div class="obj-stat"><span class="obj-label">Barão:</span> <div class="obj-badges">{render_obj_badges(j200.get('baron', 0), icon_baron, 'Barão')}</div></div>
            </div>
        </div>
    </div>
    """

    def render_duel_row(p1, p2, role_title, stats_1=None, stats_2=None, gold_d=None, xp_d=None, is_bot_duo=False, extra_badges_1="", extra_badges_2=""):
        is_t1 = p1.get("puuid") == target_puuid
        is_t2 = p2.get("puuid") == target_puuid

        # Barra baseada na diferença final de ouro (5000 delta = 100%)
        final_delta = p1.get("gold_total", 0) - p2.get("gold_total", 0)
        p1_share = calculate_gold_bar_share(final_delta)
        p2_share = 100.0 - p1_share

        def p_card(p, is_target, is_left=True, badges_html=""):
            align_class = "align-left" if is_left else "align-right"
            border_side = "border-blue" if is_left else "border-red"
            target_badge = '<span class="target-tag">VOCÊ</span>' if is_target else ""
            
            # Para o card Duo 2v2 não mostramos nick nem itens
            if is_bot_duo:
                return f"""
                <div class="player-card {align_class} {border_side} {'is-target' if is_target else ''}">
                    <div class="p-header">
                        <div class="duo-avatar-stack">
                            <img class="champ-icon duo-icon-1" src="{p['icon1']}" alt="{p['champ1']}"/>
                            <img class="champ-icon duo-icon-2" src="{p['icon2']}" alt="{p['champ2']}"/>
                        </div>
                        <div class="p-meta">
                            <div class="p-name">{p['champ1']} + {p['champ2']}</div>
                            <div class="p-champ">Duo Bot Lane</div>
                        </div>
                    </div>
                    <div class="p-kda">KDA: <b>{p['kda']}</b> | <img class="mini-icon" src="{icon_cs}"/> <b>{p['cs']}</b></div>
                    <div class="stats-pills">
                        <div class="pill">Dano: <b>{p['damage_to_champions']:,}</b></div>
                        <div class="pill">Dano/Ouro: <b>{p['damage_per_gold']}</b></div>
                        <div class="pill">Tomado: <b>{p['damage_taken']:,}</b></div>
                        <div class="pill"><img class="mini-icon" src="{icon_gold}"/> <b>{p['gold_total']:,}</b></div>
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
                <div class="p-kda">KDA: <b>{p['kda']}</b> | <img class="mini-icon" src="{icon_cs}"/> <b>{p['cs']}</b></div>
                <div class="stats-pills">
                    <div class="pill">Dano: <b>{p['damage_to_champions']:,}</b></div>
                    <div class="pill">Dano/Ouro: <b>{p['damage_per_gold']}</b></div>
                    <div class="pill">Tomado: <b>{p['damage_taken']:,}</b></div>
                    <div class="pill"><img class="mini-icon" src="{icon_gold}"/> <b>{p['gold_total']:,}</b></div>
                </div>
                <div class="items-flex">{items_html}</div>
                {obj_strip_html}
            </div>
            """

        p1_html = p_card(p1, is_t1, is_left=True, badges_html=extra_badges_1)
        p2_html = p_card(p2, is_t2, is_left=False, badges_html=extra_badges_2)

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

            duel_info_box = ""
            if not is_bot_duo:
                duel_info_box = f"""
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
                """

            delta_html = f"""
            <div class="duel-center">
                <div class="role-badge-lg">{role_title}</div>
                
                <div class="lane-bar-container" title="Distribuição de Ouro (5000 delta = barra cheia)">
                    <div class="lane-bar-blue" style="width: {p1_share:.1f}%;"></div>
                    <div class="lane-bar-red" style="width: {p2_share:.1f}%;"></div>
                </div>

                {duel_info_box}

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

    # JUNGLE com as bolotas de objetivos capturados
    if "JUNGLE" in m_by_role:
        m = m_by_role["JUNGLE"]
        
        j1_badges = render_dragon_badges(j100.get('dragons', [])) + " " + render_grub_badges(j100.get('grubs', 0))
        j2_badges = render_dragon_badges(j200.get('dragons', [])) + " " + render_grub_badges(j200.get('grubs', 0))

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

    # BOT LANE (COMBINED 2v2) logo após ADC e SUP
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

        duo_p1 = {
            "champ1": p1_bot["champion"], "icon1": p1_bot["champion_icon"],
            "champ2": p1_sup["champion"], "icon2": p1_sup["champion_icon"],
            "kda": f"{d1_kills}/{d1_deaths}/{d1_assists}",
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
            "cs": d2_cs,
            "damage_to_champions": d2_dmg,
            "damage_per_gold": round(d2_dmg / max(d2_gold, 1), 2),
            "damage_taken": d2_taken,
            "gold_total": d2_gold,
            "puuid": p2_bot["puuid"] if target_puuid in (p2_bot["puuid"], p2_sup["puuid"]) else ""
        }

        duo_delta_gold = {}
        for k in m_bot["gold_delta"].keys():
            duo_delta_gold[k] = m_bot["gold_delta"].get(k, 0) + m_sup["gold_delta"].get(k, 0)

        duels_html.append(render_duel_row(
            duo_p1, duo_p2, "BOT LANE (COMBINED 2v2)",
            gold_d=duo_delta_gold,
            is_bot_duo=True
        ))

    all_duels_rendered = "".join(duels_html)

    # Linha do tempo com espaçamento e tags limpas
    events_list_items = []
    for ev in data.get("key_events", []):
        raw_text = ev.get("text") if isinstance(ev, dict) else str(ev)
        asset_key = ev.get("asset_key") if isinstance(ev, dict) else None
        
        icon_uri = AssetManager.get_asset_uri(asset_key) if asset_key else ""
        icon_html = f'<img class="event-icon" src="{icon_uri}"/> ' if icon_uri else ""
        events_list_items.append(f'<li class="event-item">{icon_html}<span>{raw_text}</span></li>')

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
        .bot-duo-row {{
            background: linear-gradient(180deg, #131c31 0%, #0d1322 100%);
            border: 1px solid #2a3a5e;
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
        .duo-avatar-stack {{
            position: relative;
            width: 54px;
            height: 44px;
        }}
        .duo-icon-1 {{ position: absolute; left: 0; top: 0; z-index: 2; }}
        .duo-icon-2 {{ position: absolute; left: 16px; top: 0; z-index: 1; opacity: 0.85; }}
        
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
        .jungle-mini-strip {{
            display: flex;
            align-items: center;
            gap: 4px;
            margin-top: 4px;
            background: #0a0e1a;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px dashed var(--card-border);
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
        
        .header-icon {{ width: 22px; height: 22px; vertical-align: middle; margin-right: 6px; }}
        .obj-icon {{ width: 24px; height: 24px; vertical-align: middle; margin-right: 6px; border-radius: 50%; }}
        .obj-badge-icon {{ width: 20px; height: 20px; vertical-align: middle; border-radius: 50%; }}
        .jungle-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .team-jungle {{ background: #0d1322; padding: 14px; border-radius: 8px; border: 1px solid var(--card-border); }}
        .obj-stat {{ display: flex; align-items: center; justify-content: space-between; margin: 8px 0; font-size: 0.9rem; }}
        .obj-label {{ color: var(--text-muted); }}
        .obj-badges {{ display: flex; gap: 4px; align-items: center; }}

        .events-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .event-item {{
            background: #0d1322;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 0.88rem;
            display: flex;
            align-items: center;
            gap: 8px;
            line-height: 1.4;
        }}
        .event-icon {{ width: 22px; height: 22px; vertical-align: middle; border-radius: 50%; flex-shrink: 0; }}
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
