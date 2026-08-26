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

ROLES_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

def get_dragon_asset_key(sub_type: str = "") -> str:
    sub = sub_type.upper()
    if "AIR" in sub:
        return "dragon_circle_air"
    elif "CHEMTECH" in sub:
        return "dragon_circle_chemtech"
    elif "EARTH" in sub:
        return "dragon_circle_earth"
    elif "FIRE" in sub:
        return "dragon_circle_fire"
    elif "HEXTECH" in sub:
        return "dragon_circle_hextech"
    elif "WATER" in sub:
        return "dragon_circle_water"
    return "dragon_circle"

class MatchAnalysis:
    def __init__(self, match_data: Dict[str, Any], timeline_data: Dict[str, Any], target_puuid: Optional[str] = None, ddragon: Optional[DataDragon] = None):
        self.match = match_data
        self.timeline = timeline_data
        self.target_puuid = target_puuid
        self.ddragon = ddragon or DataDragon()
        self.info = self.match.get("info", {})
        self.participants = self.info.get("participants", [])
        self.target_participant = self._find_target_participant()

    def _find_target_participant(self) -> Optional[Dict[str, Any]]:
        if not self.target_puuid:
            return self.participants[0] if self.participants else None
        for p in self.participants:
            if p.get("puuid") == self.target_puuid:
                return p
        return self.participants[0] if self.participants else None

    def _get_player_details(self, p: Dict[str, Any]) -> Dict[str, Any]:
        total_dmg = p.get("totalDamageDealtToChampions", 0)
        gold = p.get("goldEarned", 1)
        items = []
        for i in range(7):
            iid = p.get(f"item{i}", 0)
            if iid > 0:
                items.append({
                    "id": iid,
                    "name": self.ddragon.get_item_name(iid),
                    "icon": self.ddragon.get_item_icon_url(iid)
                })

        perks = p.get("perks", {}).get("styles", [])
        primary_rune = perks[0].get("selections", [{}])[0].get("perk", 0) if perks and perks[0].get("selections") else 0

        champ_name = p.get("championName", "")
        return {
            "participantId": p.get("participantId"),
            "puuid": p.get("puuid"),
            "teamId": p.get("teamId"),
            "riot_id": f"{p.get('riotIdGameName', '')}#{p.get('riotIdTagline', '')}",
            "champion": champ_name,
            "champion_icon": self.ddragon.get_champion_icon_url(champ_name),
            "role": p.get("teamPosition") or p.get("individualPosition", "UNKNOWN"),
            "kda": f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
            "kills": p.get("kills", 0),
            "deaths": p.get("deaths", 0),
            "assists": p.get("assists", 0),
            "cs": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
            "gold_total": gold,
            "damage_to_champions": total_dmg,
            "damage_taken": p.get("totalDamageTaken", 0),
            "damage_mitigated": p.get("damageSelfMitigated", 0),
            "total_heal": p.get("totalHeal", 0),
            "damage_per_gold": round(total_dmg / max(gold, 1), 2),
            "vision_score": p.get("visionScore", 0),
            "items": items,
            "primary_rune": primary_rune,
            "win": p.get("win", False)
        }

    def generate_full_analysis(self) -> Dict[str, Any]:
        duration_s = self.info.get("gameDuration", 0)
        minutes = duration_s // 60
        seconds = duration_s % 60

        players = [self._get_player_details(p) for p in self.participants]
        team_100 = [p for p in players if p["teamId"] == 100]
        team_200 = [p for p in players if p["teamId"] == 200]

        matchups = self._calculate_all_matchups(players)
        jungle_stats = self._calculate_jungle_objectives()

        return {
            "match_id": self.match.get("metadata", {}).get("matchId"),
            "game_mode": self.info.get("gameMode"),
            "duration": f"{minutes}m {seconds}s",
            "target_puuid": self.target_puuid,
            "team_100": {
                "win": team_100[0]["win"] if team_100 else False,
                "players": team_100
            },
            "team_200": {
                "win": team_200[0]["win"] if team_200 else False,
                "players": team_200
            },
            "matchups": matchups,
            "jungle_stats": jungle_stats,
            "timeline_curves": self._calculate_timeline_curves(players),
            "key_events": self._extract_key_events()
        }

    def _calculate_all_matchups(self, players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        frames = self.timeline.get("info", {}).get("frames", []) if self.timeline else []
        matchups = []

        p_by_role = {}
        for p in players:
            role = p["role"]
            if role not in p_by_role:
                p_by_role[role] = []
            p_by_role[role].append(p)

        for role in ROLES_ORDER:
            pair = p_by_role.get(role, [])
            if len(pair) == 2:
                p1, p2 = pair[0], pair[1]
                id1, id2 = p1["participantId"], p2["participantId"]

                p1_solo_deaths, p1_other_deaths, p1_solo_kills = 0, 0, 0
                p2_solo_deaths, p2_other_deaths, p2_solo_kills = 0, 0, 0

                for frame in frames:
                    for ev in frame.get("events", []):
                        if ev.get("type") == "CHAMPION_KILL":
                            vic = ev.get("victimId")
                            kil = ev.get("killerId")
                            ass = ev.get("assistingParticipantIds", [])
                            
                            if vic == id1:
                                if kil == id2 and len(ass) == 0:
                                    p1_solo_deaths += 1
                                    p2_solo_kills += 1
                                else:
                                    p1_other_deaths += 1
                            elif vic == id2:
                                if kil == id1 and len(ass) == 0:
                                    p2_solo_deaths += 1
                                    p1_solo_kills += 1
                                else:
                                    p2_other_deaths += 1

                gold_diff = {}
                xp_diff = {}
                for m in [5, 10, 15, 20]:
                    if m < len(frames):
                        f1 = frames[m].get("participantFrames", {}).get(str(id1), {})
                        f2 = frames[m].get("participantFrames", {}).get(str(id2), {})
                        gold_diff[f"{m}m"] = f1.get("totalGold", 0) - f2.get("totalGold", 0)
                        xp_diff[f"{m}m"] = f1.get("xp", 0) - f2.get("xp", 0)

                matchups.append({
                    "role": role,
                    "player1": p1,
                    "player2": p2,
                    "p1_stats": {"solo_deaths": p1_solo_deaths, "other_deaths": p1_other_deaths, "solo_kills": p1_solo_kills},
                    "p2_stats": {"solo_deaths": p2_solo_deaths, "other_deaths": p2_other_deaths, "solo_kills": p2_solo_kills},
                    "gold_delta": gold_diff,
                    "xp_delta": xp_diff
                })

        return matchups

    def _calculate_jungle_objectives(self) -> Dict[str, Any]:
        stats = {100: {"dragons": 0, "grubs": 0, "herald": 0, "baron": 0}, 200: {"dragons": 0, "grubs": 0, "herald": 0, "baron": 0}}
        if not self.timeline:
            return stats
        frames = self.timeline.get("info", {}).get("frames", [])
        for frame in frames:
            for ev in frame.get("events", []):
                if ev.get("type") == "ELITE_MONSTER_KILL":
                    m_type = ev.get("monsterType", "")
                    killer_id = ev.get("killerId", 0)
                    killer_team = None
                    for p in self.participants:
                        if p.get("participantId") == killer_id:
                            killer_team = p.get("teamId")
                            break
                    if killer_team in stats:
                        if "DRAGON" in m_type:
                            stats[killer_team]["dragons"] += 1
                        elif "HORDE" in m_type or "GRUB" in m_type:
                            stats[killer_team]["grubs"] += 1
                        elif "HERALD" in m_type:
                            stats[killer_team]["herald"] += 1
                        elif "BARON" in m_type:
                            stats[killer_team]["baron"] += 1
        return stats

    def _calculate_timeline_curves(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        frames = self.timeline.get("info", {}).get("frames", []) if self.timeline else []
        timeline_data = {p["participantId"]: {"champion": p["champion"], "gold": [], "xp": []} for p in players}
        for frame in frames:
            p_frames = frame.get("participantFrames", {})
            for pid_str, p_info in p_frames.items():
                pid = int(pid_str)
                if pid in timeline_data:
                    timeline_data[pid]["gold"].append(p_info.get("totalGold", 0))
                    timeline_data[pid]["xp"].append(p_info.get("xp", 0))
        return timeline_data

    def _extract_key_events(self) -> List[Dict[str, str]]:
        if not self.timeline:
            return []
        events_log = []
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

                    if len(assisters) == 0:
                        events_log.append({
                            "text": f"[{t_str}] <b>{k_name}</b> matou SOLO <b>{v_name}</b>",
                            "asset_key": None
                        })
                    else:
                        events_log.append({
                            "text": f"[{t_str}] <b>{k_name}</b> abateu <b>{v_name}</b> (Ajuda: {len(assisters)})",
                            "asset_key": None
                        })

                elif ev_type == "ELITE_MONSTER_KILL":
                    m_type = ev.get("monsterType", "")
                    m_sub = ev.get("monsterSubType", "")
                    killer = ev.get("killerId")
                    k_name = self._get_part_name(killer)
                    desc = f"{m_type} ({m_sub})" if m_sub else m_type
                    
                    asset_key = "dragon_circle"
                    if "DRAGON" in m_type:
                        asset_key = get_dragon_asset_key(m_sub)
                    elif "HORDE" in m_type or "GRUB" in m_type:
                        asset_key = "sru_voidgrub_circle"
                    elif "HERALD" in m_type:
                        asset_key = "sruriftherald_circle"
                    elif "BARON" in m_type:
                        asset_key = "baron_circle"

                    events_log.append({
                        "text": f"[{t_str}] <b>{desc}</b> abatido por <b>{k_name}</b>",
                        "asset_key": asset_key
                    })

        return events_log[:20]

    def _get_part_name(self, participant_id: int) -> str:
        for p in self.participants:
            if p.get("participantId") == participant_id:
                return f"{p.get('championName')} ({p.get('riotIdGameName', '')})"
        return f"P{participant_id}"
