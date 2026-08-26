from ..i18n import get_text

def calculate_gold_bar_share(delta: int, max_delta: float = 5000.0) -> float:
    fraction = delta / float(max_delta)
    val = 50.0 + (fraction * 50.0)
    return max(4.0, min(96.0, val))

def clean_mode_name(mode_str: str) -> str:
    m = str(mode_str).upper()
    if m == "CLASSIC":
        return "Summoner's Rift"
    elif m == "ARAM":
        return "ARAM"
    elif m == "CHERRY":
        return "Arena"
    elif m == "URF":
        return "URF"
    return m.capitalize()

def get_queue_name(queue_id: int, lang: str = "pt_BR") -> str:
    queue_map = {
        420: "queue_ranked_solo",
        440: "queue_ranked_flex",
        400: "queue_normal_draft",
        430: "queue_normal_blind",
        450: "queue_aram",
        1700: "queue_arena",
        900: "queue_urf",
        1010: "queue_urf",
        1900: "queue_urf"
    }
    q_key = queue_map.get(queue_id, "")
    return get_text(q_key, lang=lang) if q_key else ""
