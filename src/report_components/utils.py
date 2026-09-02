from ..i18n import get_text

def calculate_gold_bar_share(delta: int, max_delta: float = 5000.0) -> float:
    fraction = delta / float(max_delta)
    val = 50.0 + (fraction * 50.0)
    return max(4.0, min(96.0, val))

def clean_mode_name(mode_str: str, lang: str = "en_US") -> str:
    m = str(mode_str).upper()
    mode_keys = {
        "CLASSIC": "mode_classic",
        "SWIFTPLAY": "mode_classic",
        "QUICKPLAY": "mode_classic",
        "LEAGUE_CLASSIC": "mode_league_classic",
        "ARAM": "mode_aram",
        "CHERRY": "mode_cherry",
        "ARENA": "mode_arena",
        "URF": "mode_urf",
        "ARURF": "mode_arurf",
        "ONEFORALL": "mode_oneforall",
        "NEXUSBLITZ": "mode_nexusblitz",
        "ULTBOOK": "mode_ultbook",
        "SWARM": "mode_swarm",
        "STRAWBERRY": "mode_swarm",
        "COOP": "mode_coop",
        "BOT": "mode_coop",
        "TUTORIAL": "mode_tutorial",
        "CUSTOM": "mode_custom",
        "PRACTICETOOL": "mode_custom"
    }
    if m in mode_keys:
        return get_text(mode_keys[m], lang=lang)
    return m.capitalize()

def get_queue_name(queue_id: int, lang: str = "en_US") -> str:
    queue_map = {
        0: "queue_custom",
        76: "queue_urf",
        400: "queue_normal_draft",
        420: "queue_ranked_solo",
        430: "queue_normal_blind",
        440: "queue_ranked_flex",
        450: "queue_aram",
        480: "queue_quickplay",
        490: "queue_quickplay",
        700: "queue_clash",
        720: "queue_clash",
        830: "queue_coop_ai",
        840: "queue_coop_ai",
        850: "queue_coop_ai",
        870: "queue_coop_ai",
        880: "queue_coop_ai",
        890: "queue_coop_ai",
        900: "queue_arurf",
        950: "queue_doom_bots",
        960: "queue_doom_bots",
        1010: "queue_arurf",
        1020: "queue_one_for_all",
        1300: "queue_nexus_blitz",
        1400: "queue_ultimate_spellbook",
        1700: "queue_arena",
        1710: "queue_arena",
        1810: "queue_swarm",
        1820: "queue_swarm",
        1830: "queue_swarm",
        1840: "queue_swarm",
        1900: "queue_urf",
        1920: "queue_league_classic",
        2000: "queue_tutorial",
        2010: "queue_tutorial",
        2020: "queue_tutorial",
        2300: "queue_brawl",
        2400: "queue_aram_mayhem"
    }
    q_key = queue_map.get(queue_id, "")
    if q_key:
        return get_text(q_key, lang=lang)
    
    # Fallback to official Riot queues.json description
    try:
        from ..ddragon import DataDragon
        dd = DataDragon(language=lang)
        raw_desc = dd.get_queue_raw_description(queue_id)
        if raw_desc:
            return raw_desc
    except Exception:
        pass

    return get_text("queue_featured" if queue_id != 0 else "queue_custom", lang=lang)

def format_full_mode_display(mode_str: str, queue_id: int = 0, lang: str = "en_US") -> str:
    m_name = clean_mode_name(mode_str, lang=lang)
    q_name = get_queue_name(queue_id, lang=lang)
    if not q_name:
        return m_name
    # If mode is unknown or generic placeholder, prioritize the queue name cleanly
    m_upper = str(mode_str).upper()
    if m_upper in ("UNKNOWN", "OTHER", "", "NONE"):
        return q_name
    if m_name.lower() == q_name.lower() or q_name.lower().startswith(m_name.lower()):
        return q_name
    return f"{m_name} ({q_name})"
