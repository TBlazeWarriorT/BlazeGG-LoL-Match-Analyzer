import os
import json
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from src.config import BASE_DIR, CACHE_DIR, MATCH_CACHE_DIR, get_api_key, get_key_expires_at, save_api_key
from src.riot_client import RiotClient, RiotAPIError
from src.cache_manager import set_last_viewed, get_last_viewed, save_session, get_last_session
from src.event_engine import MatchAnalysis
from src.ddragon import DataDragon
from src.i18n import get_text

PORT = 8000
HUB_CSS_FILE = Path(__file__).parent / "src" / "static" / "css" / "hub.css"
HUB_JS_FILE = Path(__file__).parent / "src" / "static" / "js" / "report.js"
ddragon = DataDragon(language="pt_BR")
ddragon_en = DataDragon(language="en_US")

def get_ddragon(lang: str = "pt_BR") -> DataDragon:
    return ddragon_en if lang == "en_US" else ddragon

def format_relative_time(creation_ms: int, lang: str = "pt_BR") -> str:
    import time
    if not creation_ms or creation_ms == 0:
        return ""
    diff_s = int(time.time() - (creation_ms / 1000))
    if diff_s < 60:
        return "agora mesmo" if lang == "pt_BR" else "just now"
    elif diff_s < 3600:
        m = diff_s // 60
        return f"há {m} min" if lang == "pt_BR" else f"{m}m ago"
    elif diff_s < 86400:
        h = diff_s // 3600
        return f"há {h} hora{'s' if h > 1 else ''}" if lang == "pt_BR" else f"{h}h ago"
    elif diff_s < 604800:
        d = diff_s // 86400
        return f"há {d} dia{'s' if d > 1 else ''}" if lang == "pt_BR" else f"{d}d ago"
    else:
        from datetime import datetime
        return datetime.fromtimestamp(creation_ms / 1000).strftime("%d/%m/%Y")

def get_cached_matches_list(lang: str = "pt_BR"):
    matches = []
    if not MATCH_CACHE_DIR.exists():
        return matches
    dd = get_ddragon(lang)
    for f in MATCH_CACHE_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                info = data.get("info", {})
                meta = data.get("metadata", {})
                mid = meta.get("matchId", f.stem)
                dur_s = info.get("gameDuration", 0)
                creation_ms = info.get("gameCreation", 0)
                target_puuid = meta.get("target_puuid", "")
                parts = []
                t1_parts = []
                t2_parts = []



                for p in info.get("participants", []):
                    raw_champ = p.get("championName", "")
                    part_dict = {
                        "name": p.get("riotIdGameName", ""),
                        "tag": p.get("riotIdTagline", ""),
                        "champion": dd.get_clean_champion_name(raw_champ),
                        "icon": dd.get_champion_icon_url(raw_champ),
                        "kda": f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
                        "win": p.get("win", False),
                        "placement": p.get("subteamPlacement") or p.get("placement") or p.get("challenges", {}).get("placement", 0),
                        "puuid": p.get("puuid"),
                        "team_id": p.get("teamId", 100),
                        "role": p.get("teamPosition") or p.get("individualPosition", "UNKNOWN")
                    }
                    parts.append(part_dict)
                    if p.get("teamId", 100) == 100:
                        t1_parts.append(part_dict)
                    else:
                        t2_parts.append(part_dict)


                matches.append({
                    "match_id": mid,
                    "game_mode": info.get("gameMode", "CLASSIC"),
                    "queue_id": info.get("queueId", 0),
                    "duration": f"{dur_s // 60}m {dur_s % 60}s",
                    "creation_ms": creation_ms,
                    "relative_time": format_relative_time(creation_ms, lang=lang),
                    "target_puuid": target_puuid,
                    "participants": parts,
                    "team_100": t1_parts,
                    "team_200": t2_parts
                })
        except Exception:
            continue
    matches.sort(key=lambda x: x.get("creation_ms", 0), reverse=True)
    return matches

