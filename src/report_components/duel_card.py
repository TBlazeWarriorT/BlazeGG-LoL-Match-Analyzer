from typing import Dict, Any, List
from ..i18n import get_text
from .utils import calculate_gold_bar_share
from .jungle_strip import render_jungle_chronological
from .lane_duel import render_duel_row

def render_all_duels(data: Dict[str, Any], target_puuid: str = "", lang: str = "pt_BR") -> str:
    matchups = data.get("matchups", [])
    jungle = data.get("jungle_stats", {})
    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    dur_s_game = data.get("duration_seconds", 0)
    if not dur_s_game:
        dur_str = data.get("duration", "0m 0s")
        try:
            m_part = int(dur_str.split("m")[0].strip()) if "m" in dur_str else 0
            s_part = int(dur_str.split("m")[1].replace("s", "").strip()) if "m" in dur_str and "s" in dur_str else 0
            dur_s_game = m_part * 60 + s_part
        except Exception:
            dur_s_game = 1800

    dur_min_calc = max(dur_s_game / 60.0, 1.0)

    j100 = jungle.get(100, {})
    j200 = jungle.get(200, {})

    duels_html = []
    m_by_role = {m["role"]: m for m in matchups}
    raw_game_mode = str(data.get("game_mode", "")).upper()
    is_aram = "ARAM" in raw_game_mode or data.get("queue_id") == 450
    is_arena = "CHERRY" in raw_game_mode or "ARENA" in raw_game_mode

    # If ARAM: Pair players sorted by damage (Slot #1, Slot #2...) with full stats but no fake lane deltas
    if is_aram:
        t1_sorted = sorted(team_100.get("players", []), key=lambda x: x.get("damage_to_champions", 0), reverse=True)
        t2_sorted = sorted(team_200.get("players", []), key=lambda x: x.get("damage_to_champions", 0), reverse=True)
        
        for idx in range(max(len(t1_sorted), len(t2_sorted))):
            p1 = t1_sorted[idx] if idx < len(t1_sorted) else {}
            p2 = t2_sorted[idx] if idx < len(t2_sorted) else {}
            
            p1_execs = p1.get("executions", 0)
            p2_execs = p2.get("executions", 0)
            aram_stats_1 = {"executions": p1_execs} if p1_execs > 0 else {}
            aram_stats_2 = {"executions": p2_execs} if p2_execs > 0 else {}

            duels_html.append(render_duel_row(
                p1, p2, "",
                stats_1=aram_stats_1, stats_2=aram_stats_2,
                gold_d={}, xp_d={},
                target_puuid=target_puuid, lang=lang,
                is_aram=True
            ))



    elif is_arena:
        # Group players by subteam (placement)
        all_arena_players = team_100.get("players", []) + team_200.get("players", [])
        subteams = {}
        for p in all_arena_players:
            place = p.get("placement") or p.get("subteam_id", 0)
            subteams.setdefault(place, []).append(p)
        
        sorted_subteams = sorted(subteams.items(), key=lambda x: x[0] if isinstance(x[0], int) and x[0] > 0 else 99)
        
        # Pair 2 teams per frame: (1st vs 2nd), (3rd vs 4th), etc.
        for i in range(0, len(sorted_subteams), 2):
            team_a_place, team_a_players = sorted_subteams[i]
            team_b_place, team_b_players = sorted_subteams[i+1] if i+1 < len(sorted_subteams) else (None, [])
            
            label_a = get_text("arena_team_place", lang=lang, place=team_a_place)
            label_b = get_text("arena_team_place", lang=lang, place=team_b_place)
            
            frame_header = f"""
            <div class="arena-matchup-header">
                <span class="arena-team-badge arena-team-a">{label_a}</span>
                <span style="color:#64748b; font-weight:800; font-size:0.75rem;">VS</span>
                <span class="arena-team-badge arena-team-b">{label_b}</span>
            </div>
            """ if team_b_place else f"""
            <div class="arena-matchup-header">
                <span class="arena-team-badge arena-team-a">{label_a}</span>
            </div>
            """

            team_pair_rows = []
            max_p = max(len(team_a_players), len(team_b_players))
            for p_idx in range(max_p):
                pa = team_a_players[p_idx] if p_idx < len(team_a_players) else {}
                pb = team_b_players[p_idx] if p_idx < len(team_b_players) else {}
                
                team_pair_rows.append(render_duel_row(
                    pa, pb, "",
                    gold_d={}, xp_d={},
                    target_puuid=target_puuid, lang=lang,
                    is_arena=True
                ))

            # Team Consolidated Summary Card (e.g. 3v3 or 2v2 Total)
            if team_a_players and team_b_players:
                def make_arena_team_combined(t_players, place_num):
                    t_dmg = sum(p.get("damage_to_champions", 0) for p in t_players)
                    t_gold = sum(p.get("gold_total", 0) for p in t_players)
                    t_taken = sum(p.get("damage_taken", 0) for p in t_players)
                    t_mit = sum(p.get("damage_mitigated", 0) for p in t_players)
                    t_hl = sum(p.get("total_heal", 0) for p in t_players)
                    t_phys = sum(p.get("damage_physical", 0) for p in t_players)
                    t_mag = sum(p.get("damage_magic", 0) for p in t_players)
                    t_tru = sum(p.get("damage_true", 0) for p in t_players)
                    t_cs = sum(p.get("cs", 0) for p in t_players)
                    t_kills = sum(p.get("kills", 0) for p in t_players)
                    t_deaths = sum(p.get("deaths", 0) for p in t_players)
                    t_assists = sum(p.get("assists", 0) for p in t_players)
                    t_vis = sum(p.get("vision_score", 0) for p in t_players)
                    t_pinks = sum(p.get("detector_wards", 0) for p in t_players)
                    t_anvils = sum(p.get("purchased_anvils", 0) for p in t_players)
                    
                    ratio = (t_kills + t_assists) / max(t_deaths, 1)
                    csm = round(t_cs / dur_min_calc, 1)
                    icons_html = "".join([f'<div class="team-champ-mini-wrap" title="{p.get("champion", "")}"><img class="team-champ-mini" src="{p.get("champion_icon", "")}" alt="{p.get("champion", "")}"/></div>' for p in t_players])

                    return {
                        "summoner_name": get_text("arena_team_name", lang=lang, place=place_num),
                        "champion": get_text("arena_players_cnt", lang=lang, count=len(t_players)),
                        "champion_icon": "",
                        "champ_level": "",
                        "is_team_combined": True,
                        "team_icons_html": icons_html,
                        "kda": f"{t_kills}/{t_deaths}/{t_assists}",
                        "kda_ratio": f"{ratio:.2f}:1" if t_deaths > 0 else "Perfect",
                        "cs": t_cs,
                        "cs_per_min": csm,
                        "purchased_anvils": t_anvils,
                        "gold_total": t_gold,
                        "damage_to_champions": t_dmg,
                        "damage_physical": t_phys,
                        "damage_magic": t_mag,
                        "damage_true": t_tru,
                        "damage_per_gold": round(t_dmg / max(t_gold, 1), 2),
                        "damage_taken": t_taken,
                        "damage_mitigated": t_mit,
                        "total_heal": t_hl,
                        "vision_score": t_vis,
                        "detector_wards": t_pinks,
                        "enemy_jungle_monsters": 0,
                        "spells": [],
                        "rune": {},
                        "items": [],
                        "puuid": any(p.get("puuid") == target_puuid for p in t_players) and target_puuid or ""
                    }

                comb_a = make_arena_team_combined(team_a_players, team_a_place)
                comb_b = make_arena_team_combined(team_b_players, team_b_place)
                
                comb_title = get_text("arena_matchup_total", lang=lang, t1=len(team_a_players), t2=len(team_b_players))
                team_pair_rows.append(render_duel_row(
                    comb_a, comb_b, comb_title,
                    gold_d={}, xp_d={},
                    is_bot_duo=True,
                    target_puuid=target_puuid, lang=lang,
                    is_arena=True
                ))

            duels_html.append(f"""
            <div class="arena-matchup-frame">
                {frame_header}
                {"".join(team_pair_rows)}
            </div>
            """)



    else:
        # TOP
        if "TOP" in m_by_role:
            m = m_by_role["TOP"]

            duels_html.append(render_duel_row(
                m["player1"], m["player2"], "TOP LANE",
                m["p1_stats"], m["p2_stats"],
                m["gold_delta"], m["xp_delta"],
                target_puuid=target_puuid, lang=lang
            ))

        # JUNGLE
        if "JUNGLE" in m_by_role:
            m = m_by_role["JUNGLE"]
            j1_badges = render_jungle_chronological(j100.get('timeline_sequence', []), lang=lang)
            j2_badges = render_jungle_chronological(j200.get('timeline_sequence', []), lang=lang)

            duels_html.append(render_duel_row(
                m["player1"], m["player2"], "JUNGLE",
                m["p1_stats"], m["p2_stats"],
                m["gold_delta"], m["xp_delta"],
                extra_badges_1=j1_badges,
                extra_badges_2=j2_badges,
                target_puuid=target_puuid, lang=lang
            ))

        # MIDDLE
        if "MIDDLE" in m_by_role:
            m = m_by_role["MIDDLE"]
            duels_html.append(render_duel_row(
                m["player1"], m["player2"], "MID LANE",
                m["p1_stats"], m["p2_stats"],
                m["gold_delta"], m["xp_delta"],
                target_puuid=target_puuid, lang=lang
            ))

        # BOTTOM & UTILITY (Grouped in one unified Bot Lane container)
        m_bot = m_by_role.get("BOTTOM")
        m_sup = m_by_role.get("UTILITY")

        bot_group_cards = []
        if m_bot:
            bot_group_cards.append(render_duel_row(
                m_bot["player1"], m_bot["player2"], "ADC (BOTTOM)",
                m_bot["p1_stats"], m_bot["p2_stats"],
                m_bot["gold_delta"], m_bot["xp_delta"],
                target_puuid=target_puuid, lang=lang
            ))

        if m_sup:
            bot_group_cards.append(render_duel_row(
                m_sup["player1"], m_sup["player2"], "SUPORTE (UTILITY)",
                m_sup["p1_stats"], m_sup["p2_stats"],
                m_sup["gold_delta"], m_sup["xp_delta"],
                target_puuid=target_puuid, lang=lang
            ))

        def make_combined_player_dict(players: List[Dict[str, Any]], team_name: str, target_puuid: str = "", is_5v5: bool = False, lang: str = "pt_BR") -> Dict[str, Any]:
            kills = sum(p.get("kills", 0) for p in players)
            deaths = sum(p.get("deaths", 0) for p in players)
            assists = sum(p.get("assists", 0) for p in players)
            cs = sum(p.get("cs", 0) for p in players)
            csm = round(sum(p.get("cs_per_min", 0) for p in players), 1)
            dmg = sum(p.get("damage_to_champions", 0) for p in players)
            gold = sum(p.get("gold_total", 0) or p.get("gold_earned", 0) for p in players)
            ratio = (kills + assists) / max(deaths, 1)

            if is_5v5:
                def make_mini_avatar(p):
                    c_name = p.get("champion", "")
                    r_id = p.get("riot_id") or p.get("summoner_name") or c_name
                    kda = p.get("kda", "0/0/0")
                    p_dmg = p.get("damage_to_champions", 0)
                    p_gold = p.get("gold_total", 0) or p.get("gold_earned", 0)
                    p_cs = p.get("cs", 0)
                    r_raw = str(p.get("role", "")).upper()
                    role_str = "SUPPORT" if r_raw == "UTILITY" else r_raw
                    role_label = f" ({role_str})" if role_str else ""
                    tt_lines = [
                        f"<b>{c_name}</b>{role_label} - <i>{r_id}</i>",
                        f"• KDA: <b>{kda}</b>",
                        f"• {get_text('dmg_dealt', lang=lang)}: <b>{p_dmg:,}</b>",
                        f"• {get_text('gold', lang=lang)}: <b>{p_gold:,}</b>",
                        f"• CS: <b>{p_cs}</b>"
                    ]
                    tt_html = "<br/>".join(tt_lines).replace('"', '&quot;')
                    return f'<div class="team-champ-mini-wrap" data-tooltip="{tt_html}"><img class="team-champ-mini" src="{p.get("champion_icon", "")}" alt="{c_name}"/></div>'

                team_icons_html = "".join([make_mini_avatar(p) for p in players])
                champion_label = team_name
                champ_icon = ""
            else:
                team_icons_html = ""
                champion_label = " & ".join(p.get("champion", "") for p in players)
                champ_icon = players[0].get("champion_icon", "") if players else ""

            p1_first = players[0] if len(players) > 0 else {}
            p2_second = players[1] if len(players) > 1 else {}

            return {
                "champion": champion_label,
                "champion_icon": champ_icon,
                "champ1": p1_first.get("champion", ""),
                "icon1": p1_first.get("champion_icon", ""),
                "lvl1": p1_first.get("champ_level", 1),
                "champ2": p2_second.get("champion", ""),
                "icon2": p2_second.get("champion_icon", ""),
                "lvl2": p2_second.get("champ_level", 1),
                "summoner_name": team_name,
                "riot_id": team_name,
                "is_team_combined": is_5v5,
                "team_icons_html": team_icons_html,
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "kda": f"{kills}/{deaths}/{assists}",
                "kda_ratio": f"{ratio:.2f}:1" if deaths > 0 else "Perfect",
                "cs": cs,
                "cs_per_min": csm,
                "damage_to_champions": dmg,
                "damage_physical": sum(p.get("damage_physical", 0) for p in players),
                "damage_magic": sum(p.get("damage_magic", 0) for p in players),
                "damage_true": sum(p.get("damage_true", 0) for p in players),
                "damage_total_all": sum(p.get("damage_total_all", 0) for p in players),
                "damage_to_objectives": sum(p.get("damage_to_objectives", 0) for p in players),
                "damage_to_turrets": sum(p.get("damage_to_turrets", 0) or p.get("damage_to_buildings", 0) for p in players),
                "turret_kills": sum(p.get("turret_kills", 0) for p in players),
                "inhibitor_kills": sum(p.get("inhibitor_kills", 0) for p in players),
                "damage_taken": sum(p.get("damage_taken", 0) for p in players),
                "damage_taken_physical": sum(p.get("damage_taken_physical", 0) for p in players),
                "damage_taken_magic": sum(p.get("damage_taken_magic", 0) for p in players),
                "damage_taken_true": sum(p.get("damage_taken_true", 0) for p in players),
                "damage_mitigated": sum(p.get("damage_mitigated", 0) for p in players),
                "total_heal": sum(p.get("total_heal", 0) for p in players),
                "vision_score": sum(p.get("vision_score", 0) for p in players),
                "detector_wards": sum(p.get("detector_wards", 0) for p in players),
                "vision_wards_bought": sum(p.get("vision_wards_bought", 0) for p in players),
                "wards_placed": sum(p.get("wards_placed", 0) for p in players),
                "wards_killed": sum(p.get("wards_killed", 0) for p in players),
                "enemy_jungle_monsters": sum(p.get("enemy_jungle_monsters", 0) for p in players),
                "minions_killed": sum(p.get("minions_killed", 0) for p in players),
                "neutral_monsters_killed": sum(p.get("neutral_monsters_killed", 0) for p in players),
                "gold_earned": gold,
                "gold_total": gold,
                "damage_per_gold": round(dmg / max(gold, 1), 2),
                "executions": sum(p.get("executions", 0) for p in players),
                "spells": [],
                "rune": {},
                "items": [],
                "puuid": target_puuid if any(p.get("puuid") == target_puuid for p in players) else ""
            }

        # BOT DUO (2v2)
        if m_bot and m_sup:
            p1_bot, p2_bot = m_bot["player1"], m_bot["player2"]
            p1_sup, p2_sup = m_sup["player1"], m_sup["player2"]

            duo_p1 = make_combined_player_dict([p1_bot, p1_sup], "", target_puuid=target_puuid, is_5v5=False, lang=lang)
            duo_p2 = make_combined_player_dict([p2_bot, p2_sup], "", target_puuid=target_puuid, is_5v5=False, lang=lang)

            def combine_deltas(d_bot, d_sup):
                combined = {}
                all_keys = sorted(
                    list(set(list(d_bot.keys()) + list(d_sup.keys()))),
                    key=lambda x: int(x.replace("m", "")) if x.replace("m", "").isdigit() else 999
                )
                for k in all_keys:
                    v_bot = d_bot.get(k, 0)
                    v_sup = d_sup.get(k, 0)
                    if isinstance(v_bot, dict) or isinstance(v_sup, dict):
                        diff_bot = v_bot.get("diff", 0) if isinstance(v_bot, dict) else int(v_bot)
                        diff_sup = v_sup.get("diff", 0) if isinstance(v_sup, dict) else int(v_sup)
                        p1_bot_val = v_bot.get("p1_val", 0) if isinstance(v_bot, dict) else 0
                        p1_sup_val = v_sup.get("p1_val", 0) if isinstance(v_sup, dict) else 0
                        p2_bot_val = v_bot.get("p2_val", 0) if isinstance(v_bot, dict) else 0
                        p2_sup_val = v_sup.get("p2_val", 0) if isinstance(v_sup, dict) else 0
                        combined[k] = {
                            "diff": diff_bot + diff_sup,
                            "p1_val": p1_bot_val + p1_sup_val,
                            "p2_val": p2_bot_val + p2_sup_val
                        }
                    else:
                        combined[k] = int(v_bot) + int(v_sup)
                return combined

            duo_delta_gold = combine_deltas(m_bot.get("gold_delta", {}), m_sup.get("gold_delta", {}))
            duo_delta_xp = combine_deltas(m_bot.get("xp_delta", {}), m_sup.get("xp_delta", {}))

            bot_group_cards.append(render_duel_row(
                duo_p1, duo_p2, get_text("bot_duo_title", lang=lang),
                gold_d=duo_delta_gold,
                xp_d=duo_delta_xp,
                stats_1=m_bot.get("bot_duo_stats", {}),
                stats_2={},
                is_bot_duo=True,
                target_puuid=target_puuid,
                lang=lang
            ))

        if bot_group_cards:
            bot_frame_title = get_text("bot_lane_frame_title", lang=lang)
            duels_html.append(f"""
            <div class="bot-lane-group">
                <div class="bot-lane-group-title">{bot_frame_title}</div>
                {"".join(bot_group_cards)}
            </div>
            """)

    # TEAM COMBINED (5v5 TOTAL)
    t1_players = team_100.get("players", [])
    t2_players = team_200.get("players", [])
    raw_game_mode = str(data.get("game_mode", "")).upper()
    is_arena = "CHERRY" in raw_game_mode or "ARENA" in raw_game_mode

    if t1_players and t2_players and not is_arena:
        raw_team_gold = {}
        for m in matchups:
            for k, v in m.get("gold_delta", {}).items():
                if k not in raw_team_gold:
                    raw_team_gold[k] = {"diff": 0, "p1_val": 0, "p2_val": 0}
                if isinstance(v, dict):
                    raw_team_gold[k]["diff"] += v.get("diff", 0)
                    raw_team_gold[k]["p1_val"] += v.get("p1_val", 0)
                    raw_team_gold[k]["p2_val"] += v.get("p2_val", 0)
                else:
                    raw_team_gold[k]["diff"] += int(v)

        team_delta_gold = {
            k: raw_team_gold[k]
            for k in sorted(
                raw_team_gold.keys(),
                key=lambda x: int(x.replace("m", "")) if x.replace("m", "").isdigit() else 999
            )
        }

        team_p1 = make_combined_player_dict(t1_players, get_text("blue_team", lang=lang), target_puuid, is_5v5=True, lang=lang)
        team_p2 = make_combined_player_dict(t2_players, get_text("red_team", lang=lang), target_puuid, is_5v5=True, lang=lang)

        duels_html.append(render_duel_row(
            team_p1, team_p2, get_text("team_combined_title", lang=lang),
            gold_d=team_delta_gold,
            xp_d={},
            stats_1={},
            stats_2={},
            is_bot_duo=False,
            target_puuid=target_puuid,
            lang=lang,
            is_arena=False
        ))

    return "".join(duels_html)
