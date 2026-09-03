import os
import sys
import json
import webbrowser
import urllib.parse
from urllib.parse import urlparse, parse_qs
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import concurrent.futures
from pathlib import Path

from src.config import BASE_DIR, CACHE_DIR, MATCH_CACHE_DIR, get_key_expires_at, save_api_key, is_production_mode, parse_expiry_str
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

        id_hist_cookie = urllib.parse.unquote(cookie_obj.get("blaze_id_searches").value) if "blaze_id_searches" in cookie_obj else ""
        id_search_history = [h.strip() for h in id_hist_cookie.split("|") if h.strip()] if id_hist_cookie else []

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
            view_mode = qs.get("view", ["recent"])[0].strip().lower()
            self._send_html(render_home_html(lang=lang, session_key=sess_key, session_expiry=sess_exp, user_history=user_history, is_local=is_local, view_mode=view_mode, id_search_history=id_search_history))

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
                self._send_html(render_home_html(error_msg=err_msg, lang=lang, session_key=sess_key, session_expiry=sess_exp, user_history=user_history, is_local=is_local, id_search_history=id_search_history))
                return

            searched_riot_id = f"{name}#{tag}"
            # If the live fetch below fails (no/expired key, Riot API hiccup), still
            # show this summoner's tab with whatever is already cached for them —
            # for this render only, not persisted to the history cookie, since a typo'd
            # name that never resolves shouldn't permanently clutter search history.
            fallback_hist = user_history if searched_riot_id.lower() in [h.lower() for h in user_history] else user_history + [searched_riot_id]

            try:
                client = RiotClient(session_key=sess_key, lang=lang)
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
                
                rendered_html = render_home_html(search_results=results, search_name=name, search_tag=tag, lang=lang, session_key=sess_key, session_expiry=sess_exp, user_history=new_hist, is_local=is_local, id_search_history=id_search_history)
                self.wfile.write(rendered_html.encode("utf-8"))

            except RiotAPIError as e:
                self._send_html(render_home_html(error_msg=str(e), search_name=name, search_tag=tag, lang=lang, user_history=fallback_hist, is_local=is_local, id_search_history=id_search_history, auto_expand=True))
            except Exception as e:
                self._send_html(render_home_html(error_msg=f"Erro: {e}", search_name=name, search_tag=tag, lang=lang, user_history=fallback_hist, is_local=is_local, id_search_history=id_search_history, auto_expand=True))

        elif path == "/load_more":
            name = qs.get("game_name", [""])[0].strip()
            tag = qs.get("tag_line", [""])[0].strip()
            start_str = qs.get("start", ["0"])[0].strip()
            start_offset = int(start_str) if start_str.isdigit() else 0
            if not name or not tag:
                self._redirect(f"/?lang={lang}")
                return

            try:
                client = RiotClient(session_key=sess_key, lang=lang)
                puuid = client.get_puuid(name, tag)
                save_session(name, tag, puuid)
                match_ids = client.get_recent_matches(puuid, count=8, start=start_offset)

                dd = get_ddragon(lang)
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    list(executor.map(lambda mid: client.get_match_detail(mid, target_puuid=puuid), match_ids))

                self._send_html(render_home_html(search_name=name, search_tag=tag, lang=lang, auto_expand=True, user_history=user_history, is_local=is_local, id_search_history=id_search_history))

            except RiotAPIError as e:
                self._send_html(render_home_html(error_msg=str(e), search_name=name, search_tag=tag, lang=lang, user_history=user_history, is_local=is_local, id_search_history=id_search_history))
            except Exception as e:
                self._send_html(render_home_html(error_msg=f"Erro: {e}", search_name=name, search_tag=tag, lang=lang, user_history=user_history, is_local=is_local, id_search_history=id_search_history))

        elif path == "/analyze":

            match_id = qs.get("match_id", [""])[0].strip()
            puuid = qs.get("puuid", [""])[0].strip()
            if not match_id:
                self._redirect(f"/?lang={lang}")
                return

            # No puuid in the URL means this came from a raw match-ID search
            # (/search_match), not from clicking a hub card (which always carries
            # one) — that's the one case worth remembering as an "ID search".
            is_raw_id_search = not puuid

            try:
                # If both files are already on disk, skip the Riot API (and the
                # RiotClient it would need) entirely — a cached match should never
                # fail just because there's no valid key configured right now.
                from src.cache_manager import get_cached_match, get_cached_timeline
                m = get_cached_match(match_id)
                t = get_cached_timeline(match_id)
                if not (m and t):
                    client = RiotClient(session_key=sess_key, lang=lang)
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

                cookies_out = None
                if is_raw_id_search:
                    new_id_hist = [h for h in id_search_history if h.lower() != match_id.lower()]
                    new_id_hist.insert(0, match_id)
                    new_id_hist = new_id_hist[:10]
                    id_cookie_val = urllib.parse.quote("|".join(new_id_hist))
                    cookies_out = [f"blaze_id_searches={id_cookie_val}; Path=/; SameSite=Lax; Max-Age=31536000"]

                self._send_html(content, cookies=cookies_out)
            except (ConnectionError, BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass
            except Exception as e:
                err_text = get_text("err_analyze_match", lang=lang, match_id=match_id, err=str(e))
                self._send_html(render_home_html(error_msg=err_text, lang=lang, user_history=user_history, is_local=is_local, id_search_history=id_search_history))

        else:
            self._send_html(render_home_html(error_msg=get_text("err_page_not_found", lang=lang), lang=lang, user_history=user_history, is_local=is_local, id_search_history=id_search_history))

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
            view_mode = form_data.get("view", ["recent"])[0].strip() or "recent"
            is_global = form_data.get("is_global", ["0"])[0].strip() == "1"

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

            id_hist_cookie = urllib.parse.unquote(cookie_obj.get("blaze_id_searches").value) if "blaze_id_searches" in cookie_obj else ""
            id_search_history = [h.strip() for h in id_hist_cookie.split("|") if h.strip()] if id_hist_cookie else []
            id_search_lower = set(h.lower() for h in id_search_history)
            # In "recent" view the ID Searches tab only shows matches this browser's
            # cookie tracked, so deleting it should only remove those, not every
            # ID-searched match on disk (that full wipe is what "cached" view is for).
            scope_to_cookie = is_global and view_mode != "cached"
            deleted_match_ids = []

            if s_label and is_local:
                from src.config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR
                from src.cache_manager import list_cache_files, load_json

                last_sess = get_last_session() or {}
                last_sess_puuid = last_sess.get("puuid", "")

                if MATCH_CACHE_DIR.exists():
                    for f in list_cache_files(MATCH_CACHE_DIR):
                        try:
                            data = load_json(f)
                            if not data:
                                continue
                            info = data.get("info", {})
                            meta = data.get("metadata", {})
                            target_puuid = meta.get("target_puuid", "")
                            participants = info.get("participants", [])

                            if is_global:
                                p_match = (not target_puuid) and not any(
                                    f"{part.get('riotIdGameName', '')}#{part.get('riotIdTagline', '')}".lower() in
                                    [h.lower() for h in user_history]
                                    or (last_sess_puuid and part.get("puuid") == last_sess_puuid)
                                    for part in participants
                                )
                                if p_match and scope_to_cookie:
                                    this_m_id = meta.get("matchId", f.name.split(".")[0])
                                    p_match = this_m_id.lower() in id_search_lower
                            else:
                                # Match by actual participant identity, never by target_puuid
                                # alone — target_puuid only ever records whoever got this match
                                # cached first, so relying on it here would (a) miss deleting a
                                # match for a summoner who isn't that recorded owner and (b), far
                                # worse, delete it out from under a DIFFERENT summoner's tab that
                                # still needs it (see the recent duo-partner bug).
                                p_match = any(
                                    f"{part.get('riotIdGameName', '')}#{part.get('riotIdTagline', '')}".lower() == s_label.lower()
                                    for part in participants
                                )
                                if p_match:
                                    # Orphan check: this match is only actually deleted once no
                                    # OTHER summoner still tracked (post-deletion history, or the
                                    # active local session) also played in it. Deleting one tab
                                    # must never punch a hole in another tab that still shows it.
                                    still_needed_elsewhere = any(
                                        f"{part.get('riotIdGameName', '')}#{part.get('riotIdTagline', '')}".lower() in
                                        [h.lower() for h in new_hist]
                                        or (last_sess_puuid and part.get("puuid") == last_sess_puuid)
                                        for part in participants
                                    )
                                    if still_needed_elsewhere:
                                        p_match = False

                            if p_match:
                                m_id = meta.get("matchId", f.name.split(".")[0])
                                deleted_match_ids.append(m_id.lower())
                                f.unlink(missing_ok=True)
                                if TIMELINE_CACHE_DIR.exists():
                                    (TIMELINE_CACHE_DIR / f"{m_id}.json").unlink(missing_ok=True)
                                    (TIMELINE_CACHE_DIR / f"{m_id}.json.gz").unlink(missing_ok=True)
                                    (TIMELINE_CACHE_DIR / f"{m_id}.json.xz").unlink(missing_ok=True)
                        except Exception:
                            continue

            del_cookie = [f"blaze_history={hist_cookie_val}; Path=/; SameSite=Lax; Max-Age=31536000"]
            if deleted_match_ids:
                new_id_hist = [h for h in id_search_history if h.lower() not in deleted_match_ids]
                del_cookie.append(f"blaze_id_searches={urllib.parse.quote('|'.join(new_id_hist))}; Path=/; SameSite=Lax; Max-Age=31536000")
            redirect_url = f"/?lang={lang}" + (f"&view={view_mode}" if view_mode == "cached" else "")
            self._redirect(redirect_url, cookies=del_cookie)
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


    def _send_html(self, html_str: str, cookies: list = None):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            if cookies:
                for c in cookies:
                    self.send_header("Set-Cookie", c)
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

def _port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

def _find_pid_on_port(port: int):
    import subprocess
    try:
        out = subprocess.check_output("netstat -ano -p TCP", shell=True, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3] == "LISTENING":
            return parts[-1]
    return None

def _kill_pid_tree(pid: str) -> bool:
    import subprocess
    try:
        # Only kill it if it's actually a python process — never nuke something
        # unrelated that just happened to be holding the port.
        check = subprocess.check_output(f'tasklist /FI "PID eq {pid}"', shell=True, text=True, stderr=subprocess.DEVNULL)
        if "python" not in check.lower():
            return False
        subprocess.run(["taskkill", "/F", "/PID", pid, "/T"], capture_output=True)
        return True
    except Exception:
        return False

def _supports_emoji() -> bool:
    # Classic cmd.exe (conhost) often can't render emoji glyphs even once the
    # UTF-8 codepage is set — only bother on terminals known to handle them:
    # Windows Terminal, VS Code's integrated terminal, and anything non-Windows.
    if sys.platform != "win32":
        return True
    return bool(os.getenv("WT_SESSION") or os.getenv("TERM_PROGRAM"))

def run_app():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    emoji = _supports_emoji()
    fire = "🔥" if emoji else "[i]"
    bolt = "⚡" if emoji else "->"
    # If watchdog process is not active, run with auto-reload
    if os.getenv("BLAZE_AUTO_RELOAD") != "1":
        import subprocess
        import time

        url = f"http://127.0.0.1:{PORT}"

        if _port_in_use(PORT):
            print(f"\n==================================================")
            print(f"  {fire} Blaze GG Hub is already running at: {url}")
            print(f"==================================================\n")
            answer = ""
            if not os.getenv("BLAZE_ENV") and not os.getenv("HEADLESS") and sys.stdin.isatty():
                try:
                    answer = input("  Kill it and start a fresh instance? [y/N]: ").strip().lower()
                except Exception:
                    answer = ""
            if answer == "y":
                pid = _find_pid_on_port(PORT)
                killed = pid and _kill_pid_tree(pid)
                if killed:
                    print(f"  Killed the old instance (PID {pid}). Starting fresh...\n")
                    for _ in range(20):
                        if not _port_in_use(PORT):
                            break
                        time.sleep(0.2)
                else:
                    print("  Couldn't confirm it was safe to kill — leaving it running.\n")
                    if not os.getenv("BLAZE_ENV") and not os.getenv("HEADLESS"):
                        try:
                            webbrowser.open(url)
                        except Exception:
                            pass
                    return
            else:
                print("  Opening it in your browser instead of starting a second copy.\n")
                if not os.getenv("BLAZE_ENV") and not os.getenv("HEADLESS"):
                    try:
                        webbrowser.open(url)
                    except Exception:
                        pass
                return

        print(f"\n==================================================")
        print(f"  {fire} Blaze GG Hub running at: {url}")
        print(f"  {bolt} Auto-Reloader ENABLED (code changes reload on refresh)")
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
                        print(f"\n[{bolt} Auto-Reloader] Change detected! Reloading server in background...")
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

