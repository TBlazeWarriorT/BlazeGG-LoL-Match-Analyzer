import os
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from src.config import BASE_DIR, CACHE_DIR, MATCH_CACHE_DIR, RIOT_API_KEY, save_api_key
from src.riot_client import RiotClient, RiotAPIError
from src.cache_manager import set_last_viewed, get_last_viewed, save_session, get_last_session
from src.event_engine import MatchAnalysis
from src.ddragon import DataDragon

PORT = 8000
ddragon = DataDragon()

def get_cached_matches_list():
    matches = []
    if not MATCH_CACHE_DIR.exists():
        return matches
    for f in MATCH_CACHE_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                info = data.get("info", {})
                mid = data.get("metadata", {}).get("matchId", f.stem)
                dur_s = info.get("gameDuration", 0)
                matches.append({
                    "match_id": mid,
                    "game_mode": info.get("gameMode", "CLASSIC"),
                    "duration": f"{dur_s // 60}m {dur_s % 60}s",
                    "participants": [
                        {
                            "name": p.get("riotIdGameName", ""),
                            "tag": p.get("riotIdTagline", ""),
                            "champion": p.get("championName", ""),
                            "icon": ddragon.get_champion_icon_url(p.get("championName", "")),
                            "kda": f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
                            "win": p.get("win", False),
                            "puuid": p.get("puuid")
                        }
                        for p in info.get("participants", [])
                    ]
                })
        except Exception:
            continue
    return matches

