import webbrowser
from pathlib import Path
from typing import Dict, Any
from .config import CACHE_DIR

REPORT_FILE = CACHE_DIR / "last_report.html"

def generate_html_report(data: Dict[str, Any], open_browser: bool = True) -> Path:
    target = data.get("target", {})
    opp = data.get("opponent", {})
    lane = data.get("lane_stats", {})
    win = data.get("win", False)
    
    bg_gradient = "linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%)" if win else "linear-gradient(135deg, #2b090a 0%, #1a0808 100%)"
    badge_bg = "#10b981" if win else "#ef4444"
    status_text = "VITÓRIA" if win else "DERROTA"

    # Itens do Jogador
    target_items_html = "".join([f'<span class="item-badge">{item}</span>' for item in target.get("items", [])])
    
    # Eventos
    events_html = "".join([f'<li class="event-item">{ev}</li>' for ev in data.get("key_events", [])])

    # Tabela Gold Delta
    gold_rows_html = ""
    for minute, info in lane.get("gold_diff_timeline", {}).items():
        min_num = minute.replace("min_", "")
        delta = info.get("delta", 0)
        delta_class = "gold-pos" if delta >= 0 else "gold-neg"
        delta_sign = "+" if delta >= 0 else ""
        gold_rows_html += f"""
        <tr>
            <td>{min_num} min</td>
            <td>{info.get('target_gold', 0):,}g</td>
            <td>{info.get('opponent_gold', 0):,}g</td>
            <td class="{delta_class}"><b>{delta_sign}{delta:,}g</b></td>
        </tr>
        """

    opp_card_html = ""
    if opp:
        opp_items_html = "".join([f'<span class="item-badge">{item}</span>' for item in opp.get("items", [])])
        opp_card_html = f"""
        <div class="card opponent-card">
            <h3>⚔️ Oponente Direto ({opp.get('champion')})</h3>
            <div class="kda-box">
                <div class="riot-id">{opp.get('riot_id')}</div>
                <div class="kda-val">{opp.get('kda')}</div>
            </div>
            <div class="stats-grid">
                <div class="stat"><span class="label">CS:</span> <b>{opp.get('cs')}</b></div>
                <div class="stat"><span class="label">Dano:</span> <b>{opp.get('damage_to_champions', 0):,}</b></div>
                <div class="stat"><span class="label">Dano/Ouro:</span> <b>{opp.get('damage_per_gold')}</b></div>
                <div class="stat"><span class="label">Ouro Total:</span> <b>{opp.get('gold_total', 0):,}</b></div>
            </div>
            <div class="items-section">
                <div class="label">Itens:</div>
                <div class="items-container">{opp_items_html}</div>
            </div>
            <div class="lane-duel">
                <div>Mortes Solo sofridas: <b>{lane.get('solo_deaths_in_lane', 0)}</b></div>
                <div>Mortes em Gank/Skirmish: <b>{lane.get('deaths_in_skirmish_or_gank', 0)}</b></div>
                <div>Kills Solo efetuados: <b>{lane.get('solo_kills_in_lane', 0)}</b></div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise de Partida - {target.get('champion')}</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --border: #334155;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 24px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 900px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .header {{
            background: {bg_gradient};
            border: 1px solid var(--border);
            padding: 24px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .badge {{
            background-color: {badge_bg};
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.9rem;
            letter-spacing: 0.5px;
        }}
        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            padding: 20px;
            border-radius: 12px;
        }}
        .matchup-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 768px) {{
            .matchup-container {{ grid-template-columns: 1fr; }}
        }}
        .kda-box {{
            margin-bottom: 16px;
        }}
        .riot-id {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--accent);
        }}
        .kda-val {{
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 4px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }}
        .stat {{
            background: #0f172a;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        .label {{
            color: var(--text-muted);
        }}
        .items-section {{
            margin-top: 12px;
        }}
        .items-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 6px;
        }}
        .item-badge {{
            background: #334155;
            color: #cbd5e1;
            font-size: 0.8rem;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        .lane-duel {{
            margin-top: 14px;
            padding-top: 12px;
            border-top: 1px dashed var(--border);
            font-size: 0.88rem;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        th {{
            color: var(--text-muted);
            font-weight: 600;
        }}
        .gold-pos {{ color: #10b981; }}
        .gold-neg {{ color: #ef4444; }}
        .events-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .event-item {{
            background: #0f172a;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 0.9rem;
            border-left: 3px solid var(--accent);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 style="margin: 0; font-size: 1.6rem;">{target.get('champion')} ({target.get('role', 'LANE')})</h1>
                <div style="color: var(--text-muted); margin-top: 4px;">Partida: {data.get('match_id')} | Duração: {data.get('duration')}</div>
            </div>
            <div class="badge">{status_text}</div>
        </div>

        <div class="matchup-container">
            <div class="card">
                <h3>👑 Jogador ({target.get('champion')})</h3>
                <div class="kda-box">
                    <div class="riot-id">{target.get('riot_id')}</div>
                    <div class="kda-val">{target.get('kda')}</div>
                </div>
                <div class="stats-grid">
                    <div class="stat"><span class="label">CS:</span> <b>{target.get('cs')}</b></div>
                    <div class="stat"><span class="label">Dano:</span> <b>{target.get('damage_to_champions', 0):,}</b></div>
                    <div class="stat"><span class="label">Dano/Ouro:</span> <b>{target.get('damage_per_gold')}</b></div>
                    <div class="stat"><span class="label">KP%:</span> <b>{target.get('kill_participation_pct')}%</b></div>
                    <div class="stat"><span class="label">Visão:</span> <b>{target.get('vision_score')}</b></div>
                    <div class="stat"><span class="label">Ouro Total:</span> <b>{target.get('gold_total', 0):,}</b></div>
                </div>
                <div class="items-section">
                    <div class="label">Itens Finais:</div>
                    <div class="items-container">{target_items_html}</div>
                </div>
            </div>

            {opp_card_html}
        </div>

        <div class="card">
            <h3>💰 Curva de Ouro (Gold Delta vs Oponente)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Tempo</th>
                        <th>Ouro Jogador</th>
                        <th>Ouro Oponente</th>
                        <th>Diferença</th>
                    </tr>
                </thead>
                <tbody>
                    {gold_rows_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3>🎯 Momentos Chave da Partida</h3>
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
