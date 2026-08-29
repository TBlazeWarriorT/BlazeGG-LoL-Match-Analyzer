from typing import Dict, Any, List
from ..asset_cache import AssetManager
from ..i18n import get_text

def assign_competition_ranks(items: List[Any], key_fn, max_items: int = 3) -> List[tuple]:
    """
    Standard competition ranking (1224 ranking):
    Equal values get the rank of the first member of the tie.
    """
    sorted_items = sorted(items, key=key_fn, reverse=True)[:max_items]
    rank_classes = ["rank-gold", "rank-silver", "rank-bronze"]
    
    ranked_tuples = []
    current_rank_idx = 0
    
    for i, item in enumerate(sorted_items):
        val = key_fn(item)
        if i == 0:
            current_rank_idx = 0
        else:
            prev_val = key_fn(sorted_items[i - 1])
            if val < prev_val:
                current_rank_idx = i  # drops to the current position index (e.g. 0, 0 -> 2 bronze)
        
        cls = rank_classes[min(current_rank_idx, len(rank_classes) - 1)]
        ranked_tuples.append((item, cls))
    
    return ranked_tuples

def render_match_awards(data: Dict[str, Any], all_players: List[Dict[str, Any]], is_aram: bool = False, is_arena: bool = False, lang: str = "pt_BR") -> str:
    icon_gold = AssetManager.get_asset_uri("gold_icon")

    # 1. Jungle
    objs_source = data.get("all_objectives", [])
    if not objs_source:
        objs_source = [
            {"killer_champ": ev.get("killer_champ"), "killer_name": ev.get("killer_name")}
            for ev in data.get("key_events", []) if ev.get("type") == "objective"
        ]

    team_100 = data.get("team_100", {})
    team_200 = data.get("team_200", {})
    t1_players = team_100.get("players", [])
    t2_players = team_200.get("players", [])

    t1_jungler = next((p for p in t1_players if p.get("role") == "JUNGLE"), None)
    t2_jungler = next((p for p in t2_players if p.get("role") == "JUNGLE"), None)

    player_obj_scores = {}
    for p in all_players:
        key = (p.get("riot_id", ""), p.get("champion", ""))
        player_obj_scores[key] = 0

    for ev in objs_source:
        k_team = ev.get("killer_team", 0)
        k_champ = ev.get("killer_champ", "")
        k_name = ev.get("killer_name", "")

        if k_team == 100 and t1_jungler:
            t1_key = (t1_jungler.get("riot_id", ""), t1_jungler.get("champion", ""))
            player_obj_scores[t1_key] = player_obj_scores.get(t1_key, 0) + 1
        elif k_team == 200 and t2_jungler:
            t2_key = (t2_jungler.get("riot_id", ""), t2_jungler.get("champion", ""))
            player_obj_scores[t2_key] = player_obj_scores.get(t2_key, 0) + 1
        elif k_champ:
            k_key = (k_name, k_champ)
            player_obj_scores[k_key] = player_obj_scores.get(k_key, 0) + 1

    junglers_keys = set()
    if t1_jungler:
        junglers_keys.add((t1_jungler.get("riot_id", ""), t1_jungler.get("champion", "")))
    if t2_jungler:
        junglers_keys.add((t2_jungler.get("riot_id", ""), t2_jungler.get("champion", "")))

    top_jungle_filtered = [item for item in player_obj_scores.items() if item[1] > 0]
    jungle_ranked = assign_competition_ranks(
        top_jungle_filtered,
        key_fn=lambda x: (1 if x[0] in junglers_keys else 0, x[1]),
        max_items=2
    )

    jungle_items_list = []
    for (k_name, k_champ), count, rank_cls in [(item[0], item[1], cls) for item, cls in jungle_ranked]:
        found_p = next((p for p in all_players if p.get("champion") == k_champ), None)
        icon_src = found_p.get("champion_icon", "") if found_p else ""
        jungle_items_list.append(f"""
        <div class="award-item {rank_cls}" title="{k_name} • {k_champ} ({count} obj{'s' if count > 1 else ''})">
            <div class="award-champ-info">
                <div class="award-avatar-wrap" title="{k_champ}"><img class="award-avatar" src="{icon_src}" alt="{k_champ}"/></div>
                <span class="award-name">{k_name}</span>
            </div>
            <span class="award-val">{count} obj{'s' if count > 1 else ''}</span>
        </div>
        """)
    jungle_items = "".join(jungle_items_list) if jungle_items_list else f"<div style='color:var(--text-muted); font-size:0.82rem; font-style:italic;'>{get_text('no_data', lang=lang)}</div>"

    # 2. Mayhem
    mayhem_ranked = assign_competition_ranks(all_players, key_fn=lambda x: x.get("damage_to_champions", 0), max_items=3)
    mayhem_items = "".join([
        f"""
        <div class="award-item {rank_cls}" title="{p['riot_id']} • {p['champion']} ({p.get('damage_to_champions', 0):,} DMG)">
            <div class="award-champ-info">
                <div class="award-avatar-wrap" title="{p['champion']}"><img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/></div>
                <span class="award-name">{p['riot_id']}</span>
            </div>
            <span class="award-val">{p.get('damage_to_champions', 0):,} DMG</span>
        </div>
        """ for p, rank_cls in mayhem_ranked
    ])

    # 3. Greed
    greed_ranked = assign_competition_ranks(all_players, key_fn=lambda x: x.get("gold_total", 0), max_items=3)
    greed_items = "".join([
        f"""
        <div class="award-item {rank_cls}" title="{p['riot_id']} • {p['champion']} ({p.get('gold_total', 0):,} Gold)">
            <div class="award-champ-info">
                <div class="award-avatar-wrap" title="{p['champion']}"><img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/></div>
                <span class="award-name">{p['riot_id']}</span>
            </div>
            <span class="award-val">{p.get('gold_total', 0):,} <img class="mini-icon" src="{icon_gold}"/></span>
        </div>
        """ for p, rank_cls in greed_ranked
    ])

    # 4. Might
    might_ranked = assign_competition_ranks(all_players, key_fn=lambda x: x.get("damage_taken", 0) + x.get("damage_mitigated", 0), max_items=3)
    might_items = "".join([
        f"""
        <div class="award-item {rank_cls}" title="{p['riot_id']} • {p['champion']} ({(p.get('damage_taken', 0) + p.get('damage_mitigated', 0)):,} Soaked/Mitigated)">
            <div class="award-champ-info">
                <div class="award-avatar-wrap" title="{p['champion']}"><img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/></div>
                <span class="award-name">{p['riot_id']}</span>
            </div>
            <span class="award-val">{(p.get('damage_taken', 0) + p.get('damage_mitigated', 0)):,}</span>
        </div>
        """ for p, rank_cls in might_ranked
    ])

    # 5. Visionary
    vision_ranked = assign_competition_ranks(all_players, key_fn=lambda x: x.get("vision_score", 0), max_items=3)
    visionary_items = "".join([
        f"""
        <div class="award-item {rank_cls}" title="{p['riot_id']} • {p['champion']} ({p.get('vision_score', 0)} Vision Score)">
            <div class="award-champ-info">
                <div class="award-avatar-wrap" title="{p['champion']}"><img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/></div>
                <span class="award-name">{p['riot_id']}</span>
            </div>
            <span class="award-val">{p.get('vision_score', 0)} score ({p.get('detector_wards', 0)} <img class='mini-icon mini-icon-round' src='https://ddragon.leagueoflegends.com/cdn/14.16.1/img/item/2055.png' title='Control Wards'/>)</span>
        </div>
        """ for p, rank_cls in vision_ranked
    ])

    # 6. Demolisher
    turret_ranked = assign_competition_ranks(all_players, key_fn=lambda x: x.get("damage_to_turrets", 0), max_items=3)
    demolisher_items = "".join([
        f"""
        <div class="award-item {rank_cls}" title="{p['riot_id']} • {p['champion']} ({p.get('damage_to_turrets', 0):,} Turret DMG)">
            <div class="award-champ-info">
                <div class="award-avatar-wrap" title="{p['champion']}"><img class="award-avatar" src="{p['champion_icon']}" alt="{p['champion']}"/></div>
                <span class="award-name">{p['riot_id']}</span>
            </div>
            <span class="award-val">{p.get('damage_to_turrets', 0):,} DMG</span>
        </div>
        """ for p, rank_cls in turret_ranked
    ])


    award_cards = []

    if not is_aram and not is_arena and jungle_items_list:
        award_cards.append(f"""
        <div class="award-card">
            <div>
                <div class="award-header">{get_text('award_jungle_title', lang=lang)}</div>
                <div class="award-desc">{get_text('award_jungle_desc', lang=lang)}</div>
            </div>
            <div class="award-list">{jungle_items}</div>
        </div>
        """)

    if not is_arena:
        award_cards.append(f"""
        <div class="award-card">
            <div>
                <div class="award-header">{get_text('award_mayhem_title', lang=lang)}</div>
                <div class="award-desc">{get_text('award_mayhem_desc', lang=lang)}</div>
            </div>
            <div class="award-list">{mayhem_items}</div>
        </div>
        """)

    award_cards.append(f"""
    <div class="award-card">
        <div>
            <div class="award-header">{get_text('award_greed_title', lang=lang)}</div>
            <div class="award-desc">{get_text('award_greed_desc', lang=lang)}</div>
        </div>
        <div class="award-list">{greed_items}</div>
    </div>
    """)

    award_cards.append(f"""
    <div class="award-card">
        <div>
            <div class="award-header">{get_text('award_might_title', lang=lang)}</div>
            <div class="award-desc">{get_text('award_might_desc', lang=lang)}</div>
        </div>
        <div class="award-list">{might_items}</div>
    </div>
    """)

    if not is_aram and not is_arena:
        award_cards.append(f"""
        <div class="award-card">
            <div>
                <div class="award-header">{get_text('award_visionary_title', lang=lang)}</div>
                <div class="award-desc">{get_text('award_visionary_desc', lang=lang)}</div>
            </div>
            <div class="award-list">{visionary_items}</div>
        </div>
        """)

    if not is_arena:
        award_cards.append(f"""
        <div class="award-card">
            <div>
                <div class="award-header">{get_text('award_demolisher_title', lang=lang)}</div>
                <div class="award-desc">{get_text('award_demolisher_desc', lang=lang)}</div>
            </div>
            <div class="award-list">{demolisher_items}</div>
        </div>
        """)

    return f"""
    <div class="card">
        <h3>{get_text('match_awards_title', lang=lang)}</h3>
        <div class="awards-grid">
            {"".join(award_cards)}
        </div>
    </div>
    """ if award_cards else ""

