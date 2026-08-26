import json
from typing import Dict, Any, List

def format_as_llm_json(summary_data: Dict[str, Any]) -> str:
    return json.dumps(summary_data, ensure_ascii=False, indent=2)

def format_as_whatsapp_text(data: Dict[str, Any]) -> str:
    target = data.get("target", {})
    opp = data.get("opponent", {})
    lane = data.get("lane_stats", {})

    status = "[VITORIA]" if data.get("win") else "[DERROTA]"
    champ = target.get("champion", "Desconhecido")
    riot_id = target.get("riot_id", "")
    kda = target.get("kda", "0/0/0")
    cs = target.get("cs", 0)
    dmg = target.get("damage_to_champions", 0)
    dpg = target.get("damage_per_gold", 0)
    kp = target.get("kill_participation_pct", 0)
    vis = target.get("vision_score", 0)

    lines = [
        f"--- RELATORIO FACTUAL DE PARTIDA ---",
        f"* Resultado: {status} ({data.get('duration')})",
        f"* Jogador: {riot_id} de *{champ}*",
        f"* KDA: `{kda}` | *CS*: {cs}",
        f"* Dano: {dmg:,} (*{dpg}* de dano/ouro)",
        f"* Participacao em Kills: {kp}%",
        f"* Visao: {vis}",
        ""
    ]

    if opp:
        o_champ = opp.get("champion")
        o_kda = opp.get("kda")
        o_dmg = opp.get("damage_to_champions", 0)
        lines.extend([
            f"--- MATCHUP DE LANE vs {o_champ} ---",
            f"* KDA Oponente: `{o_kda}` | *Dano*: {o_dmg:,}",
            f"* Mortes Solo na Lane: {lane.get('solo_deaths_in_lane', 0)}",
            f"* Mortes p/ Gank: {lane.get('deaths_in_skirmish_or_gank', 0)}",
            f"* Kills Solo na Lane: {lane.get('solo_kills_in_lane', 0)}",
            ""
        ])

    gold_diffs = lane.get("gold_diff_timeline", {})
    if gold_diffs:
        lines.append("--- DIFERENCA DE OURO (Delta Gold) ---")
        for minute, diff_info in gold_diffs.items():
            min_num = minute.replace("min_", "")
            delta = diff_info.get("delta", 0)
            sign = "+" if delta >= 0 else ""
            lines.append(f"* Aos {min_num}m: `{sign}{delta}g`")
        lines.append("")

    key_events = data.get("key_events", [])
    if key_events:
        lines.append("--- MOMENTOS CHAVE ---")
        for ev in key_events[:8]:
            lines.append(f"* {ev}")

    return "\n".join(lines)

def format_timeframe_events(events: List[str], start_time: str, end_time: str) -> str:
    if not events:
        return f"Nenhum evento relevante registrado entre {start_time} e {end_time}."
    header = f"--- TIMEFRAME FACTUAL ({start_time} - {end_time}) ---\n"
    body = "\n".join(f"* {ev}" for ev in events)
    return header + body
