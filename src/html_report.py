import webbrowser
from pathlib import Path
from typing import Dict, Any
from .config import CACHE_DIR
from .i18n import get_text
import src.report_components as rc

REPORT_FILE = CACHE_DIR / "last_report.html"
CSS_FILE = Path(__file__).parent / "static" / "css" / "report.css"
JS_FILE = Path(__file__).parent / "static" / "js" / "report.js"


def _load_static_assets() -> tuple[str, str]:
    css_content = ""
    js_content = ""
    if CSS_FILE.exists():
        css_content = CSS_FILE.read_text(encoding="utf-8")
    if JS_FILE.exists():
        js_content = JS_FILE.read_text(encoding="utf-8")
    return css_content, js_content

def generate_html_report(data: Dict[str, Any], open_browser: bool = True, lang: str = "pt_BR") -> Path:
    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    target_puuid = data.get("target_puuid", "")
    raw_summary = data.get("raw_summary_text", "")
    raw_game_mode = str(data.get("game_mode", "")).upper()
    is_aram = "ARAM" in raw_game_mode
    is_arena = "CHERRY" in raw_game_mode or "ARENA" in raw_game_mode

    t100_win = team_100.get("win", False)
    t200_win = team_200.get("win", False)
    t100_txt = get_text("win", lang=lang) if t100_win else get_text("loss", lang=lang)
    t200_txt = get_text("win", lang=lang) if t200_win else get_text("loss", lang=lang)
    t100_class = "win-badge" if t100_win else "loss-badge"
    t200_class = "win-badge" if t200_win else "loss-badge"

    t100_status = f'<span class="badge {t100_class}">{t100_txt}</span>'
    t200_status = f'<span class="badge {t200_class}">{t200_txt}</span>'

    # Modular components
    all_duels_rendered = rc.render_all_duels(data, target_puuid=target_puuid, lang=lang)

    t1_players = team_100.get("players", [])
    t2_players = team_200.get("players", [])
    all_players = t1_players + t2_players

    awards_html = rc.render_match_awards(data, all_players, is_aram=is_aram, is_arena=is_arena, lang=lang)
    multikills_html = rc.render_multikills_section(data.get("multikills", []), lang=lang)
    events_html, timeline_top_toggle_btn, timeline_toggle_btn = rc.render_timeline_section(data, lang=lang)

    # Header & Mode lookup
    match_mode = rc.clean_mode_name(data.get("game_mode", "CLASSIC"))
    queue_name = rc.get_queue_name(data.get("queue_id", 0), lang=lang)
    full_mode_display = f"{match_mode} ({queue_name})" if queue_name else match_mode


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
    match_id_str = data.get("match_id", "")

    tab_title_parts = []
    if target_nick:
        tab_title_parts.append(target_nick)
    if target_kda:
        tab_title_parts.append(f"({target_kda})")
    if match_mode:
        tab_title_parts.append(match_mode)
    tab_title_parts.append(f"LoL Head-to-Head Duel Analytics ({match_id_str})")
    browser_tab_title = " • ".join(tab_title_parts)

    favicon_link = f'<link rel="icon" type="image/png" href="{favicon_url}"/>' if favicon_url else ""
    header_avatar_html = f'<img src="{favicon_url}" alt="{target_nick}" style="width: 52px; height: 52px; border-radius: 50%; border: 2px solid var(--accent); box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);"/>' if favicon_url else ""

    team_titles_html = f"""
    <div class="team-titles">
        <div style="color: #60a5fa;">{get_text('blue_team', lang=lang)} {t100_status}</div>
        <div style="color: #f87171;">{get_text('red_team', lang=lang)} {t200_status}</div>
    </div>
    """ if not is_arena else ""

    css_styles, js_scripts = _load_static_assets()

    # Client-side i18n object for JS
    remaining_events = max(0, len(data.get("key_events", [])) - 20)
    js_i18n = f"""
    <script>
        window.REPORT_I18N = {{
            show_less: "{get_text('show_less_events', lang=lang)}",
            show_more: "{get_text('show_more_events', lang=lang, count=remaining_events)}",
            copied: "Copiado! ✓"
        }};
    </script>
    """

    # Target player outcome badge (Win/Defeat or Arena placement)
    target_win = target_player.get("win", False) if target_player else False
    target_placement = target_player.get("placement", 0) if target_player else 0
    if is_arena and target_placement:
        is_arena_win = (target_placement <= 4)
        h_outcome_cls = "badge-win" if is_arena_win else "badge-loss"
        h_icon = "👑" if is_arena_win else "🪦"
        ord_suf = {1: "ST", 2: "ND", 3: "RD"}.get(target_placement, "TH")
        h_outcome_txt = f"{h_icon} {target_placement}º LUGAR" if lang == "pt_BR" else f"{h_icon} {target_placement}{ord_suf} PLACE"
    else:
        h_outcome_cls = "badge-win" if target_win else "badge-loss"
        h_outcome_txt = get_text("win", lang=lang) if target_win else get_text("loss", lang=lang)

    header_outcome_badge = f'<span class="header-outcome-badge {h_outcome_cls}">{h_outcome_txt}</span>'

    html_content = f"""<!DOCTYPE html>
<html lang="{ 'pt-BR' if lang == 'pt_BR' else 'en' }">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1100">
    <title>{browser_tab_title}</title>
    {favicon_link}
    <style>
        {css_styles}
    </style>
</head>
<body>
    <div class="top-nav-bar">
        <div class="kofi-container" title="Support TBlazeWarriorT on ko-fi.com" data-tooltip="Support TBlazeWarriorT on ko-fi.com">
            <script type='text/javascript' src='https://storage.ko-fi.com/cdn/widget/Widget_2.js'></script><script type='text/javascript'>kofiwidget2.init('Support me on Ko-fi', '#ea580c', 'Q5Q1IZ1W');kofiwidget2.draw();</script>
        </div>
        <div class="lang-picker">
            <a href="/analyze?match_id={data.get('match_id')}&puuid={target_puuid}&lang=en_US" class="{'lang-btn active' if lang=='en_US' else 'lang-btn'}" title="English (US)">
                <img class="flag-icon" src="https://flagcdn.com/w40/us.png" alt="US Flag"/> EN
            </a>
            <a href="/analyze?match_id={data.get('match_id')}&puuid={target_puuid}&lang=pt_BR" class="{'lang-btn active' if lang=='pt_BR' else 'lang-btn'}" title="Português (Brasil)">
                <img class="flag-icon" src="https://flagcdn.com/w40/br.png" alt="BR Flag"/> PT
            </a>
        </div>
    </div>

    <div class="container">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 2px;">
            <a href="/?lang={lang}" style="color:#38bdf8; text-decoration:none; font-weight:700; font-size:0.9rem; background:#111827; padding:8px 14px; border-radius:8px; border:1px solid var(--card-border); transition:background 0.2s;" onmouseover="this.style.background='#1f293d'" onmouseout="this.style.background='#111827'">{get_text('back_to_hub', lang=lang)}</a>
            <a href="/?lang={lang}" class="small-logo-link" style="text-decoration:none;">
                <span class="small-logo-title"><span class="fire-flame-anim">🔥</span> <span style="background:linear-gradient(90deg, #fb923c, #f97316, #ef4444); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Blaze GG</span> <span class="logo-author-badge">by TBlazeWarriorT</span></span>
            </a>
        </div>


        <div class="header" style="display:flex; align-items:center; gap:16px;">
            {header_avatar_html}
            <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <h1 style="margin:0; font-size: 1.45rem; font-weight:800; color:#fff;">{target_nick}</h1>
                    {header_outcome_badge}
                    <span style="background:#1e293b; color:var(--accent); font-weight:800; font-size:0.9rem; padding:3px 10px; border-radius:6px; border:1px solid #334155;">KDA: {target_kda}</span>
                </div>
                <div style="color: var(--text-muted); margin-top: 5px; font-size:0.88rem;">
                    <span style="color:#94a3b8; font-family:monospace;">{data.get('match_id')}</span> • <b>{full_mode_display}</b> • {get_text('duration', lang=lang)}: <b>{data.get('duration')}</b>
                </div>
            </div>
        </div>

        {team_titles_html}

        <!-- CONFRONTOS LADO A LADO -->
        <div>
            {all_duels_rendered}
        </div>

        <!-- Pódios da Partida -->
        {awards_html}

        <!-- Destaques de Multikills -->
        {multikills_html}

        <!-- Momentos Chave -->
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h3 style="margin:0;">{get_text('timeline_title', lang=lang)}</h3>
                {timeline_top_toggle_btn}
            </div>
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

    {js_i18n}
    <script>
        {js_scripts}
    </script>
</body>
</html>
"""
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    import webbrowser
    if open_browser:
        webbrowser.open(REPORT_FILE.as_uri())

    return REPORT_FILE
