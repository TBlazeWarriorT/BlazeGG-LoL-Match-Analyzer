from typing import Dict, Any, Optional, List
from .ddragon import DataDragon

def format_timestamp(ms: int) -> str:
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def parse_time_str(time_str: str) -> int:
    parts = time_str.strip().split(":")
    if len(parts) == 2:
        return (int(parts[0]) * 60 + int(parts[1])) * 1000
    elif len(parts) == 1:
        return int(parts[0]) * 60 * 1000
    return 0

class MatchAnalysis:
    def __init__(self, match_data: Dict[str, Any], timeline_data: Dict[str, Any], target_puuid: Optional[str] = None, ddragon: Optional[DataDragon] = None):
        self.match = match_data
        self.timeline = timeline_data
        self.target_puuid = target_puuid
        self.ddragon = ddragon or DataDragon()
        self.info = self.match.get("info", {})
        self.participants = self.info.get("participants", [])
        self.target_participant = self._find_target_participant()
        self.laner_participant = self._find_lane_opponent()

    def _find_target_participant(self) -> Optional[Dict[str, Any]]:
        if not self.target_puuid:
            return self.participants[0] if self.participants else None
        for p in self.participants:
            if p.get("puuid") == self.target_puuid:
                return p
        return None

    def _find_lane_opponent(self) -> Optional[Dict[str, Any]]:
        if not self.target_participant:
            return None
        target_role = self.target_participant.get("individualPosition") or self.target_participant.get("teamPosition")
        target_team = self.target_participant.get("teamId")
        for p in self.participants:
            if p.get("teamId") != target_team:
                p_role = p.get("individualPosition") or p.get("teamPosition")
                if p_role and p_role == target_role and p_role != "Invalid":
                    return p
        return None

    def generate_summary(self) -> Dict[str, Any]:
        p = self.target_participant
        if not p:
            return {"error": "Jogador alvo não encontrado na partida"}

        opp = self.laner_participant
        duration_s = self.info.get("gameDuration", 0)
        minutes = duration_s // 60
        seconds = duration_s % 60

        total_damage = p.get("totalDamageDealtToChampions", 0)
        gold_earned = p.get("goldEarned", 1)
        dmg_per_gold = round(total_damage / max(gold_earned, 1), 2)

        # Team stats p/ KP
        team_id = p.get("teamId")
        team_kills = sum(other.get("kills", 0) for other in self.participants if other.get("teamId") == team_id)
        kp_pct = round(((p.get("kills", 0) + p.get("assists", 0)) / max(team_kills, 1)) * 100, 1)

        summary = {
            "match_id": self.match.get("metadata", {}).get("matchId"),
            "game_mode": self.info.get("gameMode"),
            "duration": f"{minutes}m {seconds}s",
            "win": p.get("win"),
            "target": {
                "riot_id": f"{p.get('riotIdGameName', '')}#{p.get('riotIdTagline', '')}",
                "champion": p.get("championName"),
                "role": p.get("teamPosition"),
                "kda": f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
                "cs": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
                "gold_total": gold_earned,
                "damage_to_champions": total_damage,
                "damage_taken": p.get("totalDamageTaken", 0),
                "damage_mitigated": p.get("damageSelfMitigated", 0),
                "damage_per_gold": dmg_per_gold,
                "kill_participation_pct": kp_pct,
                "vision_score": p.get("visionScore", 0),
                "items": [self.ddragon.get_item_name(p.get(f"item{i}", 0)) for i in range(7) if p.get(f"item{i}", 0) > 0]
            },
            "opponent": None,
            "lane_stats": self._calculate_lane_timeline_stats(),
            "key_events": self._extract_key_events()
        }

        if opp:
            opp_dmg = opp.get("totalDamageDealtToChampions", 0)
            opp_gold = opp.get("goldEarned", 1)
            summary["opponent"] = {
                "riot_id": f"{opp.get('riotIdGameName', '')}#{opp.get('riotIdTagline', '')}",
                "champion": opp.get("championName"),
                "kda": f"{opp.get('kills')}/{opp.get('deaths')}/{opp.get('assists')}",
                "cs": opp.get("totalMinionsKilled", 0) + opp.get("neutralMinionsKilled", 0),
                "gold_total": opp_gold,
                "damage_to_champions": opp_dmg,
                "damage_per_gold": round(opp_dmg / max(opp_gold, 1), 2),
                "items": [self.ddragon.get_item_name(opp.get(f"item{i}", 0)) for i in range(7) if opp.get(f"item{i}", 0) > 0]
            }

        return summary

    def _calculate_lane_timeline_stats(self) -> Dict[str, Any]:
        if not self.timeline or not self.target_participant:
            return {}

        target_id = self.target_participant.get("participantId")
        opp_id = self.laner_participant.get("participantId") if self.laner_participant else None

        solo_deaths = 0
        gank_deaths = 0
        solo_kills = 0

        frames = self.timeline.get("info", {}).get("frames", [])
        gold_at_min = {}

        for minute_idx in [5, 10, 15, 20]:
            if minute_idx < len(frames):
                p_frame = frames[minute_idx].get("participantFrames", {}).get(str(target_id), {})
                t_gold = p_frame.get("totalGold", 0)
                o_gold = 0
                if opp_id:
                    o_frame = frames[minute_idx].get("participantFrames", {}).get(str(opp_id), {})
                    o_gold = o_frame.get("totalGold", 0)
                gold_at_min[f"min_{minute_idx}"] = {
                    "target_gold": t_gold,
                    "opponent_gold": o_gold,
                    "delta": t_gold - o_gold
                }

        # Kills breakdown
        for frame in frames:
            for ev in frame.get("events", []):
                ev_type = ev.get("type")
                if ev_type == "CHAMPION_KILL":
                    victim = ev.get("victimId")
                    killer = ev.get("killerId")
                    assisters = ev.get("assistingParticipantIds", [])
                    if victim == target_id:
                        if len(assisters) == 0 and (opp_id is None or killer == opp_id):
                            solo_deaths += 1
                        else:
                            gank_deaths += 1
                    elif killer == target_id:
                        if len(assisters) == 0 and (opp_id is None or victim == opp_id):
                            solo_kills += 1

        return {
            "solo_deaths_in_lane": solo_deaths,
            "deaths_in_skirmish_or_gank": gank_deaths,
            "solo_kills_in_lane": solo_kills,
            "gold_diff_timeline": gold_at_min
        }

    def _extract_key_events(self) -> List[str]:
        if not self.timeline or not self.target_participant:
            return []
        events_log = []
        target_id = self.target_participant.get("participantId")
        frames = self.timeline.get("info", {}).get("frames", [])

        for frame in frames:
            for ev in frame.get("events", []):
                ev_type = ev.get("type")
                t_str = format_timestamp(ev.get("timestamp", 0))

                if ev_type == "CHAMPION_KILL":
                    victim = ev.get("victimId")
                    killer = ev.get("killerId")
                    assisters = ev.get("assistingParticipantIds", [])
                    v_name = self._get_part_name(victim)
                    k_name = self._get_part_name(killer)

                    if victim == target_id:
                        if len(assisters) == 0:
                            events_log.append(f"[{t_str}] Morreu SOLO para {k_name}")
                        else:
                            events_log.append(f"[{t_str}] Morreu para {k_name} (Ajuda: {len(assisters)} inimigos)")
                    elif killer == target_id:
                        if len(assisters) == 0:
                            events_log.append(f"[{t_str}] Matou SOLO {v_name}")
                        else:
                            events_log.append(f"[{t_str}] Matou {v_name}")

                elif ev_type == "ELITE_MONSTER_KILL":
                    m_type = ev.get("monsterType")
                    m_sub = ev.get("monsterSubType", "")
                    killer = ev.get("killerId")
                    k_name = self._get_part_name(killer)
                    desc = f"{m_type} ({m_sub})" if m_sub else m_type
                    events_log.append(f"[{t_str}] {desc} abatido por {k_name}")

        return events_log[:15]

    def filter_timeframe(self, start_time: str, end_time: str) -> List[str]:
        start_ms = parse_time_str(start_time)
        end_ms = parse_time_str(end_time)
        events_log = []
        frames = self.timeline.get("info", {}).get("frames", [])

        for frame in frames:
            for ev in frame.get("events", []):
                ts = ev.get("timestamp", 0)
                if start_ms <= ts <= end_ms:
                    t_str = format_timestamp(ts)
                    ev_type = ev.get("type")
                    if ev_type == "CHAMPION_KILL":
                        v_name = self._get_part_name(ev.get("victimId"))
                        k_name = self._get_part_name(ev.get("killerId"))
                        events_log.append(f"[{t_str}] KILL: {k_name} abateu {v_name}")
                    elif ev_type == "ITEM_PURCHASED":
                        p_name = self._get_part_name(ev.get("participantId"))
                        item_name = self.ddragon.get_item_name(ev.get("itemId", 0))
                        events_log.append(f"[{t_str}] ITEM: {p_name} comprou {item_name}")
                    elif ev_type == "BUILDING_KILL":
                        b_type = ev.get("buildingType")
                        lane = ev.get("laneType", "")
                        events_log.append(f"[{t_str}] TORRE/OBJETIVO: {b_type} ({lane}) destruído")
                    elif ev_type == "ELITE_MONSTER_KILL":
                        m_type = ev.get("monsterType")
                        k_name = self._get_part_name(ev.get("killerId"))
                        events_log.append(f"[{t_str}] MONSTRO: {m_type} abatido por {k_name}")
        return events_log

    def _get_part_name(self, participant_id: int) -> str:
        for p in self.participants:
            if p.get("participantId") == participant_id:
                return f"{p.get('championName')} ({p.get('riotIdGameName', '')})"
        return f"P{participant_id}"
