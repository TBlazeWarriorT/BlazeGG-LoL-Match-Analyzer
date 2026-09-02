import os
import json
import webbrowser
import urllib.parse
from urllib.parse import urlparse, parse_qs
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import concurrent.futures
from pathlib import Path

from src.config import BASE_DIR, CACHE_DIR, MATCH_CACHE_DIR, get_api_key, get_key_expires_at, save_api_key, is_production_mode, parse_expiry_str
from src.riot_client import RiotClient, RiotAPIError
from src.cache_manager import set_last_viewed, get_last_viewed, save_session, get_last_session
from src.event_engine import MatchAnalysis
from src.ddragon import DataDragon
from src.i18n import get_text, SUPPORTED_LANGUAGES, render_language_dropdown
from src.hub_view import render_home_html, format_relative_time, get_cached_matches_list, get_ddragon

PORT = int(os.environ.get("PORT", 8000))

class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        import importlib
        import src.config
        import src.riot_client
        import src.i18n
        importlib.reload(src.config)
        importlib.reload(src.i18n)
        importlib.reload(src.riot_client)

        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        host_header = self.headers.get("Host", "").lower()
        x_forwarded_for = self.headers.get("X-Forwarded-For", "")
        client_ip = self.client_address[0]
        
        is_local = not is_production_mode()

        cookies_raw = self.headers.get("Cookie", "")
        import http.cookies
        import urllib.parse
        cookie_obj = http.cookies.SimpleCookie()
        if cookies_raw:
            try:
                cookie_obj.load(cookies_raw)
            except Exception:
                pass

        cookie_lang = urllib.parse.unquote(cookie_obj.get("blaze_lang").value) if "blaze_lang" in cookie_obj else ""
        lang = qs.get("lang", [""])[0].strip() or cookie_lang or "en_US"
        if lang not in SUPPORTED_LANGUAGES:
            lang = "en_US"

        sess_key = urllib.parse.unquote(cookie_obj.get("blaze_dev_key").value) if "blaze_dev_key" in cookie_obj else ""
        sess_exp = urllib.parse.unquote(cookie_obj.get("blaze_dev_exp").value) if "blaze_dev_exp" in cookie_obj else ""
        
        hist_cookie = urllib.parse.unquote(cookie_obj.get("blaze_history").value) if "blaze_history" in cookie_obj else ""
        user_history = [h.strip() for h in hist_cookie.split("|") if h.strip()] if hist_cookie else []

        if path in ("/ping", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if path == "/riot.txt":
            riot_file = BASE_DIR / "riot.txt"
            content = riot_file.read_text(encoding="utf-8").strip() if riot_file.exists() else "da8c9e97-f726-47bc-9a8c-cf96fbe8f0ac"
            data_bytes = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data_bytes)))
            self.end_headers()
            self.wfile.write(data_bytes)
            return

        if path in ("", "/"):
            self._send_html(render_home_html(lang=lang, session_key=sess_key, session_expiry=sess_exp, user_history=user_history, is_local=is_local))

        elif path == "/search_match":
            mid_input = qs.get("match_id", [""])[0].strip()
            if not mid_input:
                self._redirect(f"/?lang={lang}")
                return
            
            # Format clean match_id
            match_id = mid_input.upper()
            if match_id.startswith("KR1_"):
                match_id = "KR_" + match_id[4:]
            elif not any(match_id.startswith(p + "_") for p in ["BR1", "NA1", "EUW1", "EUN1", "KR", "JP1", "LA1", "LA2", "OC1", "TR1", "RU", "ME1", "PH2", "SG2", "TH2", "TW2", "VN2"]) and match_id.isdigit():
                match_id = f"BR1_{match_id}"
            
            self._redirect(f"/analyze?match_id={match_id}&lang={lang}")
            return

        elif path == "/search":
            name = qs.get("game_name", [""])[0].strip()
            tag = qs.get("tag_line", [""])[0].strip()

            if "#" in name and not tag:
                parts = name.split("#", 1)
                name = parts[0].strip()
                tag = parts[1].strip()
            elif "#" in name:
                name = name.split("#")[0].strip()

            if not name or not tag:
                err_msg = get_text("err_provide_name_tag", lang=lang)
                self._send_html(render_home_html(error_msg=err_msg, lang=lang, session_key=sess_key, session_expiry=sess_exp))
                return

            try:
                client = RiotClient(api_key=get_api_key(session_key=sess_key), lang=lang)
                puuid = client.get_puuid(name, tag)
                save_session(name, tag, puuid)
                match_ids = client.get_recent_matches(puuid, count=8)
                
                dd = get_ddragon(lang)
                
                def fetch_single_match(mid):
                    try:
                        m = client.get_match_detail(mid, target_puuid=puuid)
                        info = m.get("info", {})
                        dur_s = info.get("gameDuration", 0)
                        creation_ms = info.get("gameCreation", 0)
                        
                        t1_parts = []
                        t2_parts = []
                        target_p = None
                        for part in info.get("participants", []):
                            raw_champ = part.get("championName", "")
                            p_info = {
                                "name": part.get("riotIdGameName", ""),
                                "tag": part.get("riotIdTagline", ""),
                                "champion": dd.get_clean_champion_name(raw_champ),
                                "icon": dd.get_champion_icon_url(raw_champ),
                                "kda": f"{part.get('kills')}/{part.get('deaths')}/{part.get('assists')}",
                                "win": part.get("win", False),
                                "placement": part.get("subteamPlacement") or part.get("placement") or part.get("challenges", {}).get("placement", 0),
                                "puuid": part.get("puuid"),
                                "team_id": part.get("teamId", 100),
                                "role": part.get("teamPosition") or part.get("individualPosition", "UNKNOWN")
                            }
                            if part.get("puuid") == puuid:
                                target_p = part
                            if part.get("teamId", 100) == 100:
                                t1_parts.append(p_info)
                            else:
                                t2_parts.append(p_info)

                        if not target_p and info.get("participants"):
                            target_p = info["participants"][0]

                        raw_champ = target_p.get("championName", "") if target_p else ""
                        target_placement = target_p.get("subteamPlacement") or target_p.get("placement") or target_p.get("challenges", {}).get("placement", 0) if target_p else 0
                        return {
                            "match_id": mid,
                            "puuid": puuid,
                            "champion": dd.get_clean_champion_name(raw_champ),
                            "champion_icon": dd.get_champion_icon_url(raw_champ),
                            "kda": f"{target_p.get('kills')}/{target_p.get('deaths')}/{target_p.get('assists')}" if target_p else "0/0/0",
                            "win": target_p.get("win", False) if target_p else False,
                            "placement": target_placement,
                            "duration": f"{dur_s // 60}m {dur_s % 60}s",
                            "relative_time": format_relative_time(creation_ms, lang=lang),
                            "game_mode": info.get("gameMode", "CLASSIC"),
                            "queue_id": info.get("queueId", 0),
                            "team_100": t1_parts,
                            "team_200": t2_parts
                        }
                    except Exception:
                        return None

                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    fetched_items = list(executor.map(fetch_single_match, match_ids))
                    results = [item for item in fetched_items if item is not None]

                # Add summoner to user's history list
                searched_riot_id = f"{name}#{tag}"
                new_hist = [h for h in user_history if h.lower() != searched_riot_id.lower()]
                new_hist.insert(0, searched_riot_id)
                new_hist = new_hist[:10]  # Store up to 10 recent summoners
                import urllib.parse
                hist_cookie_val = urllib.parse.quote("|".join(new_hist))
                
                # Send HTML with Set-Cookie header for history
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Set-Cookie", f"blaze_history={hist_cookie_val}; Path=/; SameSite=Lax; Max-Age=31536000")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                
                rendered_html = render_home_html(search_results=results, search_name=name, search_tag=tag, lang=lang, session_key=sess_key, session_expiry=sess_exp, user_history=new_hist, is_local=is_local)
                self.wfile.write(rendered_html.encode("utf-8"))

            except RiotAPIError as e:
                self._send_html(render_home_html(error_msg=str(e), search_name=name, search_tag=tag, lang=lang))
            except Exception as e:
                self._send_html(render_home_html(error_msg=f"Erro: {e}", search_name=name, search_tag=tag, lang=lang))

        elif path == "/load_more":
            name = qs.get("game_name", [""])[0].strip()
            tag = qs.get("tag_line", [""])[0].strip()
            start_str = qs.get("start", ["0"])[0].strip()
            start_offset = int(start_str) if start_str.isdigit() else 0
            if not name or not tag:
                self._redirect(f"/?lang={lang}")
                return

            try:
                client = RiotClient(api_key=get_api_key(session_key=sess_key), lang=lang)
                puuid = client.get_puuid(name, tag)
                save_session(name, tag, puuid)
                match_ids = client.get_recent_matches(puuid, count=8, start=start_offset)
                
                dd = get_ddragon(lang)
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    list(executor.map(lambda mid: client.get_match_detail(mid, target_puuid=puuid), match_ids))

                self._send_html(render_home_html(search_name=name, search_tag=tag, lang=lang))

            except RiotAPIError as e:
                self._send_html(render_home_html(error_msg=str(e), search_name=name, search_tag=tag, lang=lang))
            except Exception as e:
                self._send_html(render_home_html(error_msg=f"Erro: {e}", search_name=name, search_tag=tag, lang=lang))

        elif path == "/analyze":

            match_id = qs.get("match_id", [""])[0].strip()
            puuid = qs.get("puuid", [""])[0].strip()
            if not match_id:
                self._redirect(f"/?lang={lang}")
                return

            try:
                client = RiotClient(api_key=get_api_key(session_key=sess_key), lang=lang)
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    f_match = executor.submit(client.get_match_detail, match_id)
                    f_timeline = executor.submit(client.get_match_timeline, match_id)
                    m = f_match.result()
                    t = f_timeline.result()
                
                if not puuid:
                    last_sess = get_last_session() or {}
                    puuid = last_sess.get("puuid")

                dd = get_ddragon(lang)
                
                # Dynamic hot reload during development
                import importlib
                import src.event_engine
                import src.html_report
                import src.i18n
                import src.report_components
                import src.report_components.duel_card
                import src.report_components.awards_card
                import src.report_components.multikill_card
                import src.report_components.timeline
                import src.report_components.jungle_strip
                import src.report_components.utils
                importlib.reload(src.i18n)
                importlib.reload(src.report_components.utils)
                importlib.reload(src.report_components.jungle_strip)
                importlib.reload(src.report_components.duel_card)
                importlib.reload(src.report_components.awards_card)
                importlib.reload(src.report_components.multikill_card)
                importlib.reload(src.report_components.timeline)
                importlib.reload(src.report_components)
                importlib.reload(src.event_engine)
                importlib.reload(src.html_report)

                analyzer = src.event_engine.MatchAnalysis(m, t, target_puuid=puuid, ddragon=dd)

                data = analyzer.generate_full_analysis()
                
                content = src.html_report.generate_html_report(data, open_browser=False, lang=lang)
                
                self._send_html(content)
            except (ConnectionError, BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass
            except Exception as e:
                err_text = get_text("err_analyze_match", lang=lang, match_id=match_id, err=str(e))
                self._send_html(render_home_html(error_msg=err_text, lang=lang))

        else:
            self._send_html(render_home_html(error_msg=get_text("err_page_not_found", lang=lang), lang=lang))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/save_key":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            form_data = parse_qs(body)
            new_key = form_data.get("api_key", [""])[0].strip()
            exp_text = form_data.get("expires_text", [""])[0].strip()
            lang = form_data.get("lang", ["pt_BR"])[0].strip() or "pt_BR"
            
            is_local = not is_production_mode()
            
            cookies_to_set = []
            if new_key:
                exp_ts = parse_expiry_str(exp_text) if exp_text else (int(time.time() + 24 * 3600))
                if is_local:
                    # In local development, safely update .env file
                    save_api_key(new_key, exp_text)
                else:
                    # On public/remote server, isolate key inside user's private cookies (never alter global .env)
                    cookies_to_set.append(f"blaze_dev_key={new_key}; Path=/; SameSite=Lax; Max-Age=86400")
                    cookies_to_set.append(f"blaze_dev_exp={exp_ts}; Path=/; SameSite=Lax; Max-Age=86400")
            
            self._redirect(f"/?lang={lang}", cookies=cookies_to_set)
        elif parsed.path == "/delete_summoner_cache":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            form_data = parse_qs(body)
            s_label = form_data.get("summoner_label", [""])[0].strip()
            lang = form_data.get("lang", ["pt_BR"])[0].strip() or "pt_BR"
            
            host_header = self.headers.get("Host", "").lower()
            x_forwarded_for = self.headers.get("X-Forwarded-For", "")
            is_local = not is_production_mode()
            
            cookies_raw = self.headers.get("Cookie", "")
            import http.cookies
            import urllib.parse
            cookie_obj = http.cookies.SimpleCookie()
            if cookies_raw:
                try:
                    cookie_obj.load(cookies_raw)
                except Exception:
                    pass
            hist_cookie = urllib.parse.unquote(cookie_obj.get("blaze_history").value) if "blaze_history" in cookie_obj else ""
            user_history = [h.strip() for h in hist_cookie.split("|") if h.strip()] if hist_cookie else []
            new_hist = [h for h in user_history if h.lower() != s_label.lower()]
            hist_cookie_val = urllib.parse.quote("|".join(new_hist))

            if s_label and is_local:
                from src.config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR
                from src.cache_manager import list_cache_files, load_json
                if MATCH_CACHE_DIR.exists():
                    for f in list_cache_files(MATCH_CACHE_DIR):
                        try:
                            data = load_json(f)
                            if not data:
                                continue
                            info = data.get("info", {})
                            meta = data.get("metadata", {})
                            target_puuid = meta.get("target_puuid", "")
                            
                            p_match = False
                            for part in info.get("participants", []):
                                p_label = f"{part.get('riotIdGameName', '')}#{part.get('riotIdTagline', '')}"
                                if target_puuid and part.get("puuid") == target_puuid:
                                    if p_label.lower() == s_label.lower():
                                        p_match = True
                                        break
                                elif not target_puuid and p_label.lower() == s_label.lower():
                                    p_match = True
                                    break
                            
                            if p_match:
                                m_id = meta.get("matchId", f.name.split(".")[0])
                                f.unlink(missing_ok=True)
                                if TIMELINE_CACHE_DIR.exists():
                                    (TIMELINE_CACHE_DIR / f"{m_id}.json").unlink(missing_ok=True)
                                    (TIMELINE_CACHE_DIR / f"{m_id}.json.gz").unlink(missing_ok=True)
                        except Exception:
                            continue
            
            del_cookie = [f"blaze_history={hist_cookie_val}; Path=/; SameSite=Lax; Max-Age=31536000"]
            self._redirect(f"/?lang={lang}", cookies=del_cookie)
        elif parsed.path == "/clear_cache":
            from src.config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR
            from src.cache_manager import list_cache_files
            for d in [MATCH_CACHE_DIR, TIMELINE_CACHE_DIR]:
                if d.exists():
                    for f in list_cache_files(d):
                        try:
                            f.unlink()
                        except Exception:
                            pass
            self._redirect("/")
        else:
            self._redirect("/")


    def _send_html(self, html_str: str):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(html_str.encode("utf-8"))
        except (ConnectionError, BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _redirect(self, url: str, cookies: list = None):
        self.send_response(302)
        self.send_header("Location", url)
        if cookies:
            for c in cookies:
                self.send_header("Set-Cookie", c)
        self.end_headers()

def run_app():
    # If watchdog process is not active, run with auto-reload
    if os.getenv("BLAZE_AUTO_RELOAD") != "1":
        import subprocess
        import sys
        import time

        url = f"http://127.0.0.1:{PORT}"
        print(f"\n==================================================")
        print(f"  🔥 Blaze GG Hub running at: {url}")
        print(f"  ⚡ Auto-Reloader ENABLED (code changes reload on refresh)")
        print(f"  Press Ctrl+C to stop.")
        print(f"==================================================\n")
        if not os.getenv("BLAZE_ENV") and not os.getenv("HEADLESS"):
            try:
                webbrowser.open(url)
            except Exception:
                pass

        env = os.environ.copy()
        env["BLAZE_AUTO_RELOAD"] = "1"

        watched_files = [Path(__file__)] + list((Path(__file__).parent / "src").glob("**/*"))
        last_mtimes = {str(f): f.stat().st_mtime for f in watched_files if f.is_file()}

        while True:
            proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve())], env=env)
            try:
                while proc.poll() is None:
                    time.sleep(0.5)
                    # Check file changes
                    changed = False
                    current_files = [Path(__file__)] + list((Path(__file__).parent / "src").glob("**/*"))
                    for f in current_files:
                        if f.is_file():
                            mtime = f.stat().st_mtime
                            if str(f) not in last_mtimes or mtime > last_mtimes[str(f)]:
                                last_mtimes[str(f)] = mtime
                                changed = True
                    if changed:
                        print("\n[⚡ Auto-Reloader] Change detected! Reloading server in background...")
                        proc.terminate()
                        proc.wait()
                        break
            except KeyboardInterrupt:
                proc.terminate()
                proc.wait()
                print("\nServer stopped.")
                break
    # Start background asset preloading to guarantee instant analysis without cold-start timeouts
    import threading
    from src.asset_cache import AssetManager
    threading.Thread(target=AssetManager.preload_all_assets, daemon=True).start()

    # Child server worker
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AppHandler)
    server.daemon_threads = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run_app()

