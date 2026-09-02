import requests
import time
import urllib.parse
from typing import Optional, List, Dict, Any
from .config import get_api_key, get_key_expires_at, get_prod_key, get_dev_key, get_dev_expires_at, set_key_preference, DEFAULT_ROUTING, DEFAULT_REGION
from .cache_manager import get_cached_match, save_cached_match, get_cached_timeline, save_cached_timeline
from .i18n import get_text

class RiotAPIError(Exception):
    pass

class RiotClient:
    def __init__(self, api_key: Optional[str] = None, routing: str = DEFAULT_ROUTING, region: str = DEFAULT_REGION, lang: str = "en_US", session_key: str = ""):
        self.routing = routing
        self.region = region
        self.lang = lang
        self.session_key = session_key
        if api_key:
            self.api_key = api_key
            self.key_kind = self._classify_key(api_key)
        else:
            self.api_key = get_api_key(session_key=session_key)
            self.key_kind = self._classify_key(self.api_key)
        self._check_key_validity()
        self.headers = {"X-Riot-Token": self.api_key}

    @staticmethod
    def _classify_key(value: str) -> str:
        if value and value == get_prod_key():
            return "prod"
        if value and value == get_dev_key():
            return "dev"
        return "session" if value else ""

    def _key_expiry_for(self, kind: str):
        if kind == "prod":
            return "permanent"
        if kind == "dev":
            return get_dev_expires_at()
        return ""

    def _check_key_validity(self):
        if not self.api_key:
            raise RiotAPIError(get_text("err_key_missing", lang=self.lang))
        exp_val = self._key_expiry_for(self.key_kind)
        if exp_val and str(exp_val).isdigit():
            exp_ts = int(exp_val)
            if time.time() >= exp_ts:
                raise RiotAPIError(get_text("err_key_expired", lang=self.lang))

    def _switch_to_alternate_key(self) -> bool:
        """On a 401/403, try the other of PROD/DEV before giving up. Whichever
        one works becomes the preferred key going forward (not a permanent
        blacklist of the one that failed — just try-order, so it gets retried
        again once the currently-preferred one fails too)."""
        if self.key_kind not in ("prod", "dev"):
            return False
        alt_kind = "dev" if self.key_kind == "prod" else "prod"
        alt_value = get_dev_key() if alt_kind == "dev" else get_prod_key()
        if not alt_value or alt_value == self.api_key:
            return False
        self.api_key = alt_value
        self.key_kind = alt_kind
        self.headers = {"X-Riot-Token": self.api_key}
        set_key_preference(alt_kind)
        return True

    def _request(self, url: str) -> Any:
        self._check_key_validity()
        switched = False
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
                if not switched and self._switch_to_alternate_key():
                    switched = True
                    continue
                err_key = "err_prod_key_invalid" if self.key_kind == "prod" else "err_dev_key_invalid"
                # Extract clean debugging status if returned by Riot
                detail_msg = f" [Riot API: {resp.status_code} {resp.reason}]" if resp.reason else f" [Riot API: {resp.status_code}]"
                raise RiotAPIError(get_text(err_key, lang=self.lang, detail=f"<br/><small style='opacity:0.8;'>{detail_msg}</small>"))
            else:
                raise RiotAPIError(f"Riot API Error [{resp.status_code}]: {resp.text}")
        raise RiotAPIError(get_text("err_rate_limit", lang=self.lang))

    def get_puuid(self, game_name: str, tag_line: str) -> str:
        # Try routing clusters for Riot Account-v1 (americas, asia, europe)
        name_encoded = urllib.parse.quote(game_name.strip())
        tag_encoded = urllib.parse.quote(tag_line.strip())
        routings = [self.routing] + [r for r in ["americas", "asia", "europe"] if r != self.routing and r != "sea"]
        for r in routings:
            url = f"https://{r}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name_encoded}/{tag_encoded}"
            try:
                data = self._request(url)
                if data and "puuid" in data:
                    return data["puuid"]
            except RiotAPIError as e:
                # If a regional cluster gives 403/404 during fallback search, try next cluster
                if "403" in str(e) or "404" in str(e):
                    continue
                raise
        raise RiotAPIError(get_text("err_summoner_not_found", lang=self.lang, name=game_name, tag=tag_line))

    def get_recent_matches(self, puuid: str, count: int = 8, start: int = 0, queue: Optional[int] = None) -> List[str]:
        # Search match ids across clusters if needed
        routings = [self.routing] + [r for r in ["americas", "asia", "europe", "sea"] if r != self.routing]
        for r in routings:
            url = f"https://{r}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
            if queue:
                url += f"&queue={queue}"
            try:
                matches = self._request(url)
                if matches:
                    return matches
            except RiotAPIError as e:
                if "403" in str(e) or "404" in str(e):
                    continue
                raise
        return []

    def get_match_detail(self, match_id: str, target_puuid: str = "") -> Dict[str, Any]:
        cached = get_cached_match(match_id)
        if cached:
            if target_puuid and "metadata" in cached and not cached["metadata"].get("target_puuid"):
                cached["metadata"]["target_puuid"] = target_puuid
                save_cached_match(match_id, cached, target_puuid)
            return cached
        
        # Determine routing cluster from match_id prefix
        from .config import get_routing_for_match_id
        cluster = get_routing_for_match_id(match_id)
        
        # Clean canonical match_id (e.g. convert KR1_xxx to KR_xxx if needed)
        norm_match_id = match_id
        if match_id.upper().startswith("KR1_"):
            norm_match_id = "KR_" + match_id[4:]

        url = f"https://{cluster}.api.riotgames.com/lol/match/v5/matches/{norm_match_id}"
        data = None
        try:
            data = self._request(url)
        except RiotAPIError:
            pass

        if not data:
            # Fallback across other clusters just in case
            for fallback_cluster in ["americas", "asia", "europe", "sea"]:
                if fallback_cluster == cluster:
                    continue
                try:
                    data = self._request(f"https://{fallback_cluster}.api.riotgames.com/lol/match/v5/matches/{norm_match_id}")
                    if data:
                        break
                except RiotAPIError:
                    continue
        if not data:
            raise RiotAPIError(get_text("err_match_not_found", lang=self.lang, match_id=match_id))
        save_cached_match(match_id, data, target_puuid)
        return data

    def get_match_timeline(self, match_id: str) -> Dict[str, Any]:
        cached = get_cached_timeline(match_id)
        if cached:
            return cached
        
        from .config import get_routing_for_match_id
        cluster = get_routing_for_match_id(match_id)
        
        norm_match_id = match_id
        if match_id.upper().startswith("KR1_"):
            norm_match_id = "KR_" + match_id[4:]

        url = f"https://{cluster}.api.riotgames.com/lol/match/v5/matches/{norm_match_id}/timeline"
        data = None
        try:
            data = self._request(url)
        except RiotAPIError:
            pass

        if not data:
            for fallback_cluster in ["americas", "asia", "europe", "sea"]:
                if fallback_cluster == cluster:
                    continue
                try:
                    data = self._request(f"https://{fallback_cluster}.api.riotgames.com/lol/match/v5/matches/{norm_match_id}/timeline")
                    if data:
                        break
                except RiotAPIError:
                    continue
        if not data:
            raise RiotAPIError(get_text("err_timeline_not_found", lang=self.lang, match_id=match_id))
        save_cached_timeline(match_id, data)
        return data

