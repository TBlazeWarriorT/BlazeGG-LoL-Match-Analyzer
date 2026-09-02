from typing import Dict, Any, List
from ..asset_cache import AssetManager
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
    icon_gold = AssetManager.get_asset_uri("gold_icon")
    icon_cs = AssetManager.get_asset_uri("cs_icon")
    icon_pink = "https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/2055.png"

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

        # BOT DUO (2v2)
        if m_bot and m_sup:
            p1_bot, p2_bot = m_bot["player1"], m_bot["player2"]
            p1_sup, p2_sup = m_sup["player1"], m_sup["player2"]

            d1_dmg = p1_bot["damage_to_champions"] + p1_sup["damage_to_champions"]
            d2_dmg = p2_bot["damage_to_champions"] + p2_sup["damage_to_champions"]
            d1_gold = p1_bot["gold_total"] + p1_sup["gold_total"]
            d2_gold = p2_bot["gold_total"] + p2_sup["gold_total"]
            d1_taken = p1_bot["damage_taken"] + p1_sup["damage_taken"]
            d2_taken = p2_bot["damage_taken"] + p2_sup["damage_taken"]
            d1_cs = p1_bot["cs"] + p1_sup["cs"]
            d2_cs = p2_bot["cs"] + p2_sup["cs"]
            d1_kills = p1_bot["kills"] + p1_sup["kills"]
            d1_deaths = p1_bot["deaths"] + p1_sup["deaths"]
            d1_assists = p1_bot["assists"] + p1_sup["assists"]
            d2_kills = p2_bot["kills"] + p2_bot["kills"]
            d2_deaths = p2_bot["deaths"] + p2_sup["deaths"]
            d2_assists = p2_bot["assists"] + p2_sup["assists"]

            ratio_d1 = (d1_kills + d1_assists) / max(d1_deaths, 1)
            ratio_d2 = (d2_kills + d2_assists) / max(d2_deaths, 1)

            csm_d1 = round(d1_cs / dur_min_calc, 1)
            csm_d2 = round(d2_cs / dur_min_calc, 1)

            duo_p1 = {
                "champ1": p1_bot["champion"], "icon1": p1_bot["champion_icon"], "lvl1": p1_bot.get("champ_level", 1),
                "champ2": p1_sup["champion"], "icon2": p1_sup["champion_icon"], "lvl2": p1_sup.get("champ_level", 1),
                "kda": f"{d1_kills}/{d1_deaths}/{d1_assists}",
                "kda_ratio": f"{ratio_d1:.2f}:1" if d1_deaths > 0 else "Perfect",
                "cs": d1_cs,
                "cs_per_min": csm_d1,
                "damage_to_champions": d1_dmg,
                "damage_physical": p1_bot.get("damage_physical", 0) + p1_sup.get("damage_physical", 0),
                "damage_magic": p1_bot.get("damage_magic", 0) + p1_sup.get("damage_magic", 0),
                "damage_true": p1_bot.get("damage_true", 0) + p1_sup.get("damage_true", 0),
                "damage_per_gold": round(d1_dmg / max(d1_gold, 1), 2),
                "damage_taken": d1_taken,
                "damage_mitigated": p1_bot.get("damage_mitigated", 0) + p1_sup.get("damage_mitigated", 0),
                "total_heal": p1_bot.get("total_heal", 0) + p1_sup.get("total_heal", 0),
                "vision_score": p1_bot.get("vision_score", 0) + p1_sup.get("vision_score", 0),
                "detector_wards": p1_bot.get("detector_wards", 0) + p1_sup.get("detector_wards", 0),
                "enemy_jungle_monsters": p1_bot.get("enemy_jungle_monsters", 0) + p1_sup.get("enemy_jungle_monsters", 0),
                "gold_total": d1_gold,
                "puuid": p1_bot["puuid"] if target_puuid in (p1_bot["puuid"], p1_sup["puuid"]) else ""
            }

            duo_p2 = {
                "champ1": p2_bot["champion"], "icon1": p2_bot["champion_icon"], "lvl1": p2_bot.get("champ_level", 1),
                "champ2": p2_sup["champion"], "icon2": p2_sup["champion_icon"], "lvl2": p2_sup.get("champ_level", 1),
                "kda": f"{d2_kills}/{d2_deaths}/{d2_assists}",
                "kda_ratio": f"{ratio_d2:.2f}:1" if d2_deaths > 0 else "Perfect",
                "cs": d2_cs,
                "cs_per_min": csm_d2,
                "damage_to_champions": d2_dmg,
                "damage_physical": p2_bot.get("damage_physical", 0) + p2_sup.get("damage_physical", 0),
                "damage_magic": p2_bot.get("damage_magic", 0) + p2_sup.get("damage_magic", 0),
                "damage_true": p2_bot.get("damage_true", 0) + p2_sup.get("damage_true", 0),
                "damage_per_gold": round(d2_dmg / max(d2_gold, 1), 2),
                "damage_taken": d2_taken,
                "damage_mitigated": p2_bot.get("damage_mitigated", 0) + p2_sup.get("damage_mitigated", 0),
                "total_heal": p2_bot.get("total_heal", 0) + p2_sup.get("total_heal", 0),
                "vision_score": p2_bot.get("vision_score", 0) + p2_sup.get("vision_score", 0),
                "detector_wards": p2_bot.get("detector_wards", 0) + p2_sup.get("detector_wards", 0),
                "enemy_jungle_monsters": p2_bot.get("enemy_jungle_monsters", 0) + p2_sup.get("enemy_jungle_monsters", 0),
                "gold_total": d2_gold,
                "puuid": p2_bot["puuid"] if target_puuid in (p2_bot["puuid"], p2_sup["puuid"]) else ""
            }

            duo_delta_gold = {}
            duo_delta_xp = {}

            def combine_deltas(d_bot, d_sup):
                combined = {}
                # Sort keys chronologically (5m, 10m, 15m, 20m)
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
                        p1_bot = v_bot.get("p1_val", 0) if isinstance(v_bot, dict) else 0
                        p1_sup = v_sup.get("p1_val", 0) if isinstance(v_sup, dict) else 0
                        p2_bot = v_bot.get("p2_val", 0) if isinstance(v_bot, dict) else 0
                        p2_sup = v_sup.get("p2_val", 0) if isinstance(v_sup, dict) else 0
                        combined[k] = {
                            "diff": diff_bot + diff_sup,
                            "p1_val": p1_bot + p1_sup,
                            "p2_val": p2_bot + p2_sup
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
        t1_dmg = sum(p.get("damage_to_champions", 0) for p in t1_players)
        t2_dmg = sum(p.get("damage_to_champions", 0) for p in t2_players)
        t1_gold = sum(p.get("gold_total", 0) for p in t1_players)
        t2_gold = sum(p.get("gold_total", 0) for p in t2_players)
        t1_taken = sum(p.get("damage_taken", 0) for p in t1_players)
        t2_taken = sum(p.get("damage_taken", 0) for p in t2_players)
        t1_mit = sum(p.get("damage_mitigated", 0) for p in t1_players)
        t2_mit = sum(p.get("damage_mitigated", 0) for p in t2_players)
        t1_hl = sum(p.get("total_heal", 0) for p in t1_players)
        t2_hl = sum(p.get("total_heal", 0) for p in t2_players)

        t1_phys = sum(p.get("damage_physical", 0) for p in t1_players)
        t2_phys = sum(p.get("damage_physical", 0) for p in t2_players)
        t1_mag = sum(p.get("damage_magic", 0) for p in t1_players)
        t2_mag = sum(p.get("damage_magic", 0) for p in t2_players)
        t1_tru = sum(p.get("damage_true", 0) for p in t1_players)
        t2_tru = sum(p.get("damage_true", 0) for p in t2_players)

        t1_cs = sum(p.get("cs", 0) for p in t1_players)
        t2_cs = sum(p.get("cs", 0) for p in t2_players)
        t1_kills = sum(p.get("kills", 0) for p in t1_players)
        t1_deaths = sum(p.get("deaths", 0) for p in t1_players)
        t1_assists = sum(p.get("assists", 0) for p in t1_players)
        t2_kills = sum(p.get("kills", 0) for p in t2_players)
        t2_deaths = sum(p.get("deaths", 0) for p in t2_players)
        t2_assists = sum(p.get("assists", 0) for p in t2_players)

        t1_vis = sum(p.get("vision_score", 0) for p in t1_players)
        t2_vis = sum(p.get("vision_score", 0) for p in t2_players)
        t1_pinks = sum(p.get("detector_wards", 0) for p in t1_players)
        t2_pinks = sum(p.get("detector_wards", 0) for p in t2_players)
        t1_execs = sum(p.get("executions", 0) for p in t1_players)
        t2_execs = sum(p.get("executions", 0) for p in t2_players)

        t1_camps = sum(p.get("enemy_jungle_monsters", 0) for p in t1_players)
        t2_camps = sum(p.get("enemy_jungle_monsters", 0) for p in t2_players)

        ratio_t1 = (t1_kills + t1_assists) / max(t1_deaths, 1)
        ratio_t2 = (t2_kills + t2_assists) / max(t2_deaths, 1)

        csm_t1 = round(t1_cs / dur_min_calc, 1)
        csm_t2 = round(t2_cs / dur_min_calc, 1)

        t1_icons_html = "".join([f'<div class="team-champ-mini-wrap" title="{p["champion"]}"><img class="team-champ-mini" src="{p["champion_icon"]}" alt="{p["champion"]}"/></div>' for p in t1_players])
        t2_icons_html = "".join([f'<div class="team-champ-mini-wrap" title="{p["champion"]}"><img class="team-champ-mini" src="{p["champion_icon"]}" alt="{p["champion"]}"/></div>' for p in t2_players])

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

        # Sort team deltas chronologically (5m, 10m, 15m, 20m)
        team_delta_gold = {
            k: raw_team_gold[k]
            for k in sorted(
                raw_team_gold.keys(),
                key=lambda x: int(x.replace("m", "")) if x.replace("m", "").isdigit() else 999
            )
        }


        def format_team_badge(time_label: str, item: Any) -> str:
            diff = item.get("diff", 0) if isinstance(item, dict) else int(item)
            v1 = item.get("p1_val", None) if isinstance(item, dict) else None
            v2 = item.get("p2_val", None) if isinstance(item, dict) else None

            lead_lbl = get_text("lead_label", lang=lang)
            even_lbl = get_text("even_label", lang=lang)
            blue_team_lbl = get_text("blue_team", lang=lang)
            red_team_lbl = get_text("red_team", lang=lang)

            if diff > 0:
                lead_txt = f"<b style='color:#60a5fa;'>+{diff:,} gold ({blue_team_lbl})</b>"
                cls_name = "delta-blue"
                display_val = f"{diff:,}"
            elif diff < 0:
                lead_txt = f"<b style='color:#f87171;'>+{abs(diff):,} gold ({red_team_lbl})</b>"
                cls_name = "delta-red"
                display_val = f"{abs(diff):,}"
            else:
                lead_txt = f"<b style='color:#94a3b8;'>{even_lbl} (0 gold)</b>"
                cls_name = "delta-even"
                display_val = "0"

            if v1 is not None and v2 is not None and (v1 > 0 or v2 > 0):
                tt_html = f"<div style='text-align:left; font-size:0.75rem; line-height:1.4;'><span style='color:#60a5fa;'>🔵 {blue_team_lbl}:</span> <b>{v1:,}</b> gold<br/><span style='color:#f87171;'>🔴 {red_team_lbl}:</span> <b>{v2:,}</b> gold<br/><hr style='border:0; border-top:1px solid #334155; margin:3px 0;'/>{lead_lbl} {lead_txt}</div>"
            else:
                tt_html = f"{lead_lbl} {lead_txt}"

            return f'<span class="delta-tag" title="{tt_html}">{time_label}: <b class="{cls_name}">{display_val}</b></span>'


        team_gold_tags = "".join([
            format_team_badge(k, v)
            for k, v in team_delta_gold.items()
        ]) if team_delta_gold else ""



        delta_gold_section = f"""
        <div class="delta-box" style="margin-top:6px;">
            <div class="delta-title"><img class="mini-icon" src="{icon_gold}"/> {get_text("gold_delta_title", lang=lang)}</div>
            <div class="delta-flex">{team_gold_tags}</div>
        </div>
        """ if team_gold_tags else ""

        t1_dmg_delta_tag = f'<span class="lead-delta">+{t1_dmg - t2_dmg:,}</span>' if t1_dmg > t2_dmg else ""
        t2_dmg_delta_tag = f'<span class="lead-delta">+{t2_dmg - t1_dmg:,}</span>' if t2_dmg > t1_dmg else ""
        t1_gold_delta_tag = f'<span class="lead-delta">+{t1_gold - t2_gold:,}</span>' if t1_gold > t2_gold else ""
        t2_gold_delta_tag = f'<span class="lead-delta">+{t2_gold - t1_gold:,}</span>' if t2_gold > t1_gold else ""

        pink_badge_t1 = f"<img class='mini-icon mini-icon-round' src='{icon_pink}' title='Control Wards'/> <b>{t1_pinks}</b>"
        pink_badge_t2 = f"<img class='mini-icon mini-icon-round' src='{icon_pink}' title='Control Wards'/> <b>{t2_pinks}</b>"
        t1_vis_combined = f"{get_text('vision_score', lang=lang)}: <b>{t1_vis}</b> ({pink_badge_t1})"
        t2_vis_combined = f"{get_text('vision_score', lang=lang)}: <b>{t2_vis}</b> ({pink_badge_t2})"

        lbl_dmg = get_text("dmg_dealt", lang=lang)
        lbl_phys = get_text("dmg_physical", lang=lang)
        lbl_mag = get_text("dmg_magic", lang=lang)
        lbl_true = get_text("dmg_true", lang=lang)

        lbl_soaked = get_text("dmg_soaked", lang=lang)
        lbl_taken = get_text("damage_taken", lang=lang)
        lbl_mit = get_text("mitigated", lang=lang)
        lbl_hl = get_text("healed", lang=lang)

        team_exec_html = ""
        if t1_execs > 0 or t2_execs > 0:
            t1_exec_list = [f"{p['champion']} ({p['executions']})" if p['executions'] > 1 else p['champion'] for p in t1_players if p.get("executions", 0) > 0]
            t2_exec_list = [f"{p['champion']} ({p['executions']})" if p['executions'] > 1 else p['champion'] for p in t2_players if p.get("executions", 0) > 0]
            
            tt_lines = [get_text("executions_tt_title", lang=lang)]
            if t1_exec_list:
                tt_lines.append(f"<span style='color:#60a5fa;'>🔵 Blue:</span> " + ", ".join(t1_exec_list))
            if t2_exec_list:
                tt_lines.append(f"<span style='color:#f87171;'>🔴 Red:</span> " + ", ".join(t2_exec_list))
            tt_exec_str = "<br/>".join(tt_lines)

            team_exec_html = f"""
            <div class="duel-scores-wrapper" style="margin-top: 6px;">
                <div class="duel-score-row" title="{tt_exec_str}">
                    <span class="score-label" style="color:#94a3b8; cursor:help;">💀 {get_text("executions", lang=lang)}</span>
                    <div class="score-pill-sm" style="background:#1e293b; border-color:#334155; cursor:help;">
                        <b class="score-blue-sm" style="color:#cbd5e1;">{t1_execs}</b>
                        <span class="score-x-sm">x</span>
                        <b class="score-red-sm" style="color:#cbd5e1;">{t2_execs}</b>
                    </div>
                </div>
            </div>
            """


        duels_html.append(f"""
        <div class="duel-row team-combined-row">
            <div class="player-card border-blue">
                <div class="p-header">
                    <div class="team-avatar-stack">{t1_icons_html}</div>
                    <div class="p-meta">
                        <div class="p-name">{get_text("blue_team", lang=lang)}</div>
                        <div class="p-champ">KDA: <b>{t1_kills}/{t1_deaths}/{t1_assists}</b> <span class="kda-ratio">({ratio_t1:.2f}:1)</span></div>
                    </div>
                </div>

                <div class="stats-pills">
                    <div class="pill pill-wide pill-interactive" onclick="this.classList.toggle('is-pinned')">

                        <div class="pill-content-main">
                            <span>{lbl_dmg}: <b>{t1_dmg:,}</b> {t1_dmg_delta_tag}</span>
                        </div>
                        <div class="pill-content-detail">
                            <span class="dmg-breakdown-sub">{lbl_phys}: <b class="dmg-phys">{t1_phys:,}</b> <span class="breakdown-dot">•</span> {lbl_mag}: <b class="dmg-mag">{t1_mag:,}</b> <span class="breakdown-dot">•</span> {lbl_true}: <b class="dmg-true">{t1_tru:,}</b></span>
                        </div>
                    </div>
                    <div class="pill pill-wide pill-interactive" onclick="this.classList.toggle('is-pinned')">
                        <div class="pill-content-main">
                            <span>{lbl_soaked}: <b>{t1_taken + t1_mit:,}</b></span>
                        </div>
                        <div class="pill-content-detail">
                            <span class="dmg-breakdown-sub">{lbl_taken}: <b class="dmg-tk">{t1_taken:,}</b> <span class="breakdown-dot">•</span> {lbl_mit}: <b class="dmg-mit">{t1_mit:,}</b> <span class="breakdown-dot">•</span> {lbl_hl}: <b class="dmg-hl">{t1_hl:,}</b></span>
                        </div>
                    </div>
                    <div class="pill pill-wide">
                        <span><img class="mini-icon" src="{icon_gold}"/> <b>{t1_gold:,}</b> {t1_gold_delta_tag} <span style="color:var(--text-muted); font-size:0.75rem;">({round(t1_dmg / max(t1_gold, 1), 2)} dmg/g)</span></span>
                        <span><img class="mini-icon" src="{icon_cs}"/> <b>{t1_cs}</b> <span style='color:var(--text-muted); font-size:0.78rem;'>({csm_t1}/m)</span></span>
                    </div>
                    <div class="pill pill-wide">
                        <span>{t1_vis_combined}</span>
                        <span><img class="mini-icon-gromp" src="{AssetManager.get_asset_uri('gromp_icon')}" alt="Gromp"/> {get_text('camps_stolen', lang=lang)}: <b>{t1_camps}</b></span>
                    </div>
                </div>
            </div>

            <div class="duel-center">
                <div class="role-badge-lg" style="background:#3730a3; color:#c7d2fe;">{get_text("team_combined_title", lang=lang)}</div>
                <div class="lane-bar-wrapper">
                    <div class="lane-bar-container" title="{get_text('gold_dist_team_tt', lang=lang)}">
                        <div class="lane-bar-blue" style="width: {calculate_gold_bar_share(t1_gold - t2_gold, max_delta=15000.0):.1f}%;"></div>
                        <div class="lane-bar-red" style="width: {100.0 - calculate_gold_bar_share(t1_gold - t2_gold, max_delta=15000.0):.1f}%;"></div>
                    </div>
                </div>
                {team_exec_html}
                {delta_gold_section}
            </div>


            <div class="player-card border-red">
                <div class="p-header" style="justify-content: flex-end;">
                    <div class="p-meta" style="text-align: right;">
                        <div class="p-name">{get_text("red_team", lang=lang)}</div>
                        <div class="p-champ">KDA: <b>{t2_kills}/{t2_deaths}/{t2_assists}</b> <span class="kda-ratio">({ratio_t2:.2f}:1)</span></div>
                    </div>
                    <div class="team-avatar-stack">{t2_icons_html}</div>
                </div>
                <div class="stats-pills">
                    <div class="pill pill-wide pill-interactive" onclick="this.classList.toggle('is-pinned')">
                        <div class="pill-content-main">
                            <span>{lbl_dmg}: <b>{t2_dmg:,}</b> {t2_dmg_delta_tag}</span>
                        </div>
                        <div class="pill-content-detail">
                            <span class="dmg-breakdown-sub">{lbl_phys}: <b class="dmg-phys">{t2_phys:,}</b> <span class="breakdown-dot">•</span> {lbl_mag}: <b class="dmg-mag">{t2_mag:,}</b> <span class="breakdown-dot">•</span> {lbl_true}: <b class="dmg-true">{t2_tru:,}</b></span>
                        </div>
                    </div>
                    <div class="pill pill-wide pill-interactive" onclick="this.classList.toggle('is-pinned')">
                        <div class="pill-content-main">
                            <span>{lbl_soaked}: <b>{t2_taken + t2_mit:,}</b></span>
                        </div>
                        <div class="pill-content-detail">
                            <span class="dmg-breakdown-sub">{lbl_taken}: <b class="dmg-tk">{t2_taken:,}</b> <span class="breakdown-dot">•</span> {lbl_mit}: <b class="dmg-mit">{t2_mit:,}</b> <span class="breakdown-dot">•</span> {lbl_hl}: <b class="dmg-hl">{t2_hl:,}</b></span>
                        </div>
                    </div>


                    <div class="pill pill-wide">
                        <span><img class="mini-icon" src="{icon_gold}"/> <b>{t2_gold:,}</b> {t2_gold_delta_tag} <span style="color:var(--text-muted); font-size:0.75rem;">({round(t2_dmg / max(t2_gold, 1), 2)} dmg/g)</span></span>
                        <span><img class="mini-icon" src="{icon_cs}"/> <b>{t2_cs}</b> <span style='color:var(--text-muted); font-size:0.78rem;'>({csm_t2}/m)</span></span>
                    </div>
                    <div class="pill pill-wide">
                        <span>{t2_vis_combined}</span>
                        <span><img class="mini-icon-gromp" src="{AssetManager.get_asset_uri('gromp_icon')}" alt="Gromp"/> {get_text('camps_stolen', lang=lang)}: <b>{t2_camps}</b></span>
                    </div>
                </div>
            </div>
        </div>
        """)

    return "".join(duels_html)
