import sys
import argparse
from src.riot_client import RiotClient, RiotAPIError
from src.ddragon import DataDragon
from src.event_engine import MatchAnalysis
from src.cache_manager import set_last_viewed
from src.formatter import format_as_whatsapp_text, format_as_llm_json, format_timeframe_events

def interactive_mode():
    print("\n=== LoL Match Analyzer ===")
    riot_id = input("Digite o Riot ID (ex: Noob Master 46#CWB): ").strip()
    if not riot_id or "#" not in riot_id:
        print("Riot ID invalido! Deve conter GameName#TagLine.")
        return

    game_name, tag_line = riot_id.split("#", 1)
    client = RiotClient()
    ddragon = DataDragon()

    print(f"Buscando partidas de {game_name}#{tag_line}...")
    try:
        puuid = client.get_puuid(game_name, tag_line)
        matches = client.get_recent_matches(puuid, count=5)
    except RiotAPIError as e:
        print(f"Erro: {e}")
        return

    if not matches:
        print("Nenhuma partida encontrada.")
        return

    print("\nUltimas partidas:")
    for idx, mid in enumerate(matches, 1):
        print(f" [{idx}] {mid}")

    choice = input("\nEscolha a partida (1-5) [Padrao: 1]: ").strip()
    match_index = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(matches) else 0
    selected_match = matches[match_index]

    print(f"\nCarregando dados da partida {selected_match}...")
    match_data = client.get_match_detail(selected_match)
    timeline_data = client.get_match_timeline(selected_match)
    set_last_viewed(selected_match, puuid, riot_id)

    analyzer = MatchAnalysis(match_data, timeline_data, target_puuid=puuid, ddragon=ddragon)

    print("\nOpcoes de Analise:")
    print(" [1] Relatorio Formatado (WhatsApp)")
    print(" [2] Payload JSON (LLM)")
    print(" [3] Investigar Lance Específico (Timeframe MM:SS)")
    
    op = input("\nEscolha a opcao (1/2/3) [Padrao: 1]: ").strip()
    if op == "2":
        summary = analyzer.generate_summary()
        print("\n" + format_as_llm_json(summary))
    elif op == "3":
        start_t = input("Minuto inicial (ex: 12:00): ").strip() or "00:00"
        end_t = input("Minuto final (ex: 15:00): ").strip() or "20:00"
        events = analyzer.filter_timeframe(start_t, end_t)
        print("\n" + format_timeframe_events(events, start_t, end_t))
    else:
        summary = analyzer.generate_summary()
        print("\n" + format_as_whatsapp_text(summary))

def main():
    parser = argparse.ArgumentParser(description="LoL Match Analyzer to LLM/WhatsApp format")
    parser.add_argument("--player", help="Riot ID no formato GameName#TagLine")
    parser.add_argument("--match", help="Match ID específico (ex: BR1_1234567)")
    parser.add_argument("--format", choices=["text", "llm"], default="text", help="Formato de saída")
    parser.add_argument("--timeframe", help="Intervalo de tempo MM:SS-MM:SS para inspecionar")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        interactive_mode()
        return

    client = RiotClient()
    ddragon = DataDragon()
    puuid = None

    if args.player:
        if "#" not in args.player:
            print("Erro: --player deve ser Nome#Tag")
            return
        gname, tag = args.player.split("#", 1)
        puuid = client.get_puuid(gname, tag)

    match_id = args.match
    if not match_id and puuid:
        matches = client.get_recent_matches(puuid, count=1)
        if matches:
            match_id = matches[0]

    if not match_id:
        print("Erro: Forneca --match ou --player para buscar a partida.")
        return

    match_data = client.get_match_detail(match_id)
    timeline_data = client.get_match_timeline(match_id)
    if puuid:
        set_last_viewed(match_id, puuid, args.player or "")

    analyzer = MatchAnalysis(match_data, timeline_data, target_puuid=puuid, ddragon=ddragon)

    if args.timeframe:
        parts = args.timeframe.split("-")
        s, e = parts[0], parts[1] if len(parts) > 1 else parts[0]
        events = analyzer.filter_timeframe(s, e)
        print(format_timeframe_events(events, s, e))
    elif args.format == "llm":
        print(format_as_llm_json(analyzer.generate_summary()))
    else:
        print(format_as_whatsapp_text(analyzer.generate_summary()))

if __name__ == "__main__":
    main()