def clean_game_mode(mode: str, queue_id: int = 0, lang: str = "en_US") -> str:
    m = str(mode).upper()
    mode_name = "Summoner's Rift" if m == "CLASSIC" else ("ARAM" if m == "ARAM" else ("Arena" if m == "CHERRY" else ("URF" if m == "URF" else m.capitalize())))
    queue_map = {
        420: "queue_ranked_solo",
        440: "queue_ranked_flex",
        400: "queue_normal_draft",
        430: "queue_normal_blind",
        450: "queue_aram",
        1700: "queue_arena",
        900: "queue_urf",
        1010: "queue_urf",
        1020: "queue_one_for_all",
        1900: "queue_urf"
    }
    q_key = queue_map.get(queue_id, "")
    q_name = get_text(q_key, lang=lang) if q_key else ""
    return f"{mode_name} ({q_name})" if q_name else mode_name

def render_match_card(m_id, champ_name, champ_icon, riot_id, kda, win, duration, mode, puuid, rel_time="", is_cached=False, lang="en_US", queue_id=0, team_100=None, team_200=None, placement=0):
    m_upper = str(mode).upper()
    is_arena = ("CHERRY" in m_upper or "ARENA" in m_upper or queue_id == 1700)
    
    # In Arena: top 50% is considered a win (e.g. 1st-4th in 8-team 2v2v2v2 or 1st-2nd/3rd in 3v3v3v3)
    if is_arena and placement:
        is_effective_win = placement <= 4 if queue_id == 1700 or placement <= 8 else win
        place_suffix = f" (#{placement})"
        win_class = "card-win" if is_effective_win else "card-loss"
        badge_class = "badge-win" if is_effective_win else "badge-loss"
        
        ord_suffix = {1: "ST", 2: "ND", 3: "RD"}.get(placement, "TH")
        if is_effective_win:
            win_txt = f"👑 {placement}º LUGAR" if lang == "pt_BR" else f"👑 {placement}{ord_suffix} PLACE"
        else:
            win_txt = f"🪦 {placement}º LUGAR" if lang == "pt_BR" else f"🪦 {placement}{ord_suffix} PLACE"
    else:
        win_class = "card-win" if win else "card-loss"
        win_txt = get_text("win", lang=lang) if win else get_text("loss", lang=lang)
        badge_class = "badge-win" if win else "badge-loss"

    btn_text = get_text("btn_cached", lang=lang) if is_cached else get_text("btn_analyze", lang=lang)
    btn_class = "btn-analyze btn-cached" if is_cached else "btn-analyze"
    time_badge = f'<span style="color:#64748b; font-size:0.78rem; margin-left:6px;">• {rel_time}</span>' if rel_time else ""

    parts = riot_id.split("#") if "#" in riot_id else [riot_id, ""]
    g_name, t_line = parts[0], parts[1]
    search_link = f"/search?game_name={g_name}&tag_line={t_line}&lang={lang}" if t_line else "#"

    # Find lane opponent only in Summoner's Rift (CLASSIC)
    is_classic = (m_upper == "CLASSIC" or queue_id in (420, 440, 400, 430))
    opp_champ = None
    target_part = None

    if is_classic:
        all_parts = (team_100 or []) + (team_200 or [])
        for p in all_parts:
            if p.get("puuid") == puuid:
                target_part = p
                break

        if target_part:
            t_role = target_part.get("role")
            t_team = target_part.get("team_id")
            opp_team = team_200 if t_team == 100 else team_100
            for opp in (opp_team or []):
                if opp.get("puuid") != target_part.get("puuid") and opp.get("role") == t_role and t_role not in ("UNKNOWN", "", None):
                    opp_champ = opp
                    break

    avatar_block = f'<img class="champ-avatar-lg" src="{champ_icon}" alt="{champ_name}" title="{champ_name} ({riot_id})" onclick="promptSearchSummoner(\'{g_name}\', \'{t_line}\')"/>'
    if opp_champ:
        opp_gname = opp_champ.get('name', '')
        opp_tline = opp_champ.get('tag', '')
        opp_riot = f"{opp_gname}#{opp_tline}"
        opp_title = f"Oponente Direto: {opp_champ['champion']} ({opp_riot})" if lang == "pt_BR" else f"Direct Opponent: {opp_champ['champion']} ({opp_riot})"
        avatar_block = f"""
        <div class="h2h-avatar-duo">
            <img class="champ-avatar-lg" src="{champ_icon}" alt="{champ_name}" title="{champ_name} ({riot_id})" onclick="promptSearchSummoner(\'{g_name}\', \'{t_line}\')"/>
            <span class="h2h-vs-badge">VS</span>
            <img class="champ-avatar-opp" src="{opp_champ['icon']}" alt="{opp_champ['champion']}" title="{opp_title}" onclick="promptSearchSummoner(\'{opp_gname}\', \'{opp_tline}\')"/>
        </div>
        """

    teams_html = ""
    if team_100 and team_200:
        t1_icons = "".join([f'<img class="m-mini-champ" src="{p["icon"]}" title="{p["champion"]} ({p["name"]})" alt="{p["champion"]}" onclick="promptSearchSummoner(\'{p.get("name", "")}\', \'{p.get("tag", "")}\')"/>' for p in team_100])
        t2_icons = "".join([f'<img class="m-mini-champ" src="{p["icon"]}" title="{p["champion"]} ({p["name"]})" alt="{p["champion"]}" onclick="promptSearchSummoner(\'{p.get("name", "")}\', \'{p.get("tag", "")}\')"/>' for p in team_200])
        teams_html = f"""
        <div class="m-teams-strip">
            <div class="m-team-group m-team-blue">{t1_icons}</div>
            <span class="m-vs-text">vs</span>
            <div class="m-team-group m-team-red">{t2_icons}</div>
        </div>
        """


    return f"""
    <div class="match-item {win_class}">
        <div class="m-left">
            {avatar_block}
            <div>
                <div class="m-champ-name">
                    {champ_name} 
                    <a href="{search_link}" class="summoner-link" title="Buscar partidas">({riot_id})</a>
                </div>
                <div class="m-sub">{clean_game_mode(mode, queue_id=queue_id, lang=lang)} • {duration} {time_badge} • KDA: <b>{kda}</b></div>
            </div>
        </div>
        <div class="m-right">
            {teams_html}
            <div class="m-actions-row">
                <span class="m-badge {badge_class}">{win_txt}</span>
                <a class="{btn_class}" href="/analyze?match_id={m_id}&puuid={puuid}&lang={lang}">{btn_text}</a>
            </div>
        </div>
    </div>
    """




