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
    try:
        from ..ddragon import DataDragon
        dd = DataDragon(language=lang)
        return dd.get_queue_name(queue_id, lang=lang)
    except Exception:
        return get_text("queue_0" if queue_id == 0 else "queue_featured", lang=lang)

def format_full_mode_display(mode_str: str, queue_id: int = 0, lang: str = "en_US", player_count: int = 0) -> str:
    m_upper = str(mode_str).upper()
    # Arena mode distinction based on total player count
    if m_upper in ("CHERRY", "ARENA") or queue_id in (1700, 1710):
        if player_count == 18:
            return "Arena (3v3)"
        if player_count in (8, 12, 16) or (player_count > 0 and player_count % 2 == 0):
            return "Arena (2v2)"
        return "Arena"

    m_name = clean_mode_name(mode_str, lang=lang)
    q_name = get_queue_name(queue_id, lang=lang)
    if not q_name:
        return m_name
    # If mode is unknown or generic placeholder, prioritize the queue name cleanly
    if m_upper in ("UNKNOWN", "OTHER", "", "NONE"):
        return q_name
    if m_name.lower() == q_name.lower() or q_name.lower().startswith(m_name.lower()):
        return q_name
    return f"{m_name} ({q_name})"