def render_home_html(search_results=None, error_msg="", search_name="", search_tag=""):
    cached_list = get_cached_matches_list()
    last_sess = get_last_session() or {}
    def_name = search_name or last_sess.get("game_name", "Noob Master 46")
    def_tag = search_tag or last_sess.get("tag_line", "CWB")
    
    curr_key = os.getenv("RIOT_API_KEY") or RIOT_API_KEY or ""
    key_configured = bool(curr_key)
    
    if key_configured:
        masked_key = f"{curr_key[:6]}...{curr_key[-4:]}" if len(curr_key) > 10 else "******"
        key_status_badge = f'<span style="color:#86efac; background:#166534; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">Chave Ativa ({masked_key}) ✓</span>'
    else:
        masked_key = "Nenhuma"
        key_status_badge = '<span style="color:#fca5a5; background:#991b1b; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">Chave Faltando ⚠️</span>'

    search_html = ""
    if search_results is not None:
        if not search_results:
            search_html = '<div class="no-data">Nenhuma partida encontrada para este invocador.</div>'
        else:
            cards = []
            for m in search_results:
                win_class = "card-win" if m["win"] else "card-loss"
                win_txt = "VITÓRIA" if m["win"] else "DERROTA"
                cards.append(f"""
                <div class="match-item {win_class}">
                    <div class="m-left">
                        <img class="champ-avatar-lg" src="{m['champion_icon']}" alt="{m['champion']}"/>
                        <div>
                            <div class="m-champ-name">{m['champion']} <span class="m-badge {'badge-win' if m['win'] else 'badge-loss'}">{win_txt}</span></div>
                            <div class="m-sub">{m['game_mode']} • {m['duration']} • KDA: <b>{m['kda']}</b></div>
                        </div>
                    </div>
                    <a class="btn-analyze" href="/analyze?match_id={m['match_id']}&puuid={m['puuid']}">Analisar Partida ➔</a>
                </div>
                """)
            search_html = f"""
            <div class="section-card">
                <h3>🎮 Últimas Partidas de {search_name}#{search_tag} (Live Riot API)</h3>
                <div class="matches-grid">{"".join(cards)}</div>
            </div>
            """

    cached_html = ""
    if cached_list:
        c_cards = []
        for m in cached_list:
            p = m["participants"][0] if m["participants"] else {}
            if last_sess.get("puuid"):
                for part in m["participants"]:
                    if part["puuid"] == last_sess.get("puuid"):
                        p = part
                        break
            win_class = "card-win" if p.get("win") else "card-loss"
            c_cards.append(f"""
            <div class="match-item {win_class}">
                <div class="m-left">
                    <img class="champ-avatar-lg" src="{p.get('icon', '')}"/>
                    <div>
                        <div class="m-champ-name">{p.get('champion', '')} ({p.get('name')}#{p.get('tag')})</div>
                        <div class="m-sub">ID: {m['match_id']} • {m['duration']} • KDA: <b>{p.get('kda', '')}</b></div>
                    </div>
                </div>
                <a class="btn-analyze btn-cached" href="/analyze?match_id={m['match_id']}&puuid={p.get('puuid', '')}">Abrir Análise ➔</a>
            </div>
            """)
        cached_html = f"""
        <div class="section-card" style="margin-top: 24px;">
            <h3>💾 Partidas Salvas no Cache Local (Offline)</h3>
            <div class="matches-grid">{"".join(c_cards)}</div>
        </div>
        """

    error_html = f'<div class="error-banner">{error_msg}</div>' if error_msg else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>LoL API Analyzer - Central de Partidas</title>
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
            max-width: 1000px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--card-border);
            padding: 20px 24px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0; font-size: 1.5rem; }}
        .section-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 20px;
        }}
        .section-card h3 {{ margin-top: 0; font-size: 1.15rem; color: var(--accent); }}
        .form-row {{
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }}
        input[type="text"], input[type="password"] {{
            background: #090d16;
            border: 1px solid var(--card-border);
            color: #fff;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 0.95rem;
            flex: 1;
        }}
        .btn {{
            background: #2563eb;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s;
            text-decoration: none;
            font-size: 0.95rem;
        }}
        .btn:hover {{ background: #1d4ed8; }}
        .matches-grid {{ display: flex; flex-direction: column; gap: 10px; margin-top: 14px; }}
        .match-item {{
            background: #0d1322;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 4px solid #4b5563;
        }}
        .card-win {{ border-left-color: #22c55e; }}
        .card-loss {{ border-left-color: #ef4444; }}
        .m-left {{ display: flex; align-items: center; gap: 14px; }}
        .champ-avatar-lg {{
            width: 46px;
            height: 46px;
            border-radius: 50%;
            border: 2px solid var(--card-border);
        }}
        .m-champ-name {{ font-weight: 700; font-size: 1rem; display: flex; align-items: center; gap: 8px; }}
        .m-sub {{ color: var(--text-muted); font-size: 0.82rem; margin-top: 3px; }}
        .m-badge {{ padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 800; }}
        .badge-win {{ background: #166534; color: #86efac; }}
        .badge-loss {{ background: #991b1b; color: #fca5a5; }}
        .btn-analyze {{
            background: #0284c7;
            color: #fff;
            padding: 8px 14px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.85rem;
            text-decoration: none;
            transition: background 0.2s;
        }}
        .btn-analyze:hover {{ background: #0369a1; }}
        .btn-cached {{ background: #334155; }}
        .btn-cached:hover {{ background: #475569; }}
        .error-banner {{
            background: #991b1b;
            color: #fca5a5;
            padding: 12px 16px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        .no-data {{ color: var(--text-muted); font-style: italic; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>⚔️ LoL API Analyzer</h1>
                <div style="color: var(--text-muted); margin-top: 4px;">Central de Partidas & Análise Head-to-Head</div>
            </div>
            <div>{key_status_badge}</div>
        </div>

        {error_html}

        <!-- BUSCADOR DE INVOCADOR -->
        <div class="section-card">
            <h3>🔍 Buscar Invocador (Riot ID)</h3>
            <form action="/search" method="GET" class="form-row">
                <input type="text" name="game_name" placeholder="Nome de Jogo (Ex: Noob Master 46)" value="{def_name}" required style="flex: 2;"/>
                <input type="text" name="tag_line" placeholder="TAG (Ex: CWB)" value="{def_tag}" required style="flex: 1;"/>
                <button type="submit" class="btn">Buscar Partidas ➔</button>
            </form>
        </div>

        {search_html}

        {cached_html}

        <!-- CONFIGURAR API KEY -->
        <div class="section-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0;">🔑 Configuração da Riot API Key</h3>
                <a href="https://developer.riotgames.com" target="_blank" style="color:var(--accent); font-size:0.85rem; font-weight:700; text-decoration:none;">🔗 Abrir Portal Riot Developer ➔</a>
            </div>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin: 8px 0 12px 0;">
                Chave atual: <b>{masked_key}</b> • Chaves de desenvolvimento expiram a cada <b>24 horas</b>. Ao renovar no site da Riot, cole a nova chave abaixo e clique em Salvar:
            </p>
            <form action="/save_key" method="POST" class="form-row">
                <input type="password" name="api_key" placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" required/>
                <button type="submit" class="btn" style="background:#16a34a;">Salvar Chave</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path in ("", "/"):
            self._send_html(render_home_html())

        elif path == "/search":
            name = qs.get("game_name", [""])[0].strip()
            tag = qs.get("tag_line", [""])[0].strip()
            if not name or not tag:
                self._send_html(render_home_html(error_msg="Informe o Nome e a Tag do jogador."))
                return

            try:
                client = RiotClient()
                puuid = client.get_puuid(name, tag)
                save_session(name, tag, puuid)
                match_ids = client.get_recent_matches(puuid, count=8)
                
                results = []
                for mid in match_ids:
                    try:
                        m = client.get_match_detail(mid)
                        info = m.get("info", {})
                        dur_s = info.get("gameDuration", 0)
                        p = [x for x in info.get("participants", []) if x.get("puuid") == puuid][0]
                        champ = p.get("championName", "")
                        results.append({
                            "match_id": mid,
                            "puuid": puuid,
                            "champion": champ,
                            "champion_icon": ddragon.get_champion_icon_url(champ),
                            "kda": f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
                            "win": p.get("win", False),
                            "duration": f"{dur_s // 60}m {dur_s % 60}s",
                            "game_mode": info.get("gameMode", "CLASSIC")
                        })
                    except Exception:
                        continue

                self._send_html(render_home_html(search_results=results, search_name=name, search_tag=tag))

            except RiotAPIError as e:
                self._send_html(render_home_html(error_msg=str(e), search_name=name, search_tag=tag))
            except Exception as e:
                self._send_html(render_home_html(error_msg=f"Erro inesperado: {e}", search_name=name, search_tag=tag))

        elif path == "/analyze":
            match_id = qs.get("match_id", [""])[0].strip()
            puuid = qs.get("puuid", [""])[0].strip()
            if not match_id:
                self._redirect("/")
                return

            try:
                client = RiotClient()
                m = client.get_match_detail(match_id)
                t = client.get_match_timeline(match_id)
                
                if not puuid:
                    last_sess = get_last_session() or {}
                    puuid = last_sess.get("puuid")

                analyzer = MatchAnalysis(m, t, target_puuid=puuid, ddragon=ddragon)
                data = analyzer.generate_full_analysis()
                
                from src.html_report import generate_html_report, REPORT_FILE
                generate_html_report(data, open_browser=False)
                
                with open(REPORT_FILE, "r", encoding="utf-8") as rf:
                    content = rf.read()
                
                back_btn = '<div style="margin-bottom: 12px;"><a href="/" style="color:#38bdf8; text-decoration:none; font-weight:700; font-size:0.9rem; background:#111827; padding:8px 14px; border-radius:6px; border:1px solid #1f293d;">⬅ Voltar para a Central de Partidas</a></div>'
                content = content.replace('<div class="header">', back_btn + '<div class="header">')
                
                self._send_html(content)
            except Exception as e:
                self._send_html(render_home_html(error_msg=f"Erro ao analisar {match_id}: {e}"))

        else:
            self._send_html(render_home_html(error_msg="Página não encontrada."))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/save_key":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            form_data = parse_qs(body)
            new_key = form_data.get("api_key", [""])[0].strip()
            if new_key:
                save_api_key(new_key)
            self._redirect("/")
        else:
            self._redirect("/")

    def _send_html(self, html_str: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_str.encode("utf-8"))

    def _redirect(self, url: str):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

def run_app():
    server = HTTPServer(("127.0.0.1", PORT), AppHandler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"\n==================================================")
    print(f"  LoL API Analyzer App rodando em: {url}")
    print(f"  Pressione Ctrl+C no console para parar.")
    print(f"==================================================\n")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor finalizado.")

if __name__ == "__main__":
    run_app()
