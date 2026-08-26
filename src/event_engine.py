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

def calculate_kda_ratio(k: int, d: int, a: int) -> str:
    if d == 0:
        return "Perfect"
    ratio = (k + a) / d
    return f"{ratio:.2f}:1"

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

def clean_monster_name(monster_type: str, sub_type: str = "", lang: str = "pt_BR") -> str:
    from .i18n import get_text
    m = monster_type.upper()
    s = sub_type.upper()
    if "DRAGON" in m:
        element_map = {
            "FIRE_DRAGON": "dragon_infernal",
            "EARTH_DRAGON": "dragon_mountain",
            "WATER_DRAGON": "dragon_ocean",
            "AIR_DRAGON": "dragon_cloud",
            "CHEMTECH_DRAGON": "dragon_chemtech",
            "HEXTECH_DRAGON": "dragon_hextech",
            "ELDER_DRAGON": "dragon_elder"
        }
        key = element_map.get(s, "dragon_elemental")
        return get_text(key, lang=lang)
    elif "HORDE" in m or "GRUB" in m:
        return get_text("grub", lang=lang)
    elif "HERALD" in m:
        return get_text("herald", lang=lang)
    elif "BARON" in m:
        return get_text("baron", lang=lang)
    return monster_type

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

        raw_champ = p.get("championName", "")
        champ_name = self.ddragon.get_clean_champion_name(raw_champ)
        k = p.get("kills", 0)
        d = p.get("deaths", 0)
        a = p.get("assists", 0)
        cs = p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
        dur_m = max(self.info.get("gameDuration", 0) / 60.0, 1.0)
        cs_per_min = round(cs / dur_m, 1)

        # Spells
        s1_id = p.get("summoner1Id", 0)
        s2_id = p.get("summoner2Id", 0)
        s1_info = self.ddragon.get_spell_info(s1_id)
        s2_info = self.ddragon.get_spell_info(s2_id)

        # Keystone Rune
        perk_id = 0
        perks_styles = p.get("perks", {}).get("styles", [])
        if perks_styles and len(perks_styles) > 0:
            selections = perks_styles[0].get("selections", [])
            if selections and len(selections) > 0:
                perk_id = selections[0].get("perk", 0)
        rune_info = self.ddragon.get_rune_info(perk_id) if perk_id else {"name": "", "icon": ""}

        return {
            "participantId": p.get("participantId"),
            "puuid": p.get("puuid"),
            "teamId": p.get("teamId"),
            "riot_id": f"{p.get('riotIdGameName', '')}#{p.get('riotIdTagline', '')}",
            "champion": champ_name,
            "champion_raw": raw_champ,
            "champion_icon": self.ddragon.get_champion_icon_url(raw_champ),
            "role": p.get("teamPosition") or p.get("individualPosition", "UNKNOWN"),
            "kda": f"{k}/{d}/{a}",
            "kda_ratio": calculate_kda_ratio(k, d, a),
            "kills": k,
            "deaths": d,
            "assists": a,
            "cs": cs,
            "cs_per_min": cs_per_min,
            "gold_total": gold,
            "damage_to_champions": total_dmg,
            "damage_physical": p.get("physicalDamageDealtToChampions", 0),
            "damage_magic": p.get("magicDamageDealtToChampions", 0),
            "damage_true": p.get("trueDamageDealtToChampions", 0),
            "damage_to_turrets": p.get("damageDealtToTurrets", 0),
            "damage_taken": p.get("totalDamageTaken", 0),
            "damage_mitigated": p.get("damageSelfMitigated", 0),
            "total_heal": p.get("totalHeal", 0),
            "damage_per_gold": round(total_dmg / max(gold, 1), 2),
            "vision_score": p.get("visionScore", 0),
            "detector_wards": p.get("detectorWardsPlaced", 0),
            "enemy_jungle_monsters": p.get("totalEnemyJungleMinionsKilled", 0) or p.get("challenges", {}).get("enemyJungleMonsterKills", 0),
            "spells": [s1_info, s2_info],
            "rune": rune_info,
            "items": items,
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

        analysis_dict = {
            "match_id": self.match.get("metadata", {}).get("matchId"),
            "game_mode": self.info.get("gameMode"),
            "queue_id": self.info.get("queueId", 0),
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
            "all_objectives": self._extract_all_objectives(),
            "key_events": self._extract_key_events()
        }
        analysis_dict["raw_summary_text"] = self._generate_compact_raw_summary(analysis_dict)
        return analysis_dict

    def _generate_compact_raw_summary(self, data: Dict[str, Any]) -> str:
        lines = []
        winner = "BLUE" if data["team_100"]["win"] else "RED"
        lines.append(f"MATCH: {data['match_id']} | DURATION: {data['duration']} | WINNER: {winner}")

        # 1. OBJETIVOS PRINCIPAIS
        j1 = data["jungle_stats"].get(100, {}).get("timeline_sequence", [])
        j2 = data["jungle_stats"].get(200, {}).get("timeline_sequence", [])
        j1_str = ", ".join([f"{x['name']}({x['time']})" for x in j1]) or "None"
        j2_str = ", ".join([f"{x['name']}({x['time']})" for x in j2]) or "None"
        lines.append(f"\n[OBJECTIVES]\n• Blue Team: {j1_str}\n• Red Team: {j2_str}")

        # 2. CONFRONTOS DE LANE E DELTAS
        lines.append("\n[LANE MATCHUPS & GOLD DELTAS (Blue vs Red)]")
        for m in data["matchups"]:
            p1, p2 = m["player1"], m["player2"]
            g_tags = " ".join([f"{k}:{v:+d}g" for k, v in m["gold_delta"].items()])
            lines.append(f"• {m['role']} ({p1['champion']} vs {p2['champion']}): {g_tags} | SoloKills: {m['p1_stats']['solo_kills']}x{m['p2_stats']['solo_kills']} | GankDeaths: {m['p1_stats']['other_deaths']}x{m['p2_stats']['other_deaths']}")

        # 3. JOGADORES (Blue & Red)
        def format_team_players(team_key, team_name):
            t_lines = [f"\n[{team_name} TEAM]"]
            for p in data[team_key]["players"]:
                items_str = ", ".join([it["name"] for it in p["items"]]) or "None"
                t_lines.append(f"• {p['role']} {p['champion']} ({p['riot_id']}): KDA {p['kda']} | CS {p['cs']} | DMG {p['damage_to_champions']:,} | GOLD {p['gold_total']:,} | ITEMS: {items_str}")
            return t_lines

        lines.extend(format_team_players("team_100", "BLUE"))
        lines.extend(format_team_players("team_200", "RED"))

        # 4. DESTAQUES (Pentakills & Multikills)
        highlights = []
        for ev in data.get("key_events", []):
            streak = ev.get("streak", "normal")
            if streak == "penta":
                highlights.append(f"[{ev['time']}] PENTAKILL por {ev['killer_champ']} ({ev['killer_name']})")
            elif streak == "quadra":
                highlights.append(f"[{ev['time']}] QUADRA KILL por {ev['killer_champ']} ({ev['killer_name']})")
            elif streak == "triple":
                highlights.append(f"[{ev['time']}] TRIPLE KILL por {ev['killer_champ']} ({ev['killer_name']})")
        if highlights:
            lines.append("\n[HIGHLIGHTS]")
            lines.extend([f"• {h}" for h in highlights])

        full_text = "\n".join(lines)
        return full_text

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
        stats = {
            100: {"timeline_sequence": []},
            200: {"timeline_sequence": []}
        }
        if not self.timeline:
            return stats
        drake_count_by_team = {100: 0, 200: 0}
        frames = self.timeline.get("info", {}).get("frames", [])
        for frame in frames:
            for ev in frame.get("events", []):
                if ev.get("type") == "ELITE_MONSTER_KILL":
                    m_type = ev.get("monsterType", "")
                    m_sub = ev.get("monsterSubType", "")
                    t_str = format_timestamp(ev.get("timestamp", 0))
                    killer_id = ev.get("killerId", 0)
                    killer_team = None
                    for p in self.participants:
                        if p.get("participantId") == killer_id:
                            killer_team = p.get("teamId")
                            break
                    if not killer_team and ev.get("killerTeamId") in (100, 200):
                        killer_team = ev.get("killerTeamId")

                    if killer_team in stats:
                        asset_key = "dragon_circle"
                        is_soul = False
                        if "DRAGON" in m_type:
                            if "ELDER" not in str(m_sub).upper():
                                drake_count_by_team[killer_team] += 1
                                if drake_count_by_team[killer_team] == 4:
                                    is_soul = True
                            asset_key = get_dragon_asset_key(m_sub)
                        elif "HORDE" in m_type or "GRUB" in m_type:
                            asset_key = "sru_voidgrub_circle"
                        elif "HERALD" in m_type:
                            asset_key = "sruriftherald_circle"
                        elif "BARON" in m_type:
                            asset_key = "baron_circle"

                        clean_name = clean_monster_name(m_type, m_sub)
                        if is_soul:
                            clean_name = f"{clean_name} (SOUL 🐉)"

                        stats[killer_team]["timeline_sequence"].append({
                            "time": t_str,
                            "name": clean_name,
                            "asset_key": asset_key,
                            "is_soul": is_soul
                        })
        return stats

    def _extract_key_events(self) -> List[Dict[str, Any]]:
        if not self.timeline:
            return []
        events_log = []
        frames = self.timeline.get("info", {}).get("frames", [])
        kill_streaks = {}

        for frame in frames:
            for ev in frame.get("events", []):
                ev_type = ev.get("type")
                ts = ev.get("timestamp", 0)
                t_str = format_timestamp(ts)

                if ev_type == "CHAMPION_KILL":
                    victim = ev.get("victimId")
                    killer = ev.get("killerId")
                    assisters = ev.get("assistingParticipantIds", [])
                    v_p = self._get_part_dict(victim)
                    k_p = self._get_part_dict(killer)

                    streak_type = "normal"
                    killer_streak = kill_streaks.get(killer, {"count": 0, "last_ts": 0})
                    current_count = killer_streak["count"]
                    last_ts = killer_streak["last_ts"]

                    # Janela padrão de 10s entre abates; se for Quadra Kill (4 kills), a janela para Pentakill sobe para 30s
                    allowed_window = 30000 if current_count == 4 else 10000

                    if current_count > 0 and (ts - last_ts) <= allowed_window:
                        new_count = current_count + 1
                    else:
                        new_count = 1

                    kill_streaks[killer] = {"count": new_count, "last_ts": ts}

                    if new_count >= 5:
                        streak_type = "penta"
                    elif new_count == 4:
                        streak_type = "quadra"
                    elif new_count == 3:
                        streak_type = "triple"
                    elif new_count == 2:
                        streak_type = "double"

                    is_solo = len(assisters) == 0
                    k_raw = k_p.get("championName", "")
                    v_raw = v_p.get("championName", "")
                    events_log.append({
                        "type": "kill",
                        "streak": streak_type,
                        "time": t_str,
                        "killer_champ": self.ddragon.get_clean_champion_name(k_raw),
                        "killer_icon": self.ddragon.get_champion_icon_url(k_raw),
                        "killer_name": k_p.get("riotIdGameName", ""),
                        "victim_champ": self.ddragon.get_clean_champion_name(v_raw),
                        "victim_icon": self.ddragon.get_champion_icon_url(v_raw),
                        "victim_name": v_p.get("riotIdGameName", ""),
                        "is_solo": is_solo,
                        "assists_count": len(assisters),
                        "assisters": [self.ddragon.get_clean_champion_name(self._get_part_dict(aid).get("championName", "")) for aid in assisters]
                    })

                elif ev_type == "ELITE_MONSTER_KILL":
                    m_type = ev.get("monsterType", "")
                    m_sub = ev.get("monsterSubType", "")
                    killer = ev.get("killerId")
                    k_p = self._get_part_dict(killer)
                    desc = clean_monster_name(m_type, m_sub)
                    
                    asset_key = "dragon_circle"
                    if "DRAGON" in m_type:
                        asset_key = get_dragon_asset_key(m_sub)
                    elif "HORDE" in m_type or "GRUB" in m_type:
                        asset_key = "sru_voidgrub_circle"
                    elif "HERALD" in m_type:
                        asset_key = "sruriftherald_circle"
                    elif "BARON" in m_type:
                        asset_key = "baron_circle"

                    k_raw = k_p.get("championName", "")
                    events_log.append({
                        "type": "objective",
                        "time": t_str,
                        "monster_type": m_type,
                        "monster_sub_type": m_sub,
                        "desc": desc,
                        "asset_key": asset_key,
                        "killer_champ": self.ddragon.get_clean_champion_name(k_raw),
                        "killer_icon": self.ddragon.get_champion_icon_url(k_raw),
                        "killer_name": k_p.get("riotIdGameName", "")
                    })

        return events_log

    def _extract_all_objectives(self) -> List[Dict[str, Any]]:
        if not self.timeline:
            return []
        obj_list = []
        frames = self.timeline.get("info", {}).get("frames", [])
        for frame in frames:
            for ev in frame.get("events", []):
                if ev.get("type") == "ELITE_MONSTER_KILL":
                    m_type = ev.get("monsterType", "")
                    m_sub = ev.get("monsterSubType", "")
                    killer = ev.get("killerId", 0)
                    k_p = self._get_part_dict(killer)
                    k_raw = k_p.get("championName", "")
                    k_name = k_p.get("riotIdGameName", "")
                    k_champ = self.ddragon.get_clean_champion_name(k_raw)
                    obj_list.append({
                        "time": format_timestamp(ev.get("timestamp", 0)),
                        "type": m_type,
                        "sub_type": m_sub,
                        "killer_id": killer,
                        "killer_champ": k_champ,
                        "killer_name": k_name,
                        "killer_team": ev.get("killerTeamId", 0),
                        "assisting_participant_ids": ev.get("assistingParticipantIds", [])
                    })
        return obj_list

    def _get_part_dict(self, participant_id: int) -> Dict[str, Any]:
        for p in self.participants:
            if p.get("participantId") == participant_id:
                return p
        return {}
