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
                    "icon": self.ddragon.get_item_icon_url(iid),
                    "tooltip": self.ddragon.get_item_tooltip(iid),
                    "is_role_bound": False
                })

        # Riot sends quest boots/role-bound items in roleBoundItem
        role_bound_iid = p.get("roleBoundItem", 0)
        if role_bound_iid > 0:
            items.append({
                "id": role_bound_iid,
                "name": self.ddragon.get_item_name(role_bound_iid),
                "icon": self.ddragon.get_item_icon_url(role_bound_iid),
                "tooltip": self.ddragon.get_item_tooltip(role_bound_iid),
                "is_role_bound": True
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

        # Keystone Rune, Full Rune Tree & Secondary Tree
        perk_id = 0
        sub_style_id = 0
        primary_style_id = 0
        selected_perks_list = []
        stat_perks_list = []

        perks_obj = p.get("perks", {})
        stat_perks_obj = perks_obj.get("statPerks", {})
        if stat_perks_obj:
            stat_perks_list = [
                stat_perks_obj.get("offense", 0),
                stat_perks_obj.get("flex", 0),
                stat_perks_obj.get("defense", 0)
            ]
        perks_styles = perks_obj.get("styles", [])
        if perks_styles and len(perks_styles) > 0:
            primary_style_id = perks_styles[0].get("style", 0)
            selections = perks_styles[0].get("selections", [])
            for sel in selections:
                pid_val = sel.get("perk", 0)
                if pid_val:
                    selected_perks_list.append(pid_val)
            if selected_perks_list:
                perk_id = selected_perks_list[0]
        if perks_styles and len(perks_styles) > 1:
            sub_style_id = perks_styles[1].get("style", 0)
            selections_sub = perks_styles[1].get("selections", [])
            for sel in selections_sub:
                pid_val = sel.get("perk", 0)
                if pid_val:
                    selected_perks_list.append(pid_val)

        perks_data = {
            "primary_style": primary_style_id,
            "sub_style": sub_style_id,
            "selected_perks": selected_perks_list,
            "stat_perks": [sp for sp in stat_perks_list if sp]
        }
        full_rune_tree_tooltip = self.ddragon.get_full_rune_tree_tooltip(perks_data)
        rune_info = self.ddragon.get_rune_info(perk_id) if perk_id else {"name": "", "icon": ""}
        sub_rune_info = self.ddragon.get_rune_style_info(sub_style_id) if sub_style_id else {"name": "", "icon": ""}

        # Arena Augments
        augments = []
        for a_idx in range(1, 7):
            aid = p.get(f"playerAugment{a_idx}", 0)
            if aid and aid > 0:
                aug_info = self.ddragon.get_augment_info(aid)
                if aug_info:
                    augments.append(aug_info)

        # Executions count and final frame championStats from timeline
        exec_count = 0
        final_stats = {}
        frames = self.timeline.get("info", {}).get("frames", []) if self.timeline else []
        if frames:
            last_p_frames = frames[-1].get("participantFrames", {})
            p_pid_str = str(p.get("participantId"))
            final_stats = last_p_frames.get(p_pid_str, {}).get("championStats", {})

        purchased_anvils = 0
        for frame in frames:
            for ev in frame.get("events", []):
                ev_type = ev.get("type")
                if ev_type == "CHAMPION_KILL" and ev.get("victimId") == p.get("participantId"):
                    kil = ev.get("killerId", 0)
                    ass = ev.get("assistingParticipantIds", [])
                    if kil == 0 and not ass:
                        exec_count += 1
                elif ev_type == "ITEM_PURCHASED" and ev.get("participantId") == p.get("participantId"):
                    iid = ev.get("itemId", 0)
                    if iid in (220000, 220008, 220009, 220010, 6032):
                        purchased_anvils += 1
                    else:
                        iname = self.ddragon.get_item_name(iid).lower()
                        if "stat bonus" in iname or "atributo adicional" in iname or "bigorna" in iname or "anvil" in iname:
                            purchased_anvils += 1

        return {
            "participantId": p.get("participantId"),
            "puuid": p.get("puuid"),
            "final_stats": final_stats,
            "teamId": p.get("teamId"),
            "riot_id": f"{p.get('riotIdGameName', '')}#{p.get('riotIdTagline', '')}",
            "champion": champ_name,
            "champion_raw": raw_champ,
            "champion_icon": self.ddragon.get_champion_icon_url(raw_champ),
            "role": (
                ""
                if str(p.get("teamPosition") or p.get("individualPosition") or "").strip().upper() in ["", "INVALID", "UNKNOWN"]
                else str(p.get("teamPosition") or p.get("individualPosition", "")).strip().upper()
            ),
            "champ_level": p.get("champLevel", 1),
            "kda": f"{k}/{d}/{a}",
            "executions": exec_count,
            "kda_ratio": calculate_kda_ratio(k, d, a),
            "kills": k,
            "deaths": d,
            "assists": a,
            "cs": cs,
            "cs_per_min": cs_per_min,
            "minions_killed": p.get("totalMinionsKilled", 0),
            "neutral_minions_killed": p.get("neutralMinionsKilled", 0),
            "ally_jungle_monsters": p.get("totalAllyJungleMinionsKilled", 0),
            "enemy_jungle_monsters": p.get("totalEnemyJungleMinionsKilled", 0) or p.get("challenges", {}).get("enemyJungleMonsterKills", 0),
            "gold_total": gold,
            "gold_spent": p.get("goldSpent", 0),
            "damage_total_all": p.get("totalDamageDealt", 0),
            "damage_to_champions": total_dmg,
            "damage_physical": p.get("physicalDamageDealtToChampions", 0),
            "damage_magic": p.get("magicDamageDealtToChampions", 0),
            "damage_true": p.get("trueDamageDealtToChampions", 0),
            "damage_to_turrets": p.get("damageDealtToTurrets", 0),
            "damage_to_buildings": p.get("damageDealtToBuildings", 0),
            "damage_to_objectives": p.get("damageDealtToObjectives", 0),
            "turret_kills": p.get("turretKills", 0),
            "inhibitor_kills": p.get("inhibitorKills", 0),
            "damage_taken": p.get("totalDamageTaken", 0),
            "damage_taken_physical": p.get("physicalDamageTaken", 0),
            "damage_taken_magic": p.get("magicDamageTaken", 0),
            "damage_taken_true": p.get("trueDamageTaken", 0),
            "damage_mitigated": p.get("damageSelfMitigated", 0),
            "total_heal": p.get("totalHeal", 0),
            "damage_per_gold": round(total_dmg / max(gold, 1), 2),
            "time_ccing_others": p.get("timeCCingOthers", 0),
            "total_time_cc_dealt": p.get("totalTimeCCDealt", 0),
            "largest_multikill": p.get("largestMultiKill", 1),
            "largest_killing_spree": p.get("largestKillingSpree", 0),
            "largest_critical_strike": p.get("largestCriticalStrike", 0),
            "vision_score": p.get("visionScore", 0),
            "detector_wards": p.get("detectorWardsPlaced", 0),
            "vision_wards_bought": p.get("visionWardsBoughtInGame", 0),
            "wards_placed": p.get("wardsPlaced", 0),
            "wards_killed": p.get("wardsKilled", 0),
            "spells": [s1_info, s2_info],
            "rune": rune_info,
            "sub_rune": sub_rune_info,
            "perks_data": perks_data,
            "full_rune_tree_tooltip": full_rune_tree_tooltip,
            "augments": augments,
            "purchased_anvils": purchased_anvils,
            "items": items,
            "subteam_id": p.get("playerSubteamId", 0),
            "placement": p.get("subteamPlacement") or p.get("placement") or p.get("challenges", {}).get("placement", 0),
            "penta_kills": p.get("pentaKills", 0),
            "quadra_kills": p.get("quadraKills", 0),
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
            "key_events": self._extract_key_events(),
            "item_events": getattr(self, "_cached_item_events", []),
            "multikills": self._extract_multikill_sequences()
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
            role_name = "SUPPORT" if m["role"] == "UTILITY" else m["role"]
            g_tags = " ".join([
                f"{k}:{(v['diff'] if isinstance(v, dict) else v):+d}g"
                for k, v in m["gold_delta"].items()
            ])
            lines.append(f"• {role_name} ({p1['champion']} vs {p2['champion']}): {g_tags} | SoloKills: {m['p1_stats']['solo_kills']}x{m['p2_stats']['solo_kills']} | GankDeaths: {m['p1_stats']['other_deaths']}x{m['p2_stats']['other_deaths']}")

        # 3. JOGADORES (Blue & Red)
        def format_team_players(team_key, team_name):
            t_lines = [f"\n[{team_name} TEAM]"]
            for p in data[team_key]["players"]:
                items_str = ", ".join([it["name"] for it in p["items"]]) or "None"
                dmg_total = p["damage_to_champions"]
                dmg_p = p.get("damage_physical", 0)
                dmg_m = p.get("damage_magic", 0)
                dmg_t = p.get("damage_true", 0)
                dmg_str = f"{dmg_total:,} (Phys: {dmg_p:,}, Magic: {dmg_m:,}, True: {dmg_t:,})"
                raw_role = p.get("role") or ""
                clean_role = "SUPPORT" if raw_role == "UTILITY" else raw_role
                role_prefix = f"{clean_role} " if clean_role else ""
                t_lines.append(f"• {role_prefix}{p['champion']} ({p['riot_id']}): KDA {p['kda']} | CS {p['cs']} | DMG {dmg_str} | GOLD {p['gold_total']:,} | ITEMS: {items_str}")
            return t_lines

        lines.extend(format_team_players("team_100", "BLUE"))
        lines.extend(format_team_players("team_200", "RED"))

        # 4. DESTAQUES (Pentakills & Multikills)
        highlights = []
        for ev in data.get("key_events", []):
            streak = ev.get("streak", "normal")
            if streak == "penta":
                highlights.append(f"[{ev['time']}] PENTAKILL by {ev['killer_champ']} ({ev['killer_name']})")
            elif streak == "quadra":
                highlights.append(f"[{ev['time']}] QUADRA KILL by {ev['killer_champ']} ({ev['killer_name']})")
            elif streak == "triple":
                highlights.append(f"[{ev['time']}] TRIPLE KILL by {ev['killer_champ']} ({ev['killer_name']})")
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

                p1_solo_deaths, p1_other_deaths, p1_solo_kills, p1_executions = 0, 0, 0, 0
                p2_solo_deaths, p2_other_deaths, p2_solo_kills, p2_executions = 0, 0, 0, 0

                for frame in frames:
                    for ev in frame.get("events", []):
                        if ev.get("type") == "CHAMPION_KILL":
                            vic = ev.get("victimId")
                            kil = ev.get("killerId", 0)
                            ass = ev.get("assistingParticipantIds", [])
                            if ass is None:
                                ass = []
                            
                            if vic == id1:
                                if kil == 0 and len(ass) == 0:
                                    p1_executions += 1
                                elif kil == id2 and len(ass) == 0:
                                    p1_solo_deaths += 1
                                    p2_solo_kills += 1
                                else:
                                    p1_other_deaths += 1
                            elif vic == id2:
                                if kil == 0 and len(ass) == 0:
                                    p2_executions += 1
                                elif kil == id1 and len(ass) == 0:
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
                        g1 = f1.get("totalGold", 0)
                        g2 = f2.get("totalGold", 0)
                        x1 = f1.get("xp", 0)
                        x2 = f2.get("xp", 0)
                        gold_diff[f"{m}m"] = {
                            "diff": g1 - g2,
                            "p1_val": g1,
                            "p2_val": g2
                        }
                        xp_diff[f"{m}m"] = {
                            "diff": x1 - x2,
                            "p1_val": x1,
                            "p2_val": x2
                        }

                matchups.append({
                    "role": role,
                    "player1": p1,
                    "player2": p2,
                    "p1_stats": {"solo_deaths": p1_solo_deaths, "other_deaths": p1_other_deaths, "solo_kills": p1_solo_kills, "executions": p1_executions},
                    "p2_stats": {"solo_deaths": p2_solo_deaths, "other_deaths": p2_other_deaths, "solo_kills": p2_solo_kills, "executions": p2_executions},
                    "gold_delta": gold_diff,
                    "xp_delta": xp_diff
                })

        # Calculate 2v2 isolated lane deaths for bot duo
        bot_pair = p_by_role.get("BOTTOM", [])
        sup_pair = p_by_role.get("UTILITY", [])
        if len(bot_pair) == 2 and len(sup_pair) == 2:
            d1_ids = {bot_pair[0]["participantId"], sup_pair[0]["participantId"]}
            d2_ids = {bot_pair[1]["participantId"], sup_pair[1]["participantId"]}
            d1_lane_deaths, d1_other_deaths, d1_executions = 0, 0, 0
            d2_lane_deaths, d2_other_deaths, d2_executions = 0, 0, 0

            for frame in frames:
                for ev in frame.get("events", []):
                    if ev.get("type") == "CHAMPION_KILL":
                        vic = ev.get("victimId")
                        kil = ev.get("killerId", 0)
                        ass = ev.get("assistingParticipantIds", [])
                        if ass is None:
                            ass = []
                        involved_enemies = set([kil] + ass)

                        if vic in d1_ids:
                            if kil == 0 and len(ass) == 0:
                                d1_executions += 1
                            elif involved_enemies.issubset(d2_ids):
                                d1_lane_deaths += 1
                            else:
                                d1_other_deaths += 1
                        elif vic in d2_ids:
                            if kil == 0 and len(ass) == 0:
                                d2_executions += 1
                            elif involved_enemies.issubset(d1_ids):
                                d2_lane_deaths += 1
                            else:
                                d2_other_deaths += 1

            for m in matchups:
                if m["role"] in ("BOTTOM", "UTILITY"):
                    m["bot_duo_stats"] = {
                        "d1_lane_deaths": d1_lane_deaths,
                        "d1_other_deaths": d1_other_deaths,
                        "d1_executions": d1_executions,
                        "d2_lane_deaths": d2_lane_deaths,
                        "d2_other_deaths": d2_other_deaths,
                        "d2_executions": d2_executions
                    }


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
        life_streaks = {}
        ongoing_kda = {pid: {"k": 0, "d": 0, "a": 0} for pid in range(1, 11)}
        timeline_drake_count = {100: 0, 200: 0}
        first_blood_awarded = False

        # Track ongoing inventory snapshots per participant
        # All players start with Stealth Ward (3340) automatically in matchmade queues
        inventories = {pid: [3340] for pid in range(1, 11)}
        
        # In permanent matchmade Summoner's Rift queues, Support role automatically starts with World Atlas (3865)
        for p in self.match.get("info", {}).get("participants", []):
            pid = p.get("participantId")
            role = p.get("teamPosition") or p.get("individualPosition") or ""
            if pid and role.upper() == "UTILITY":
                inventories[pid].append(3865) # Atlas Mundial / World Atlas

        item_events_log = []

        for frame in frames:
            for ev in frame.get("events", []):
                ev_type = ev.get("type")
                ts = ev.get("timestamp", 0)
                t_str = format_timestamp(ts)
                pid = ev.get("participantId")
                item_id = ev.get("itemId", 0)
                after_id = ev.get("afterId", 0)
                before_id = ev.get("beforeId", 0)

                # Inventory tracking
                if pid and pid in inventories:
                    if ev_type == "ITEM_PURCHASED":
                        inventories[pid].append(item_id)
                        p_dict = self._get_part_dict(pid)
                        raw_c = p_dict.get("championName", "")
                        item_name = self.ddragon.get_item_name(item_id)
                        item_icon = self.ddragon.get_item_icon_url(item_id)
                        snap = [
                            {
                                "id": iid,
                                "name": self.ddragon.get_item_name(iid),
                                "icon": self.ddragon.get_item_icon_url(iid),
                                "tooltip": self.ddragon.get_item_tooltip(iid)
                            }
                            for iid in inventories[pid] if iid
                        ]
                        # Group consecutive purchases by the same participant within ~60s window
                        if item_events_log and item_events_log[-1]["participant_id"] == pid and (ts - item_events_log[-1].get("ts", 0)) <= 60000:
                            last_group = item_events_log[-1]
                            last_group["time"] = t_str
                            last_group["ts"] = ts
                            last_group["items_snapshot"] = snap
                            # Update items list in group
                            found_item = False
                            for it_entry in last_group["items"]:
                                if it_entry["item_id"] == item_id:
                                    it_entry["count"] += 1
                                    found_item = True
                                    break
                            if not found_item:
                                last_group["items"].append({
                                    "item_id": item_id,
                                    "item_name": item_name,
                                    "item_icon": item_icon,
                                    "tooltip": self.ddragon.get_item_tooltip(item_id),
                                    "count": 1
                                })
                        else:
                            item_events_log.append({
                                "type": "item_purchased",
                                "time": t_str,
                                "ts": ts,
                                "participant_id": pid,
                                "role": str(p_dict.get("teamPosition") or p_dict.get("individualPosition", "")).upper(),
                                "champ": self.ddragon.get_clean_champion_name(raw_c),
                                "champ_icon": self.ddragon.get_champion_icon_url(raw_c),
                                "summoner_name": p_dict.get("riotIdGameName", ""),
                                "items": [
                                    {
                                        "item_id": item_id,
                                        "item_name": item_name,
                                        "item_icon": item_icon,
                                        "tooltip": self.ddragon.get_item_tooltip(item_id),
                                        "count": 1
                                    }
                                ],
                                "items_snapshot": snap
                            })
                    elif ev_type == "ITEM_SOLD":
                        if item_id in inventories[pid]:
                            inventories[pid].remove(item_id)
                    elif ev_type == "ITEM_DESTROYED":
                        if item_id in inventories[pid]:
                            inventories[pid].remove(item_id)
                    elif ev_type == "ITEM_UNDO":
                        if before_id and before_id in inventories[pid]:
                            inventories[pid].remove(before_id)
                        if after_id:
                            inventories[pid].append(after_id)

                if ev_type == "CHAMPION_KILL":
                    victim = ev.get("victimId")
                    killer = ev.get("killerId")
                    assisters = ev.get("assistingParticipantIds", [])
                    v_p = self._get_part_dict(victim)
                    k_p = self._get_part_dict(killer)

                    is_first_blood = False
                    if killer != 0 and not first_blood_awarded:
                        is_first_blood = True
                        first_blood_awarded = True

                    # Multikill tracking (Double, Triple, Quadra, Penta within time window)
                    streak_type = "normal"
                    killer_streak = kill_streaks.get(killer, {"count": 0, "last_ts": 0})
                    current_count = killer_streak["count"]
                    last_ts = killer_streak["last_ts"]

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

                    # Life streak tracking (Killing spree 3+, Rampage 4, Unstoppable 5, Dominating 6, Godlike 7, Legendary 8+)
                    life_streak_type = "none"
                    if killer and killer != 0:
                        life_streaks[killer] = life_streaks.get(killer, 0) + 1
                        l_count = life_streaks[killer]
                        if l_count >= 8:
                            life_streak_type = "legendary"
                        elif l_count == 7:
                            life_streak_type = "godlike"
                        elif l_count == 6:
                            life_streak_type = "dominating"
                        elif l_count == 5:
                            life_streak_type = "unstoppable"
                        elif l_count == 4:
                            life_streak_type = "rampage"
                        elif l_count == 3:
                            life_streak_type = "spree"

                    # Reset victim's life streak on death
                    if victim:
                        life_streaks[victim] = 0

                    is_solo = len(assisters) == 0
                    is_execution = (killer == 0)
                    k_raw = k_p.get("championName", "")
                    v_raw = v_p.get("championName", "")

                    assisters_data = []
                    for aid in assisters:
                        a_p = self._get_part_dict(aid)
                        a_raw = a_p.get("championName", "")
                        assisters_data.append({
                            "champ": self.ddragon.get_clean_champion_name(a_raw),
                            "icon": self.ddragon.get_champion_icon_url(a_raw),
                            "name": a_p.get("riotIdGameName", ""),
                            "team_id": a_p.get("teamId", 100)
                        })

                    # Extract participant frame data (stats, level, gold)
                    p_frames = frame.get("participantFrames", {})
                    k_pframe = p_frames.get(str(killer), {}) if (killer and killer != 0) else {}
                    v_pframe = p_frames.get(str(victim), {}) if victim else {}

                    k_stats = k_pframe.get("championStats", {})
                    v_stats = v_pframe.get("championStats", {})

                    k_lvl = k_pframe.get("level", 1)
                    v_lvl = v_pframe.get("level", 1)

                    k_gold = k_pframe.get("totalGold", 0)
                    v_gold = v_pframe.get("totalGold", 0)

                    # Update ongoing KDA for killer, victim, assisters
                    if killer and killer != 0 and killer in ongoing_kda:
                        ongoing_kda[killer]["k"] += 1
                    if victim and victim in ongoing_kda:
                        ongoing_kda[victim]["d"] += 1
                    for aid in assisters:
                        if aid in ongoing_kda:
                            ongoing_kda[aid]["a"] += 1

                    k_kda_str = f"{ongoing_kda[killer]['k']}/{ongoing_kda[killer]['d']}/{ongoing_kda[killer]['a']}" if (killer and killer in ongoing_kda) else "0/0/0"
                    v_kda_str = f"{ongoing_kda[victim]['k']}/{ongoing_kda[victim]['d']}/{ongoing_kda[victim]['a']}" if (victim and victim in ongoing_kda) else "0/0/0"

                    # Current items snapshot at kill moment
                    k_items = [
                        {"id": iid, "name": self.ddragon.get_item_name(iid), "icon": self.ddragon.get_item_icon_url(iid), "tooltip": self.ddragon.get_item_tooltip(iid)}
                        for iid in inventories.get(killer, []) if iid
                    ] if killer and killer != 0 else []
                    v_items = [
                        {"id": iid, "name": self.ddragon.get_item_name(iid), "icon": self.ddragon.get_item_icon_url(iid), "tooltip": self.ddragon.get_item_tooltip(iid)}
                        for iid in inventories.get(victim, []) if iid
                    ] if victim else []

                    events_log.append({
                        "type": "kill",
                        "streak": streak_type,
                        "life_streak": life_streak_type,
                        "time": t_str,
                        "is_execution": is_execution,
                        "killer_champ": self.ddragon.get_clean_champion_name(k_raw) if not is_execution else "",
                        "killer_icon": self.ddragon.get_champion_icon_url(k_raw) if not is_execution else "",
                        "killer_name": k_p.get("riotIdGameName", "") if not is_execution else "",
                        "killer_role": str(k_p.get("teamPosition") or k_p.get("individualPosition", "")).upper() if not is_execution else "",
                        "killer_team": k_p.get("teamId", 100) if not is_execution else 0,
                        "killer_level": k_lvl,
                        "killer_gold": k_gold,
                        "killer_kda": k_kda_str,
                        "killer_stats": k_stats,
                        "killer_items": k_items,
                        "victim_champ": self.ddragon.get_clean_champion_name(v_raw),
                        "victim_icon": self.ddragon.get_champion_icon_url(v_raw),
                        "victim_name": v_p.get("riotIdGameName", ""),
                        "victim_role": str(v_p.get("teamPosition") or v_p.get("individualPosition", "")).upper(),
                        "victim_team": v_p.get("teamId", 200),
                        "victim_level": v_lvl,
                        "victim_gold": v_gold,
                        "victim_kda": v_kda_str,
                        "victim_stats": v_stats,
                        "victim_items": v_items,
                        "is_solo": is_solo,
                        "is_first_blood": is_first_blood,
                        "assists_count": len(assisters),
                        "assisters": assisters_data
                    })

                elif ev_type == "ELITE_MONSTER_KILL":
                    m_type = ev.get("monsterType", "")
                    m_sub = ev.get("monsterSubType", "")
                    killer = ev.get("killerId")
                    k_p = self._get_part_dict(killer)
                    desc = clean_monster_name(m_type, m_sub)
                    
                    asset_key = "dragon_circle"
                    is_soul = False
                    killer_team = k_p.get("teamId") or ev.get("killerTeamId")
                    if "DRAGON" in m_type:
                        if "ELDER" not in str(m_sub).upper():
                            if killer_team in timeline_drake_count:
                                timeline_drake_count[killer_team] += 1
                                if timeline_drake_count[killer_team] == 4:
                                    is_soul = True
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
                        "is_soul": is_soul,
                        "killer_champ": self.ddragon.get_clean_champion_name(k_raw),
                        "killer_icon": self.ddragon.get_champion_icon_url(k_raw),
                        "killer_name": k_p.get("riotIdGameName", "")
                    })

        self._cached_item_events = item_events_log
        return events_log

    def _extract_multikill_sequences(self) -> List[Dict[str, Any]]:
        if not self.timeline:
            return []
        multikills = []
        frames = self.timeline.get("info", {}).get("frames", [])
        active_streaks = {}

        for frame in frames:
            for ev in frame.get("events", []):
                if ev.get("type") == "CHAMPION_KILL":
                    ts = ev.get("timestamp", 0)
                    killer = ev.get("killerId", 0)
                    victim = ev.get("victimId", 0)
                    if not killer or not victim:
                        continue

                    k_p = self._get_part_dict(killer)
                    v_p = self._get_part_dict(victim)

                    streak = active_streaks.get(killer)
                    allowed_window = 30000 if (streak and streak["count"] == 4) else 10000

                    if streak and (ts - streak["last_ts"]) <= allowed_window:
                        streak["count"] += 1
                        streak["last_ts"] = ts
                        streak["victims"].append({
                            "champ": self.ddragon.get_clean_champion_name(v_p.get("championName", "")),
                            "icon": self.ddragon.get_champion_icon_url(v_p.get("championName", "")),
                            "name": v_p.get("riotIdGameName", "")
                        })
                    else:
                        if streak and streak["count"] >= 3:
                            multikills.append(streak)
                        active_streaks[killer] = {
                            "killer_id": killer,
                            "killer_name": k_p.get("riotIdGameName", ""),
                            "killer_champ": self.ddragon.get_clean_champion_name(k_p.get("championName", "")),
                            "killer_icon": self.ddragon.get_champion_icon_url(k_p.get("championName", "")),
                            "start_time": format_timestamp(ts),
                            "last_ts": ts,
                            "count": 1,
                            "victims": [{
                                "champ": self.ddragon.get_clean_champion_name(v_p.get("championName", "")),
                                "icon": self.ddragon.get_champion_icon_url(v_p.get("championName", "")),
                                "name": v_p.get("riotIdGameName", "")
                            }]
                        }

        # Flush remaining streaks at game end
        for killer, streak in active_streaks.items():
            if streak and streak["count"] >= 3:
                multikills.append(streak)

        # Classificar tipo e ordenar por maior multikill primeiro (penta > quadra > triple), depois por tempo
        for mk in multikills:
            cnt = mk["count"]
            if cnt >= 5:
                mk["streak_type"] = "penta"
                mk["title"] = "PENTAKILL"
                mk["badge_icon"] = "👑"
            elif cnt == 4:
                mk["streak_type"] = "quadra"
                mk["title"] = "QUADRA KILL"
                mk["badge_icon"] = "🔥"
            elif cnt == 3:
                mk["streak_type"] = "triple"
                mk["title"] = "TRIPLE KILL"
                mk["badge_icon"] = "⚔️"

        multikills.sort(key=lambda x: (-x["count"], x["last_ts"]))
        return multikills

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
