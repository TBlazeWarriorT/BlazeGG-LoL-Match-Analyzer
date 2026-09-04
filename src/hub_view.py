import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import concurrent.futures

from src.config import BASE_DIR, CACHE_DIR, MATCH_CACHE_DIR, TIMELINE_CACHE_DIR, get_api_key, get_key_expires_at, save_api_key, is_production_mode, parse_expiry_str, get_prod_key
from src.riot_client import RiotClient, RiotAPIError
from src.cache_manager import set_last_viewed, get_last_viewed, save_session, get_last_session
from src.event_engine import MatchAnalysis
from src.ddragon import DataDragon
from src.i18n import get_text, SUPPORTED_LANGUAGES, render_language_dropdown, render_kofi_button

COMMON_CSS_FILE = Path(__file__).parent / "static" / "css" / "common.css"
HUB_CSS_FILE = Path(__file__).parent / "static" / "css" / "hub.css"
HUB_JS_FILE = Path(__file__).parent / "static" / "js" / "report.js"

def get_ddragon(lang: str = "en_US") -> DataDragon:
    return DataDragon(language=lang)

def format_relative_time(creation_ms: int, lang: str = "en_US") -> str:
    import time
    if not creation_ms or creation_ms == 0:
        return ""
    diff_s = int(time.time() - (creation_ms / 1000))
    if diff_s < 60:
        return get_text("time_just_now", lang=lang)
    elif diff_s < 3600:
        m = diff_s // 60
        return get_text("time_mins_ago", lang=lang, count=m)
    elif diff_s < 86400:
        h = diff_s // 3600
        key = "time_hour_ago" if h == 1 else "time_hours_ago"
        return get_text(key, lang=lang, count=h)
    elif diff_s < 604800:
        d = diff_s // 86400
        key = "time_day_ago" if d == 1 else "time_days_ago"
        return get_text(key, lang=lang, count=d)
    else:
        fmt = "%d/%m/%Y" if lang == "pt_BR" else "%m/%d/%Y"
        return datetime.fromtimestamp(creation_ms / 1000).strftime(fmt)

_MATCHES_CACHE_STORE = {}
_MATCHES_CACHE_TIMESTAMP = 0

def get_cache_storage_mb() -> float:
    from src.cache_manager import list_cache_files
    total_bytes = 0
    for directory in (MATCH_CACHE_DIR, TIMELINE_CACHE_DIR):
        for f in list_cache_files(directory):
            try:
                total_bytes += f.stat().st_size
            except OSError:
                pass
    return total_bytes / (1024 * 1024)

def get_cached_matches_list(lang: str = "en_US"):
    global _MATCHES_CACHE_STORE, _MATCHES_CACHE_TIMESTAMP
    from src.cache_manager import list_cache_files, load_json
    if not MATCH_CACHE_DIR.exists():
        return []

    # Get current directory state / latest mtime
    try:
        current_files = list_cache_files(MATCH_CACHE_DIR)
        latest_mtime = max((f.stat().st_mtime for f in current_files), default=0)
        cache_key = (lang, len(current_files), latest_mtime)
        if cache_key in _MATCHES_CACHE_STORE:
            return _MATCHES_CACHE_STORE[cache_key]
    except Exception:
        current_files = list_cache_files(MATCH_CACHE_DIR)

    matches = []
    dd = get_ddragon(lang)
    for f in current_files:
        try:
            data = load_json(f)
            if not data:
                continue
            info = data.get("info", {})
            meta = data.get("metadata", {})
            mid = meta.get("matchId", f.name.split(".")[0])
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
                    "role": p.get("teamPosition") or p.get("individualPosition", "UNKNOWN"),
                    "largest_multikill": p.get("largestMultiKill", 0),
                    "penta_kills": p.get("pentaKills", 0),
                    "quadra_kills": p.get("quadraKills", 0),
                    "triple_kills": p.get("tripleKills", 0)
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
    if 'cache_key' in locals():
        _MATCHES_CACHE_STORE[cache_key] = matches
    return matches

def clean_game_mode(mode: str, queue_id: int = 0, lang: str = "en_US", player_count: int = 0) -> str:
    from src.report_components.utils import format_full_mode_display
    return format_full_mode_display(mode, queue_id=queue_id, lang=lang, player_count=player_count)

