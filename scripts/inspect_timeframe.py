import os
import sys
import glob
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR
from src.cache_manager import load_json, get_last_viewed
from src.ddragon import DataDragon
from src.event_engine import MatchAnalysis
from src.formatter import format_timeframe_events

def main():
    last_session = get_last_viewed()
    match_id = None
    target_puuid = None

    if last_session:
        match_id = last_session.get("match_id")
        target_puuid = last_session.get("puuid")

    if not match_id or (not (MATCH_CACHE_DIR / f"{match_id}.json.gz").exists() and not (MATCH_CACHE_DIR / f"{match_id}.json").exists()):
        from src.cache_manager import list_cache_files
        match_files = list_cache_files(MATCH_CACHE_DIR)
        if not match_files:
            print("\n[!] Nenhuma partida em cache encontrada!")
            input("\nPressione Enter para fechar...")
            return
        latest_file = max(match_files, key=os.path.getmtime)
        match_id = latest_file.name.split(".")[0]

    match_data = load_json(MATCH_CACHE_DIR / f"{match_id}.json")
    timeline_data = load_json(TIMELINE_CACHE_DIR / f"{match_id}.json")

    if not timeline_data:
        print(f"\n[!] Timeline da partida {match_id} nao encontrada em cache!")
        input("\nPressione Enter para fechar...")
        return

    ddragon = DataDragon()
    analyzer = MatchAnalysis(match_data, timeline_data, target_puuid=target_puuid, ddragon=ddragon)

    print("\n" + "="*50)
    print(f"INVESTIGACAO DE LANCE (Partida: {match_id})")
    print("="*50)

    while True:
        print("\nDigite o intervalo de tempo para inspecionar:")
        start_t = input("Minuto Inicial (ex: 12:00 ou Enter p/ 00:00): ").strip() or "00:00"
        end_t = input("Minuto Final   (ex: 15:00 ou Enter p/ 20:00): ").strip() or "20:00"

        events = analyzer.filter_timeframe(start_t, end_t)
        print("\n" + "-"*40)
        print(format_timeframe_events(events, start_t, end_t))
        print("-"*40)

        continuar = input("\nDeseja olhar outro minuto desta partida? (s/n) [Padrao: n]: ").strip().lower()
        if continuar not in ("s", "sim", "y", "yes"):
            break

    input("\nPressione Enter para sair...")

if __name__ == "__main__":
    main()
