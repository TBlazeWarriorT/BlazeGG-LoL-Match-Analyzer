import requests
import time
from typing import Optional, List, Dict, Any
from .config import get_api_key, get_key_expires_at, DEFAULT_ROUTING, DEFAULT_REGION
from .cache_manager import get_cached_match, save_cached_match, get_cached_timeline, save_cached_timeline
from .i18n import get_text

class RiotAPIError(Exception):
    pass

class RiotClient:
    def __init__(self, api_key: Optional[str] = None, routing: str = DEFAULT_ROUTING, region: str = DEFAULT_REGION, lang: str = "en_US"):
        self.api_key = api_key or get_api_key()
        self.routing = routing
        self.region = region
        self.lang = lang
        self._check_key_validity()
        self.headers = {"X-Riot-Token": self.api_key}

    def _check_key_validity(self):
        if not self.api_key:
            raise RiotAPIError(get_text("err_key_missing", lang=self.lang))
        exp_val = get_key_expires_at()
        if exp_val and str(exp_val).isdigit():
            exp_ts = int(exp_val)
            if time.time() >= exp_ts:
                raise RiotAPIError(get_text("err_key_expired", lang=self.lang))

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
                raise RiotAPIError(get_text("err_key_invalid", lang=self.lang))
            else:
                raise RiotAPIError(f"Riot API Error [{resp.status_code}]: {resp.text}")
        raise RiotAPIError(get_text("err_rate_limit", lang=self.lang))

    def get_puuid(self, game_name: str, tag_line: str) -> str:
        url = f"https://{self.routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        data = self._request(url)
        if not data or "puuid" not in data:
            raise RiotAPIError(get_text("err_summoner_not_found", lang=self.lang, name=game_name, tag=tag_line))
        return data["puuid"]

    def get_recent_matches(self, puuid: str, count: int = 8, start: int = 0, queue: Optional[int] = None) -> List[str]:
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
        if queue:
            url += f"&queue={queue}"
        matches = self._request(url)
        return matches or []


    def get_match_detail(self, match_id: str, target_puuid: str = "") -> Dict[str, Any]:
        cached = get_cached_match(match_id)
        if cached:
            if target_puuid and "metadata" in cached and not cached["metadata"].get("target_puuid"):
                cached["metadata"]["target_puuid"] = target_puuid
                save_cached_match(match_id, cached, target_puuid)
            return cached
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        data = self._request(url)
        if not data:
            raise RiotAPIError(get_text("err_match_not_found", lang=self.lang, match_id=match_id))
        save_cached_match(match_id, data, target_puuid)
        return data

    def get_match_timeline(self, match_id: str) -> Dict[str, Any]:
        cached = get_cached_timeline(match_id)
        if cached:
            return cached
        url = f"https://{self.routing}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
        data = self._request(url)
        if not data:
            raise RiotAPIError(get_text("err_timeline_not_found", lang=self.lang, match_id=match_id))
        save_cached_timeline(match_id, data)
        return data

