import requests
import time
from typing import Optional, List, Dict, Any
from .config import RIOT_API_KEY, RIOT_KEY_EXPIRES_AT, DEFAULT_ROUTING, DEFAULT_REGION
from .cache_manager import get_cached_match, save_cached_match, get_cached_timeline, save_cached_timeline

class RiotAPIError(Exception):
    pass

class RiotClient:
    def __init__(self, api_key: Optional[str] = None, routing: str = DEFAULT_ROUTING, region: str = DEFAULT_REGION):
        self.api_key = api_key or RIOT_API_KEY
        self.routing = routing
        self.region = region
        self._check_key_validity()
        self.headers = {"X-Riot-Token": self.api_key}

    def _check_key_validity(self):
        if not self.api_key:
            raise RiotAPIError("RIOT_API_KEY não configurada. Defina no arquivo .env")
        if RIOT_KEY_EXPIRES_AT and str(RIOT_KEY_EXPIRES_AT).isdigit():
            exp_ts = int(RIOT_KEY_EXPIRES_AT)
            if time.time() >= exp_ts:
                raise RiotAPIError("Sua chave de desenvolvimento da Riot EXPIROU! Gere uma nova em developer.riotgames.com e atualize seu .env.")

    def _request(self, url: str) -> Any:
        self._check_key_validity()
        for _ in range(3):
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                time.sleep(retry_after)
                continue
            elif resp.status_code == 404:
                return None
            elif resp.status_code in (401, 403):
                raise RiotAPIError("Chave de API inválida ou expirada. Atualize em developer.riotgames.com")
            else:
                raise RiotAPIError(f"Erro na API Riot [{resp.status_code}]: {resp.text}")
        raise RiotAPIError("Rate limit excedido repetidamente.")

    def get_puuid(self, game_name: str, tag_line: str) -> str:
        url = f"https://{self.routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        data = self._request(url)
        if not data or "puuid" not in data:
            raise RiotAPIError(f"Jogador {game_name}#{tag_line} não encontrado.")
        return data["puuid"]

    def get_recent_matches(self, puuid: str, count: int = 5, queue: Optional[int] = None) -> List[str]:
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}"
        if queue:
            url += f"&queue={queue}"
        matches = self._request(url)
        return matches or []

    def get_match_detail(self, match_id: str) -> Dict[str, Any]:
        cached = get_cached_match(match_id)
        if cached:
            return cached
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        data = self._request(url)
        if not data:
            raise RiotAPIError(f"Partida {match_id} não encontrada.")
        save_cached_match(match_id, data)
        return data

    def get_match_timeline(self, match_id: str) -> Dict[str, Any]:
        cached = get_cached_timeline(match_id)
        if cached:
            return cached
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
        data = self._request(url)
        if not data:
            raise RiotAPIError(f"Timeline para a partida {match_id} não encontrada.")
        save_cached_timeline(match_id, data)
        return data
