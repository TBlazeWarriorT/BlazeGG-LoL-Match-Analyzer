import os
import sys
import glob
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import MATCH_CACHE_DIR, TIMELINE_CACHE_DIR
from src.cache_manager import load_json, get_last_viewed
from src.ddragon import DataDragon
from src.event_engine import MatchAnalysis
from src.formatter import format_as_whatsapp_text

def main():
    last_session = get_last_viewed()
    match_id = None
    target_puuid = None

    if last_session:
        match_id = last_session.get("match_id")
        target_puuid = last_session.get("puuid")

    if not match_id or not (MATCH_CACHE_DIR / f"{match_id}.json").exists():
        match_files = glob.glob(str(MATCH_CACHE_DIR / "*.json"))
        if not match_files:
            print("\n[!] Nenhuma partida em cache encontrada!")
            print("Baixe uma partida primeiro usando 3_BAIXAR_NOVA_PARTIDA.bat")
            input("\nPressione Enter para fechar...")
            return
        latest_file = max(match_files, key=os.path.getmtime)
        match_id = Path(latest_file).stem

    match_data = load_json(MATCH_CACHE_DIR / f"{match_id}.json")
    timeline_data = load_json(TIMELINE_CACHE_DIR / f"{match_id}.json") or {}

    ddragon = DataDragon()
    analyzer = MatchAnalysis(match_data, timeline_data, target_puuid=target_puuid, ddragon=ddragon)

    print("\n" + "="*50)
    print(f"DADOS DA ULTIMA PARTIDA SALVA ({match_id})")
    print("="*50 + "\n")
    print(format_as_whatsapp_text(analyzer.generate_summary()))
    print("\n" + "="*50)
    input("\nPressione Enter para sair...")

if __name__ == "__main__":
    main()
