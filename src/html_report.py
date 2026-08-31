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

    match_id_str = data.get("match_id", "")
    tab_title_parts = []
    if target_player:
        target_nick = target_player.get("riot_id", "")
        target_kda = target_player.get("kda", "")
        if target_nick:
            tab_title_parts.append(target_nick)
        if target_kda:
            tab_title_parts.append(f"({target_kda})")
    if match_mode:
        tab_title_parts.append(match_mode)
    tab_title_parts.append(f"LoL Head-to-Head Duel Analytics ({match_id_str})")
    browser_tab_title = " • ".join(tab_title_parts)

    favicon_url = target_player.get("champion_icon", "") if target_player else ""
    favicon_link = f'<link rel="icon" type="image/png" href="{favicon_url}"/>' if favicon_url else ""
    
    if target_player:
        header_avatar_html = f'''<div class="avatar-glint-wrapper" style="width:52px; height:52px; border:2px solid var(--accent); box-shadow:0 0 12px rgba(56, 189, 248, 0.35); flex-shrink:0;">
            <img src="{favicon_url}" alt="{target_player.get('riot_id', '')}" style="width:100%; height:100%; object-fit:cover; transform:scale(1.15); display:block;"/>
            <span class="avatar-glint-sweep"></span>
        </div>'''
        target_win = target_player.get("win", False)
        target_placement = target_player.get("placement", 0)
        if is_arena and target_placement:
            is_arena_win = (target_placement <= 4)
            h_outcome_cls = "badge-win" if is_arena_win else "badge-loss"
            ord_suf = {1: "ST", 2: "ND", 3: "RD"}.get(target_placement, "TH")
            key_res = "arena_place_win" if is_arena_win else "arena_place_loss"
            h_outcome_txt = get_text(key_res, lang=lang, place=target_placement, ord_suffix=ord_suf)
        else:
            h_outcome_cls = "badge-win" if target_win else "badge-loss"
            h_outcome_txt = get_text("win", lang=lang) if target_win else get_text("loss", lang=lang)
        header_outcome_badge = f'<span class="header-outcome-badge {h_outcome_cls}">{h_outcome_txt}</span>'
        header_kda_badge = f'<span style="background:#1e293b; color:var(--accent); font-weight:800; font-size:0.9rem; padding:3px 10px; border-radius:6px; border:1px solid #334155;">KDA: {target_player.get("kda", "")}</span>'
        header_title_name = target_player.get("riot_id", "")
        header_main_info = f"""
        {header_avatar_html}
        <div style="flex:1;">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <h1 style="margin:0; font-size: 1.45rem; font-weight:800; color:#fff;">{header_title_name}</h1>
                {header_outcome_badge}
                {header_kda_badge}
            </div>
            <div style="color: var(--text-muted); margin-top: 5px; font-size:0.88rem; display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                {rc.get_region_flag_badge(data.get('match_id', ''))}
                <span style="color:#94a3b8; font-family:monospace;">{data.get('match_id')}</span> • <b>{full_mode_display}</b> • {get_text('duration', lang=lang)}: <b>{data.get('duration')}</b>
            </div>
        </div>
        """
    else:
        # Neutral header (searched directly by Match ID)
        header_main_info = f"""
        <div style="flex:1;">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <h1 style="margin:0; font-size: 1.35rem; font-weight:800; color:#fff; display:flex; align-items:center; gap:8px;">
                    {rc.get_region_flag_badge(data.get('match_id', ''))}
                    <span style="font-family:monospace; color:#f1f5f9; letter-spacing:0.5px;">{data.get('match_id')}</span>
                </h1>
                <span style="background:#1e293b; color:#cbd5e1; font-weight:700; font-size:0.85rem; padding:3px 10px; border-radius:6px; border:1px solid #334155;">{full_mode_display}</span>
                <span style="background:#090d16; color:#94a3b8; font-weight:600; font-size:0.85rem; padding:3px 10px; border-radius:6px; border:1px solid #1e293b;">{get_text('duration', lang=lang)}: <b>{data.get('duration')}</b></span>
            </div>
        </div>
        """
    team_titles_html = f"""
    <div class="team-titles">
        <div style="color: #60a5fa;">{get_text('blue_team', lang=lang)} {t100_status}</div>
        <div style="color: #f87171;">{get_text('red_team', lang=lang)} {t200_status}</div>
    </div>
    """ if not is_arena else ""

    css_styles, js_scripts = _load_static_assets()

    # Client-side i18n object for JS
    js_i18n = f"""
    <script>
        window.REPORT_I18N = {{
            copied: "{get_text('copied_btn', lang=lang)}",
            nav_prev_early: "{get_text('nav_prev_early', lang=lang)}",
            nav_prev_mid: "{get_text('nav_prev_mid', lang=lang)}",
            nav_next_mid: "{get_text('nav_next_mid', lang=lang)}",
            nav_next_late: "{get_text('nav_next_late', lang=lang)}",
            expand_timeline: "{get_text('expand_timeline', lang=lang)}",
            collapse_timeline: "{get_text('collapse_timeline', lang=lang)}",
            no_events: "{get_text('no_events_in_phase', lang=lang)}"
        }};
    </script>
    """

    # Inject stat icon CSS variables once in stylesheet to avoid repeating large strings in DOM
    from .asset_cache import AssetManager
    stat_vars = f"""
    :root {{
        --ico-hp: url('{AssetManager.get_asset_uri("stat_hp")}');
        --ico-hpregen: url('{AssetManager.get_asset_uri("stat_hpregen")}');
        --ico-ad: url('{AssetManager.get_asset_uri("stat_ad")}');
        --ico-ap: url('{AssetManager.get_asset_uri("stat_ap")}');
        --ico-armor: url('{AssetManager.get_asset_uri("stat_armor")}');
        --ico-mr: url('{AssetManager.get_asset_uri("stat_mr")}');
        --ico-as: url('{AssetManager.get_asset_uri("stat_as")}');
        --ico-ah: url('{AssetManager.get_asset_uri("stat_ah")}');
        --ico-crit: url('{AssetManager.get_asset_uri("stat_crit")}');
        --ico-armpen: url('{AssetManager.get_asset_uri("stat_armpen")}');
        --ico-mpen: url('{AssetManager.get_asset_uri("stat_mpen")}');
        --ico-lifesteal: url('{AssetManager.get_asset_uri("stat_lifesteal")}');
        --ico-omnivamp: url('{AssetManager.get_asset_uri("stat_omnivamp")}');
        --ico-ms: url('{AssetManager.get_asset_uri("stat_ms")}');
        --ico-range: url('{AssetManager.get_asset_uri("stat_range")}');
        --ico-tenacity: url('{AssetManager.get_asset_uri("stat_tenacity")}');
        --ico-gold: url('{AssetManager.get_asset_uri("gold_icon")}');
    }}
    """

    html_content = f"""<!DOCTYPE html>
<html lang="{get_text('html_lang_code', lang=lang)}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1100">
    <title>{browser_tab_title}</title>
    {favicon_link}
    <style>
        {stat_vars}
        {css_styles}
    </style>
</head>
<body>
    <div class="top-nav-bar">
        <div class="kofi-container" title="Support TBlazeWarriorT on ko-fi.com" data-tooltip="Support TBlazeWarriorT on ko-fi.com">
            <script type='text/javascript' src='https://storage.ko-fi.com/cdn/widget/Widget_2.js'></script><script type='text/javascript'>kofiwidget2.init('{get_text("kofi_btn", lang=lang)}', '#ea580c', 'Q5Q1IZ1W');kofiwidget2.draw();</script>
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
            <a href="/?lang={lang}" class="small-logo-link" style="text-decoration:none;" title="{get_text('tooltip_back_home', lang=lang)}">
                <span class="small-logo-title"><span class="fire-flame-anim">🔥</span> <span style="background:linear-gradient(90deg, #fb923c, #f97316, #ef4444); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Blaze GG</span> <span class="logo-author-badge">by TBlazeWarriorT</span></span>
            </a>
        </div>


        <div class="header" style="display:flex; align-items:center; gap:16px;">
            {header_main_info}
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
            {events_html}
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
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        pass

    import webbrowser
    if open_browser:
        try:
            webbrowser.open(REPORT_FILE.as_uri())
        except Exception:
            pass

    return html_content