def render_home_html(search_results=None, error_msg="", search_name="", search_tag="", lang="pt_BR"):
    cached_list = get_cached_matches_list(lang=lang)
    last_sess = get_last_session() or {}
    def_name = search_name or last_sess.get("game_name", "Noob Master 46")
    def_tag = search_tag or last_sess.get("tag_line", "CWB")
    
    curr_key = get_api_key()
    exp_val = get_key_expires_at()
    key_configured = bool(curr_key)
    
    import time
    expiry_msg = ""
    is_expired = False
    
    if key_configured:
        masked_key = f"{curr_key[:6]}...{curr_key[-4:]}" if len(curr_key) > 10 else "******"
        if exp_val and str(exp_val).isdigit():
            exp_ts = int(exp_val)
            diff_s = exp_ts - time.time()
            if diff_s <= 0:
                is_expired = True
                expiry_msg = get_text("key_status_expired", lang=lang)
                key_status_badge = f'<span style="color:#fca5a5; background:#991b1b; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_expired", lang=lang, masked=masked_key)}</span>'
            else:
                hours = int(diff_s // 3600)
                mins = int((diff_s % 3600) // 60)
                expiry_msg = get_text("key_status_valid", lang=lang, hours=hours, mins=mins)
                key_status_badge = f'<span style="color:#86efac; background:#166534; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_active", lang=lang, masked=masked_key, hours=hours, mins=mins)}</span>'
        else:
            expiry_msg = get_text("key_status_no_info", lang=lang)
            key_status_badge = f'<span style="color:#86efac; background:#166534; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_active_no_exp", lang=lang, masked=masked_key)}</span>'
    else:
        masked_key = "Nenhuma" if lang == "pt_BR" else "None"
        expiry_msg = get_text("key_status_none", lang=lang)
        key_status_badge = f'<span style="color:#fca5a5; background:#991b1b; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_missing", lang=lang)}</span>'

    cached_html = ""
    if cached_list:
        # Group cached matches by target summoner
        summoner_groups = {}
        for m in cached_list:
            p = None
            if m.get("target_puuid"):
                for part in m["participants"]:
                    if part["puuid"] == m["target_puuid"]:
                        p = part
                        break
            if not p and last_sess.get("puuid"):
                for part in m["participants"]:
                    if part["puuid"] == last_sess.get("puuid"):
                        p = part
                        break
            if not p:
                p = m["participants"][0] if m["participants"] else {}

            card_html = render_match_card(
                m["match_id"], p.get("champion", ""), p.get("icon", ""),
                f"{p.get('name', '')}#{p.get('tag', '')}", p.get("kda", ""),
                p.get("win", False), m["duration"], m["game_mode"],
                p.get("puuid", ""), rel_time=m.get("relative_time", ""), is_cached=True, lang=lang, queue_id=m.get("queue_id", 0),
                team_100=m.get("team_100"), team_200=m.get("team_200"), placement=p.get("placement", 0)
            )

            s_name = p.get("name", "")
            s_tag = p.get("tag", "")
            s_label = f"{s_name}#{s_tag}" if (s_name and s_tag) else ("Global / Diversos" if lang == "pt_BR" else "Global / Other")
            summoner_groups.setdefault(s_label, []).append(card_html)

        # Build tabs
        tab_buttons = []
        tab_panes = []
        sorted_groups = sorted(summoner_groups.items(), key=lambda x: len(x[1]), reverse=True)
        
        # Decide initial active tab (prefer search summoner, then session summoner, then highest count)
        searched_label = f"{search_name}#{search_tag}" if (search_name and search_tag) else ""
        sess_label = f"{last_sess.get('game_name', '')}#{last_sess.get('tag_line', '')}"
        target_focus = searched_label or sess_label

        active_tab_idx = 0
        for idx, (label, _) in enumerate(sorted_groups):
            if label.lower() == target_focus.lower():
                active_tab_idx = idx
                break

        del_prompt = "Excluir todas as partidas salvas deste invocador?" if lang == "pt_BR" else "Delete all saved matches for this summoner?"
        for idx, (s_label, cards_list) in enumerate(sorted_groups):
            is_active = (idx == active_tab_idx)
            btn_active_cls = "active" if is_active else ""
            pane_active_cls = "active" if is_active else ""
            tab_id = f"cache-tab-{idx}"

            # Format cards: first 8 visible, remaining with .match-hidden
            formatted_cards = []
            for c_idx, card_str in enumerate(cards_list):
                if c_idx >= 8:
                    card_str = card_str.replace('class="match-item ', 'class="match-item match-hidden ', 1)
                formatted_cards.append(card_str)

            # Actions bar (Show more / Show less and Load More from Riot API)
            actions_html = ""
            expand_btn = ""
            if len(cards_list) > 8:
                rem_count = len(cards_list) - 8
                lbl_show_more = get_text("show_more_matches", lang=lang, count=rem_count)
                expand_btn = f"""
                <button type="button" class="btn-tab-action" id="expand-btn-{idx}" onclick="toggleTabMatches({idx}, {len(cards_list)})">
                    <span>▼ {lbl_show_more}</span>
                </button>
                """

            # Parse game_name and tag_line for refresh & load more
            load_more_btn = ""
            refresh_btn = ""
            if "#" in s_label:
                parts = s_label.split("#")
                g_n, t_l = parts[0], parts[1]
                
                lbl_refresh = get_text("btn_refresh_summoner", lang=lang)
                refresh_btn = f"""
                <form action="/search" method="GET" style="margin:0; display:inline;">
                    <input type="hidden" name="game_name" value="{g_n}"/>
                    <input type="hidden" name="tag_line" value="{t_l}"/>
                    <input type="hidden" name="lang" value="{lang}"/>
                    <button type="submit" class="btn-tab-action btn-tab-refresh" onclick="this.innerText='{get_text('refreshing_btn', lang=lang)}';">
                        <span>{lbl_refresh}</span>
                    </button>
                </form>
                """

                lbl_load_more = get_text("btn_load_more", lang=lang)
                load_more_btn = f"""
                <form action="/load_more" method="GET" style="margin:0; display:inline;">
                    <input type="hidden" name="game_name" value="{g_n}"/>
                    <input type="hidden" name="tag_line" value="{t_l}"/>
                    <input type="hidden" name="start" value="{len(cards_list)}"/>
                    <input type="hidden" name="lang" value="{lang}"/>
                    <button type="submit" class="btn-tab-action btn-tab-load-more" onclick="this.innerText='{get_text('loading_more_btn', lang=lang)}';">
                        <span>⬇️ {lbl_load_more}</span>
                    </button>
                </form>
                """

            if expand_btn or load_more_btn or refresh_btn:
                actions_html = f"""
                <div class="tab-actions-bar">
                    {expand_btn}
                    {refresh_btn}
                    {load_more_btn}
                </div>
                """

            tab_buttons.append(f"""
            <div class="cache-tab-btn {btn_active_cls}" onclick="switchCacheTab({idx})">
                <span>{s_label}</span>
                <span class="cache-tab-count">{len(cards_list)}</span>
                <form action="/delete_summoner_cache" method="POST" style="display:inline; margin:0;" onsubmit="event.stopPropagation(); return confirm('{del_prompt}');">
                    <input type="hidden" name="summoner_label" value="{s_label}"/>
                    <input type="hidden" name="lang" value="{lang}"/>
                    <button type="submit" class="cache-tab-delete" title="Excluir partidas deste invocador" style="background:none; border:none; cursor:pointer;" onclick="event.stopPropagation();">✕</button>
                </form>
            </div>
            """)

            tab_panes.append(f"""
            <div id="{tab_id}" class="cache-tab-content {pane_active_cls}">
                {"".join(formatted_cards)}
                {actions_html}
            </div>
            """)


        c_title = get_text("cached_matches_title", lang=lang, count=len(cached_list))
        cached_html = f"""
        <div class="section-card" style="margin-top: 24px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0;">{c_title}</h3>
                <form action="/clear_cache" method="POST" onsubmit="return confirm('{get_text('confirm_clear_cache', lang=lang)}');">
                    <button type="submit" class="btn btn-clear-cache">{get_text('btn_clear_cache', lang=lang)}</button>
                </form>
            </div>
            
            <div class="cache-tabs-nav">
                {"".join(tab_buttons)}
            </div>

            <div class="cache-tabs-container">
                {"".join(tab_panes)}
            </div>
        </div>
        """



    error_html = f'<div class="error-banner">{error_msg}</div>' if error_msg else ""

    hub_css = HUB_CSS_FILE.read_text(encoding="utf-8") if HUB_CSS_FILE.exists() else ""
    hub_js = HUB_JS_FILE.read_text(encoding="utf-8") if HUB_JS_FILE.exists() else ""

    return f"""<!DOCTYPE html>
<html lang="{ 'pt-BR' if lang == 'pt_BR' else 'en' }">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1100">
    <title>Blaze GG - LoL Analytics</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔥</text></svg>">
    <style>
{hub_css}
    </style>
</head>
<body>
    <div class="lang-picker">
        <a href="/?lang=en_US" class="{'lang-btn active' if lang=='en_US' else 'lang-btn'}" title="English (US)">
            <img class="flag-icon" src="https://flagcdn.com/w40/us.png" alt="US Flag"/> EN
        </a>
        <a href="/?lang=pt_BR" class="{'lang-btn active' if lang=='pt_BR' else 'lang-btn'}" title="Português (Brasil)">
            <img class="flag-icon" src="https://flagcdn.com/w40/br.png" alt="BR Flag"/> PT
        </a>
    </div>

    <div class="container">
        <div class="header">
            <div>
                <a href="/?lang={lang}" style="text-decoration:none;" title="Voltar ao início">
                    <h1 class="logo-title" style="font-size:1.8rem; font-weight:900; letter-spacing:0.5px; margin:0; display:inline-block; cursor:pointer;">🔥 Blaze GG</h1>
                </a>
                <div style="color: var(--text-muted); margin-top: 4px; font-size:0.95rem;">{get_text('app_sub', lang=lang)}</div>
            </div>
            <div>{key_status_badge}</div>
        </div>


        {error_html}

        <!-- BUSCADORES (INVOCADOR & MATCH ID) -->
        <div style="display:grid; grid-template-columns: 1.6fr 1fr; gap:16px;">
            <!-- BUSCADOR DE INVOCADOR -->
            <div class="section-card">
                <h3 style="margin-top:0;">{get_text('search_title', lang=lang)}</h3>
                <form action="/search" method="GET" class="form-row">
                    <input type="hidden" name="lang" value="{lang}"/>
                    <input type="text" name="game_name" placeholder="{get_text('search_game_name_ph', lang=lang)}" value="{def_name}" required style="flex: 2;"/>
                    <span style="color:#64748b; font-weight:800; font-size:1.3rem; margin:0 2px;">#</span>
                    <input type="text" name="tag_line" placeholder="{get_text('search_tag_ph', lang=lang)}" value="{def_tag}" required style="flex: 1; max-width: 130px;"/>
                    <button type="submit" class="btn" id="btnSearch" onclick="this.innerText='{get_text('searching_btn', lang=lang)}';">{get_text('search_btn', lang=lang)}</button>
                </form>
            </div>

            <!-- BUSCADOR DE MATCH ID -->
            <div class="section-card">
                <h3 style="margin-top:0;">{get_text('search_match_id_title', lang=lang)}</h3>
                <form action="/search_match" method="GET" class="form-row">
                    <input type="hidden" name="lang" value="{lang}"/>
                    <input type="text" name="match_id" placeholder="{get_text('search_match_id_ph', lang=lang)}" required style="flex: 1;"/>
                    <button type="submit" class="btn" style="background:#0284c7;">{get_text('search_match_id_btn', lang=lang)}</button>
                </form>
            </div>
        </div>

        {cached_html}



        <!-- CONFIGURAR API KEY -->
        <div class="section-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0;">{get_text('key_config_title', lang=lang)}</h3>
                <a href="https://developer.riotgames.com" target="_blank" style="color:var(--accent); font-size:0.85rem; font-weight:700; text-decoration:none;">{get_text('key_portal_link', lang=lang)}</a>
            </div>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin: 8px 0 14px 0;">
                {get_text('key_current', lang=lang, masked=masked_key, status=expiry_msg)}
            </p>
            <form action="/save_key" method="POST" style="display:flex; flex-direction:column; gap:12px;">
                <input type="hidden" name="lang" value="{lang}"/>
                <div style="display:flex; gap:12px; flex-wrap:wrap;">
                    <div class="form-group" style="flex: 1.2;">
                        <label class="form-label">{get_text('key_label', lang=lang)}</label>
                        <input type="password" name="api_key" placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" required/>
                    </div>
                    <div class="form-group" style="flex: 1.8;">
                        <label class="form-label">{get_text('key_exp_label', lang=lang)}</label>
                        <input type="text" name="expires_text" placeholder="Ex: Expires: Wed, Aug 26th, 2026 @ 9:57pm (PT) in 21 hours and 26 minutes"/>
                    </div>
                </div>
                <div>
                    <button type="submit" class="btn" style="background:#16a34a;">{get_text('btn_save_config', lang=lang)}</button>
                </div>
            </form>
        </div>

        <div class="legal-footer">
            Blaze.gg isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
        </div>
    </div>
    <script>
        {hub_js}
    </script>
</body>
</html>
"""


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
        lang = qs.get("lang", ["en_US"])[0].strip() or "en_US"

        if path in ("", "/"):
            self._send_html(render_home_html(lang=lang))

        elif path == "/search_match":
            mid_input = qs.get("match_id", [""])[0].strip()
            if not mid_input:
                self._redirect(f"/?lang={lang}")
                return
            
            # Format clean match_id
            match_id = mid_input.upper()
            if not match_id.startswith(("BR1_", "NA1_", "EUW1_", "KR_")) and match_id.isdigit():
                match_id = f"BR1_{match_id}"
            
            last_sess = get_last_session() or {}
            puuid = last_sess.get("puuid", "")
            self._redirect(f"/analyze?match_id={match_id}&puuid={puuid}&lang={lang}")
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
                err_msg = "Informe o Nome e a Tag do jogador." if lang == "pt_BR" else "Please provide Game Name and Tag."
                self._send_html(render_home_html(error_msg=err_msg, lang=lang))
                return

            try:
                client = RiotClient(lang=lang)
                puuid = client.get_puuid(name, tag)
                save_session(name, tag, puuid)
                match_ids = client.get_recent_matches(puuid, count=8)
                
                dd = get_ddragon(lang)
                results = []
                for mid in match_ids:
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
                        results.append({
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
                        })
                    except Exception:
                        continue

                self._send_html(render_home_html(search_results=results, search_name=name, search_tag=tag, lang=lang))

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
                client = RiotClient(lang=lang)
                puuid = client.get_puuid(name, tag)
                save_session(name, tag, puuid)
                match_ids = client.get_recent_matches(puuid, count=8, start=start_offset)
                
                dd = get_ddragon(lang)
                for mid in match_ids:
                    try:
                        client.get_match_detail(mid, target_puuid=puuid)
                    except Exception:
                        continue

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
                client = RiotClient(lang=lang)
                m = client.get_match_detail(match_id)
                t = client.get_match_timeline(match_id)
                
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
                
                src.html_report.generate_html_report(data, open_browser=False, lang=lang)
                
                with open(src.html_report.REPORT_FILE, "r", encoding="utf-8") as rf:
                    content = rf.read()
                
                self._send_html(content)
            except Exception as e:
                self._send_html(render_home_html(error_msg=f"Erro ao analisar {match_id}: {e}", lang=lang))

        else:
            self._send_html(render_home_html(error_msg="Página não encontrada.", lang=lang))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/save_key":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            form_data = parse_qs(body)
            new_key = form_data.get("api_key", [""])[0].strip()
            exp_text = form_data.get("expires_text", [""])[0].strip()
            lang = form_data.get("lang", ["pt_BR"])[0].strip() or "pt_BR"
            if new_key:
                save_api_key(new_key, exp_text)
            self._redirect(f"/?lang={lang}")
        elif parsed.path == "/delete_summoner_cache":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            form_data = parse_qs(body)
            s_label = form_data.get("summoner_label", [""])[0].strip()
            lang = form_data.get("lang", ["pt_BR"])[0].strip() or "pt_BR"
            
            if s_label:
                from src.config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR
                if MATCH_CACHE_DIR.exists():
                    for f in MATCH_CACHE_DIR.glob("*.json"):
                        try:
                            with open(f, "r", encoding="utf-8") as file:
                                data = json.load(file)
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
                                m_id = meta.get("matchId", f.stem)
                                f.unlink(missing_ok=True)
                                if TIMELINE_CACHE_DIR.exists():
                                    (TIMELINE_CACHE_DIR / f"{m_id}.json").unlink(missing_ok=True)
                        except Exception:
                            continue
            self._redirect(f"/?lang={lang}")
        elif parsed.path == "/clear_cache":
            from src.config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR
            for d in [MATCH_CACHE_DIR, TIMELINE_CACHE_DIR]:
                if d.exists():
                    for f in d.glob("*.json"):
                        try:
                            f.unlink()
                        except Exception:
                            pass
            self._redirect("/")
        else:
            self._redirect("/")


    def _send_html(self, html_str: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(html_str.encode("utf-8"))

    def _redirect(self, url: str):
        self.send_response(302)
        self.send_header("Location", url)
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
        webbrowser.open(url)

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
        return

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