def _render_mini_champ_icon(p, puuid, title_suffix=""):
    """Small clickable champion icon used in the team strips on a match card
    (arena subteams, blue/red teams) — was copy-pasted 3x with only the title
    differing (arena adds a placement suffix)."""
    host_cls = " m-mini-host" if p.get("puuid") == puuid else ""
    return f'<img class="m-mini-champ{host_cls}" src="{p["icon"]}" title="{p["champion"]} ({p["name"]}){title_suffix}" alt="{p["champion"]}" onclick="promptSearchSummoner(\'{p.get("name", "")}\', \'{p.get("tag", "")}\')"/>'

def render_match_card(m_id, champ_name, champ_icon, riot_id, kda, win, duration, mode, puuid, rel_time="", is_cached=False, lang="en_US", queue_id=0, team_100=None, team_200=None, placement=0, largest_multikill=0, penta_kills=0, quadra_kills=0):
    m_upper = str(mode).upper()
    is_arena = ("CHERRY" in m_upper or "ARENA" in m_upper or queue_id in (1700, 1710))
    all_parts = (team_100 or []) + (team_200 or [])
    player_count = len(all_parts)
    
    # In Arena: top 50% is considered a win (e.g. 1st-4th in 8-team 2v2v2v2 or 1st-2nd/3rd in 3v3v3v3)
    if is_arena and placement:
        is_effective_win = placement <= 4 if queue_id in (1700, 1710) or placement <= 8 else win
        place_suffix = f" (#{placement})"
        win_class = "card-win" if is_effective_win else "card-loss"
        badge_class = "badge-win" if is_effective_win else "badge-loss"
        
        ord_suffix = {1: "ST", 2: "ND", 3: "RD"}.get(placement, "TH")
        if is_effective_win:
            win_txt = get_text("arena_place_win", lang=lang, place=placement, ord_suffix=ord_suffix)
        else:
            win_txt = get_text("arena_place_loss", lang=lang, place=placement, ord_suffix=ord_suffix)
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

    avatar_block = f"""
    <div class="avatar-glint-wrapper" onclick="promptSearchSummoner('{g_name}', '{t_line}')" title="{champ_name} ({riot_id})">
        <img class="champ-avatar-lg" src="{champ_icon}" alt="{champ_name}"/>
        <div class="avatar-glint-sweep"></div>
    </div>
    """
    if opp_champ:
        opp_gname = opp_champ.get('name', '')
        opp_tline = opp_champ.get('tag', '')
        opp_riot = f"{opp_gname}#{opp_tline}"
        opp_title = get_text("direct_opponent_title", lang=lang, champ=opp_champ['champion'], riot_id=opp_riot)
        avatar_block = f"""
        <div class="h2h-avatar-duo">
            <div class="avatar-glint-wrapper" onclick="promptSearchSummoner('{g_name}', '{t_line}')" title="{champ_name} ({riot_id})">
                <img class="champ-avatar-lg" src="{champ_icon}" alt="{champ_name}"/>
                <div class="avatar-glint-sweep"></div>
            </div>
            <span class="h2h-vs-badge">VS</span>
            <div class="avatar-glint-wrapper avatar-opp-wrapper" onclick="promptSearchSummoner('{opp_gname}', '{opp_tline}')" title="{opp_title}">
                <img class="champ-avatar-opp" src="{opp_champ['icon']}" alt="{opp_champ['champion']}"/>
            </div>
        </div>
        """

    teams_html = ""
    if is_arena and all_parts:
        subteams = {}
        for p in all_parts:
            place = p.get("placement") or p.get("subteam_id", 0)
            subteams.setdefault(place, []).append(p)
        sorted_subteams = sorted(subteams.items(), key=lambda x: x[0] if isinstance(x[0], int) and x[0] > 0 else 99)
        
        subteam_groups = []
        for place, plist in sorted_subteams:
            p_icons = "".join(_render_mini_champ_icon(p, puuid, f" - #{place}") for p in plist)
            extra_cls = " m-team-first" if place == 1 else ""
            subteam_groups.append(f'<div class="m-team-group m-team-arena{extra_cls}" title="#{place}">{p_icons}</div>')
        teams_html = f'<div class="m-teams-strip m-arena-strip">{"".join(subteam_groups)}</div>'
    elif team_100 and team_200:
        t1_icons = "".join(_render_mini_champ_icon(p, puuid) for p in team_100)
        t2_icons = "".join(_render_mini_champ_icon(p, puuid) for p in team_200)
        teams_html = f"""
        <div class="m-teams-strip">
            <div class="m-team-group m-team-blue">{t1_icons}</div>
            <span class="m-vs-text">vs</span>
            <div class="m-team-group m-team-red">{t2_icons}</div>
        </div>
        """


    multikill_badge = ""
    is_penta = (penta_kills > 0 or largest_multikill >= 5)
    is_quadra = (quadra_kills > 0 or largest_multikill == 4)
    if is_penta:
        multikill_badge = '<span class="m-badge badge-penta" title="Pentakill!">PENTAKILL 💥</span>'
    elif is_quadra:
        multikill_badge = '<span class="m-badge badge-quadra" title="Quadrakill!">QUADRA KILL ⚔️</span>'

    return f"""
    <div class="match-item {win_class}">
        <div class="m-left">
            {avatar_block}
            <div>
                <div class="m-champ-name">
                    {champ_name} 
                    <a href="{search_link}" class="summoner-link" title="{get_text('tooltip_search_matches', lang=lang)}">({riot_id})</a>
                    {multikill_badge}
                </div>
                <div class="m-sub">{clean_game_mode(mode, queue_id=queue_id, lang=lang, player_count=player_count)} • {duration} {time_badge} • KDA: <b>{kda}</b></div>
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




def render_home_html(search_results=None, error_msg="", search_name="", search_tag="", lang="en_US", session_key="", session_expiry="", user_history=None, is_local=True, auto_expand=False, view_mode="recent", id_search_history=None):
    cached_list = get_cached_matches_list(lang=lang)
    last_sess = get_last_session() or {}
    def_name = search_name or (last_sess.get("game_name", "") if is_local else "")
    def_tag = search_tag or (last_sess.get("tag_line", "") if is_local else "")
    
    curr_key = get_api_key(session_key=session_key)
    exp_val = get_key_expires_at(session_expiry=session_expiry)
    key_configured = bool(curr_key)
    
    import time
    expiry_msg = ""
    is_expired = False
    
    prod_mode = is_production_mode(session_key=session_key)
    err_lower = str(error_msg).lower()
    has_api_error = bool(error_msg and ("expir" in err_lower or "401" in err_lower or "403" in err_lower or "chave" in err_lower or "key" in err_lower or "unauthorized" in err_lower or "forbidden" in err_lower))
    
    if key_configured:
        masked_key = f"{curr_key[:6]}...{curr_key[-4:]}" if len(curr_key) > 10 else "******"
        if prod_mode:
            expiry_msg = get_text("prod_key_active", lang=lang)
            key_status_badge = ""  # Clean header in production
        elif exp_val and str(exp_val).isdigit():
            exp_ts = int(exp_val)
            diff_s = exp_ts - time.time()
            if diff_s <= 0:
                is_expired = True
                expiry_msg = f'<span style="color:#ef4444; font-weight:bold;">{get_text("key_status_expired", lang=lang)}</span>'
                key_status_badge = f'<span style="color:#fca5a5; background:#991b1b; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_expired", lang=lang, masked=masked_key)}</span>'
            else:
                hours = int(diff_s // 3600)
                mins = int((diff_s % 3600) // 60)
                expiry_msg = f'<span style="color:#86efac; font-weight:bold;">{get_text("key_status_valid", lang=lang, hours=hours, mins=mins)}</span>'
                key_status_badge = f'<span style="color:#86efac; background:#166534; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_active", lang=lang, masked=masked_key, hours=hours, mins=mins)}</span>'
        else:
            expiry_msg = f'<span style="color:var(--text-muted);">{get_text("key_status_no_info", lang=lang)}</span>'
            key_status_badge = f'<span style="color:#86efac; background:#166534; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_active_no_exp", lang=lang, masked=masked_key)}</span>'
    else:
        masked_key = get_text("none_label", lang=lang)
        expiry_msg = get_text("key_status_none", lang=lang)
        key_status_badge = f'<span style="color:#fca5a5; background:#991b1b; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{get_text("key_missing", lang=lang)}</span>'

    id_search_lower = set(i.strip().lower() for i in (id_search_history or []) if i.strip())

    cached_html = ""
    auto_expand_indices = []
    if cached_list:
        # Group cached matches by target summoner
        summoner_groups = {}
        for m in cached_list:
            # Find which participant(s) match target_puuid or user history. A single
            # match can rightfully belong to more than one tab (e.g. two searched
            # summoners who duo'd together) — target_puuid only records whoever got
            # cached first, so it must never short-circuit checking user_history too,
            # or a later searcher's own matches silently vanish into someone else's tab.
            matched_summoners = []
            matched_puuids = set()
            if m.get("target_puuid"):
                for part in m["participants"]:
                    if part["puuid"] == m["target_puuid"]:
                        matched_summoners.append(part)
                        matched_puuids.add(part["puuid"])
            if user_history:
                u_hist_lower = [h.strip().lower() for h in user_history if h.strip()]
                for part in m["participants"]:
                    if part["puuid"] in matched_puuids:
                        continue
                    p_label = f"{part.get('name', '')}#{part.get('tag', '')}".lower()
                    if p_label in u_hist_lower:
                        matched_summoners.append(part)
                        matched_puuids.add(part["puuid"])
            if is_local and last_sess.get("puuid"):
                for part in m["participants"]:
                    if part["puuid"] in matched_puuids:
                        continue
                    if part["puuid"] == last_sess.get("puuid"):
                        matched_summoners.append(part)
                        matched_puuids.add(part["puuid"])
            if m["match_id"].lower() in id_search_lower and m["participants"]:
                # This browser itself searched this exact match by ID (tracked via the
                # blaze_id_searches cookie) — show it under "ID Searches" regardless of
                # local/prod, same as a named-summoner match shows under user_history.
                # Deliberately NOT deduped against matched_puuids: this is a distinct
                # tab/perspective from any named attribution above, not a duplicate of
                # it, so the same player's match can legitimately show under both their
                # own name tab and this browser's "ID Searches" tab at the same time.
                first_p = dict(m["participants"][0])
                first_p["_is_global_tab"] = True
                matched_summoners.append(first_p)
            if not matched_summoners and is_local and m["participants"]:
                # True last resort: nothing above claims this match at all (not the
                # recorded target_puuid owner, not your history, not this browser's ID
                # search list, not even your active local session) — dump it in the
                # generic bucket so "cached" view can still show/manage it somewhere.
                first_p = dict(m["participants"][0])
                first_p["_is_global_tab"] = True
                matched_summoners.append(first_p)

            if not matched_summoners:
                continue

            for p in matched_summoners:
                card_html = render_match_card(
                    m["match_id"], p.get("champion", ""), p.get("icon", ""),
                    f"{p.get('name', '')}#{p.get('tag', '')}", p.get("kda", ""),
                    p.get("win", False), m["duration"], m["game_mode"],
                    p.get("puuid", ""), rel_time=m.get("relative_time", ""), is_cached=True, lang=lang, queue_id=m.get("queue_id", 0),
                    team_100=m.get("team_100"), team_200=m.get("team_200"), placement=p.get("placement", 0),
                    largest_multikill=p.get("largest_multikill", 0), penta_kills=p.get("penta_kills", 0), quadra_kills=p.get("quadra_kills", 0)
                )

                s_name = p.get("name", "")
                s_tag = p.get("tag", "")
                if p.get("_is_global_tab"):
                    s_label = get_text("global_other_tab", lang=lang)
                else:
                    s_label = f"{s_name}#{s_tag}" if (s_name and s_tag) else get_text("global_other_tab", lang=lang)
                
                # Track group cards, wins and losses
                is_match_win = p.get("win", False)
                place_val = p.get("placement", 0)
                if "CHERRY" in str(m.get("game_mode", "")).upper() or "ARENA" in str(m.get("game_mode", "")).upper():
                    if place_val:
                        is_match_win = (place_val <= 4)
                
                group_entry = summoner_groups.setdefault(s_label, {"cards": [], "wins": 0, "losses": 0, "is_global": bool(p.get("_is_global_tab")), "card_match_ids": [], "card_wins": []})
                group_entry["cards"].append(card_html)
                group_entry["card_match_ids"].append(m["match_id"])
                group_entry["card_wins"].append(is_match_win)
                if is_match_win:
                    group_entry["wins"] += 1
                else:
                    group_entry["losses"] += 1

        # In remote/production, always filter to only summoners searched by THIS user.
        # Locally, "recent" (the default) applies that same filter as a lightweight view;
        # "cached" is the edit/inspect mode showing everything on disk, unfiltered.
        show_recent_only = (not is_local) or view_mode != "cached"
        had_unfiltered_cache_data = bool(summoner_groups)
        if show_recent_only:
            user_hist_list = user_history if user_history is not None else []
            user_history_lower = [h.strip().lower() for h in user_hist_list if h.strip()]
            filtered_groups = {}
            for k, v in summoner_groups.items():
                if k.lower() in user_history_lower:
                    filtered_groups[k] = v
                    continue
                if v.get("is_global") and id_search_lower:
                    # The "ID Searches" group may also hold matches nobody's cookie
                    # tracked (the full-disk fallback used by "cached" view) — only
                    # keep the cards *this browser* actually searched by ID.
                    keep_idx = [i for i, mid in enumerate(v.get("card_match_ids", [])) if mid.lower() in id_search_lower]
                    if keep_idx:
                        filtered_groups[k] = {
                            "cards": [v["cards"][i] for i in keep_idx],
                            "wins": sum(1 for i in keep_idx if v["card_wins"][i]),
                            "losses": sum(1 for i in keep_idx if not v["card_wins"][i]),
                            "is_global": True,
                            "card_match_ids": [v["card_match_ids"][i] for i in keep_idx],
                            "card_wins": [v["card_wins"][i] for i in keep_idx],
                        }
            summoner_groups = filtered_groups

        # Build tabs: Order by user's recent search order (user_history) so newest is always first on the left
        tab_buttons = []
        tab_panes = []
        
        # Sort function: if summoner in user_history, use its index; otherwise fallback to negative match count
        def get_group_sort_key(item):
            s_lbl = item[0].lower()
            if user_history:
                for h_idx, h in enumerate(user_history):
                    if h.lower() == s_lbl:
                        return (0, h_idx)
            return (1, -len(item[1]["cards"]))

        sorted_groups = sorted(summoner_groups.items(), key=get_group_sort_key)

        # Decide initial active tab (prefer search summoner, then user's most recent search, then first tab 0)
        searched_label = f"{search_name}#{search_tag}" if (search_name and search_tag) else ""
        user_recent_label = user_history[0] if (user_history and len(user_history) > 0) else ""
        sess_label = f"{last_sess.get('game_name', '')}#{last_sess.get('tag_line', '')}" if is_local else ""
        target_focus = searched_label or user_recent_label or sess_label
        
        active_tab_idx = 0
        for idx, (s_label, s_data) in enumerate(sorted_groups):
            if s_label.lower() == target_focus.lower():
                active_tab_idx = idx
                break

        for idx, (s_label, s_data) in enumerate(sorted_groups):
            cards_list = s_data["cards"]
            wins_cnt = s_data["wins"]
            loss_cnt = s_data["losses"]
            tab_id = f"cache-tab-{idx}"
            btn_active_cls = "active" if idx == active_tab_idx else ""
            pane_active_cls = "active" if idx == active_tab_idx else ""
            tab_pre_expanded = auto_expand and idx == active_tab_idx

            # Format cards: first 8 visible, remaining hidden (unless this tab was just fetched via load more)
            formatted_cards = []
            for c_idx, c_html in enumerate(cards_list):
                if c_idx < 8 or tab_pre_expanded:
                    formatted_cards.append(c_html)
                else:
                    hidden_card = c_html.replace('class="match-item ', 'class="match-item match-hidden ')
                    formatted_cards.append(hidden_card)

            # Build action buttons inside tab
            expand_btn = ""
            if len(cards_list) > 8:
                if tab_pre_expanded:
                    auto_expand_indices.append(idx)
                    lbl_show_less = get_text("tab_show_less", lang=lang)
                    expand_btn = f"""
                    <button type="button" class="btn-tab-action" id="expand-btn-{idx}" onclick="toggleTabMatches({idx}, {len(cards_list)})">
                        <span>{lbl_show_less}</span>
                    </button>
                    """
                else:
                    lbl_show_more = get_text("show_more_matches", lang=lang, count=len(cards_list) - 8)
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
                    <button type="submit" class="btn-tab-action btn-tab-refresh" data-label="{lbl_refresh}" onclick="this.querySelector('span').innerText='{get_text('refreshing_btn', lang=lang)}';">
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
                    <button type="submit" class="btn-tab-action btn-tab-load-more" data-label="{lbl_load_more}" onclick="this.querySelector('span').innerText='{get_text('loading_more_btn', lang=lang)}';">
                        <span>{lbl_load_more}</span>
                    </button>
                </form>
                """

            actions_html = ""
            if expand_btn or load_more_btn or refresh_btn:
                actions_html = f"""
                <div class="tab-actions-bar">
                    {expand_btn}
                    {refresh_btn}
                    {load_more_btn}
                </div>
                """

            # Only "cached" view (the full-disk inspect/edit mode) actually deletes
            # anything. In "recent" view — even locally — the X just drops this
            # summoner from your own browsing history, same as it already does in
            # prod: hitting X while glancing at your recent searches should never be
            # able to nuke cache that "cached" view (or someone else's recent tab
            # sharing the same match) still relies on.
            is_destructive_delete = is_local and view_mode == "cached"
            del_prompt = get_text("del_summoner_prompt", lang=lang) if is_destructive_delete else get_text("close_summoner_prompt", lang=lang)
            tab_delete_title = get_text("tooltip_delete_tab", lang=lang) if is_destructive_delete else get_text("tooltip_close_tab", lang=lang)
            lbl_saved = get_text("lbl_saved_matches", lang=lang)
            lbl_v = get_text("lbl_victories", lang=lang)
            lbl_d = get_text("lbl_defeats", lang=lang)
            
            tab_tip_lines = [
                f"<b>{s_label}</b>",
                f"• {lbl_saved}: <b>{len(cards_list)}</b>",
                f"• {lbl_v}: <b>{wins_cnt}</b>",
                f"• {lbl_d}: <b>{loss_cnt}</b>"
            ]
            tab_tip_html = "<br/>".join(tab_tip_lines).replace('"', '&quot;')

            onsubmit_str = f"event.stopPropagation(); return confirmDeleteSummonerModal(this, '{s_label}');" if is_destructive_delete else "event.stopPropagation();"

            tab_buttons.append(f"""
            <div class="cache-tab-btn {btn_active_cls}" onclick="switchCacheTab({idx})" data-tooltip="{tab_tip_html}">
                <span>{s_label}</span>
                <span class="cache-tab-count">{len(cards_list)}</span>
                <form action="/delete_summoner_cache" method="POST" style="display:inline; margin:0;" onsubmit="{onsubmit_str}">
                    <input type="hidden" name="summoner_label" value="{s_label}"/>
                    <input type="hidden" name="lang" value="{lang}"/>
                    <input type="hidden" name="view" value="{'cached' if not show_recent_only else 'recent'}"/>
                    <input type="hidden" name="is_global" value="{'1' if s_data.get('is_global') else '0'}"/>
                    <button type="submit" class="cache-tab-delete" data-tooltip="{tab_delete_title}" style="background:none; border:none; cursor:pointer;" onclick="event.stopPropagation();">✕</button>
                </form>
            </div>
            """)

            tab_panes.append(f"""
            <div id="{tab_id}" class="cache-tab-content {pane_active_cls}">
                {"".join(formatted_cards)}
                {actions_html}
            </div>
            """)


        clear_cache_btn = f"""
        <form action="/clear_cache" method="POST" onsubmit="return confirmClearAllCacheModal(this);">
            <button type="submit" class="btn btn-clear-cache">{get_text('btn_clear_cache', lang=lang)}</button>
        </form>
        """ if is_local else ""

        if tab_buttons:
            title_key = "recent_summoners_title" if show_recent_only else "cached_matches_title"
            c_title = get_text(title_key, lang=lang, count=sum(len(v["cards"]) for v in summoner_groups.values()))

            view_toggle_html = ""
            if is_local:
                other_mode = "cached" if show_recent_only else "recent"
                other_label = get_text("btn_view_cached", lang=lang) if show_recent_only else get_text("btn_view_recent", lang=lang)
                view_toggle_html = f"""
                <a href="/?lang={lang}&view={other_mode}" class="btn-tab-action" style="text-decoration:none;">{other_label}</a>
                """
                if not show_recent_only:
                    storage_mb = get_cache_storage_mb()
                    view_toggle_html = f"""
                    <span class="m-sub">{get_text('cache_storage_used', lang=lang, mb=f"{storage_mb:.1f}")}</span>
                    {view_toggle_html}
                    """

            cached_html = f"""
            <div class="section-card" style="margin-top: 24px;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
                    <h3 style="margin:0;">{c_title}</h3>
                    <div style="display:flex; gap:8px; align-items:center;">
                        {view_toggle_html}
                        {clear_cache_btn}
                    </div>
                </div>
                
                <div class="cache-tabs-nav">
                    {"".join(tab_buttons)}
                </div>

                <div class="cache-tabs-container">
                    {"".join(tab_panes)}
                </div>
            </div>
            """
        elif is_local and show_recent_only and had_unfiltered_cache_data:
            # "Recent" filtered everything away, but there IS cached data on disk —
            # don't just render nothing, point at "cached" view instead of leaving
            # the section silently blank as if there were no data anywhere at all.
            cached_html = f"""
            <div class="section-card" style="margin-top: 24px; text-align:center;">
                <p style="color:var(--text-muted); margin:0 0 10px 0;">{get_text('empty_recent_hint', lang=lang)}</p>
                <a href="/?lang={lang}&view=cached" class="btn-tab-action" style="text-decoration:none; display:inline-block;">{get_text('btn_view_cached', lang=lang)}</a>
            </div>
            """
        else:
            cached_html = ""



    key_card_cls = "section-card key-card-urgent" if (is_expired or not key_configured or "expir" in str(error_msg).lower()) else "section-card"
    error_html = f'<div class="error-banner">{error_msg}</div>' if error_msg else ""

    common_css = COMMON_CSS_FILE.read_text(encoding="utf-8") if COMMON_CSS_FILE.exists() else ""
    hub_css = common_css + (HUB_CSS_FILE.read_text(encoding="utf-8") if HUB_CSS_FILE.exists() else "")
    hub_js = HUB_JS_FILE.read_text(encoding="utf-8") if HUB_JS_FILE.exists() else ""

    config_card_html = f"""
    <!-- CONFIGURAR API KEY -->
    <div class="{key_card_cls}" style="margin-top: 16px;">
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
                <button type="submit" class="btn" style="background:#16a34a; border-color:#22c55e;">{get_text('btn_save_config', lang=lang)}</button>
            </div>
        </form>
    </div>
    """

    # Dynamic positioning: if expired/invalid or has API error, put config above cached matches
    # If in production mode AND the active key is the official prod key (nothing for
    # this visitor to manage — it's centrally administered), hide the box completely.
    # A visitor using their own dev/session key still needs to see it to refresh it
    # before it expires, even though the deployment itself is "production".
    is_official_prod_key = bool(curr_key) and curr_key == get_prod_key()
    if has_api_error or is_expired or not key_configured:
        body_sections_html = f"""
        {config_card_html}
        {cached_html}
        """
    elif prod_mode and is_official_prod_key:
        body_sections_html = f"""
        {cached_html}
        """
    else:
        body_sections_html = f"""
        {cached_html}
        {config_card_html}
        """

    js_i18n = f"""
    <script>
        window.REPORT_I18N = {{
            lang: "{lang}",
            search_modal_title: "{get_text('modal_search_summoner_title', lang=lang)}",
            search_modal_body: "{get_text('modal_search_summoner_body', lang=lang)}",
            search_modal_confirm: "{get_text('search_btn', lang=lang)}",
            delete_modal_title: "{get_text('tooltip_delete_tab', lang=lang)}",
            delete_modal_body: "{get_text('modal_delete_summoner_body', lang=lang)}",
            delete_modal_confirm: "{get_text('modal_delete_summoner_confirm', lang=lang)}",
            clear_all_title: "{get_text('confirm_clear_cache', lang=lang)}",
            clear_all_body: "{get_text('modal_clear_all_body', lang=lang)}",
            clear_all_confirm: "{get_text('modal_clear_all_confirm', lang=lang)}",
            cancel: "{get_text('btn_cancel', lang=lang)}",
            tab_show_less: "{get_text('tab_show_less', lang=lang)}",
            tab_show_more: "{get_text('tab_show_more', lang=lang)}"
        }};
    </script>
    """

    return f"""<!DOCTYPE html>
<html lang="{get_text('html_lang_code', lang=lang)}">
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
<div class="top-nav-bar">
    {render_kofi_button(lang=lang)}
    {render_language_dropdown(current_lang=lang)}
</div>

<div class="container">
    <div class="header">
        <div>
            <a href="/?lang={lang}" style="text-decoration:none;" title="{get_text('tooltip_back_home', lang=lang)}">
                <div style="display:inline-flex; align-items:baseline; gap:16px;">
                    <h1 class="logo-title" style="font-size:2.35rem; font-weight:900; letter-spacing:0.5px; margin:0; display:inline-flex; align-items:center; gap:10px; cursor:pointer;"><span class="fire-flame-anim">🔥</span> Blaze GG</h1>
                    <span class="logo-author-badge">by TBlazeWarriorT</span>
                </div>
            </a>
            <div style="color: var(--text-muted); margin-top: 4px; font-size:0.95rem;">{get_text('app_sub', lang=lang)}</div>
        </div>
        <div>{key_status_badge}</div>
    </div>


    {error_html}

    <!-- BUSCADORES (INVOCADOR & MATCH ID) -->
    <div class="search-cards-grid">
        <!-- BUSCADOR DE INVOCADOR -->
        <div class="section-card search-card-glow">
            <div class="search-card-header">
                <span class="search-card-title">{get_text('search_title', lang=lang)}</span>
            </div>
            <form action="/search" method="GET" class="search-form-layout">
                <input type="hidden" name="lang" value="{lang}"/>
                <div class="search-inputs-group">
                    <input type="text" name="game_name" class="input-game-name" placeholder="{get_text('search_game_name_ph', lang=lang)}" value="{def_name}" required/>
                    <span class="tag-hash-separator">#</span>
                    <input type="text" name="tag_line" class="input-tag-line" placeholder="{get_text('search_tag_ph', lang=lang)}" value="{def_tag}" required/>
                </div>
                <div class="search-btn-container">
                    <button type="submit" class="btn btn-search-action" id="btnSearch" data-label="{get_text('search_btn', lang=lang)}" onclick="this.innerText='{get_text('searching_btn', lang=lang)}';">{get_text('search_btn', lang=lang)}</button>
                </div>
            </form>
        </div>

        <!-- BUSCADOR DE MATCH ID -->
        <div class="section-card search-card-glow">
            <div class="search-card-header">
                <span class="search-card-title">{get_text('search_match_id_title', lang=lang)}</span>
            </div>
            <form action="/search_match" method="GET" class="search-form-layout">
                <input type="hidden" name="lang" value="{lang}"/>
                <div class="search-inputs-group">
                    <input type="text" name="match_id" class="input-match-id" placeholder="{get_text('search_match_id_ph', lang=lang)}" required/>
                </div>
                <div class="search-btn-container">
                    <button type="submit" class="btn btn-search-action btn-search-match-id">{get_text('search_match_id_btn', lang=lang)}</button>
                </div>
            </form>
        </div>
    </div>

    {body_sections_html}

    <div class="legal-footer">
        Blaze.gg isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
    </div>
</div>
{js_i18n}
<script>
    {hub_js}
    {"".join(f"tabExpandedState[{i}] = true;" for i in auto_expand_indices)}
</script>
</body>
</html>
"""


