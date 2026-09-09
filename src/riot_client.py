import requests
import time
import urllib.parse
from typing import Optional, List, Dict, Any
from .config import get_api_key, get_key_expires_at, get_prod_key, get_dev_key, get_dev_expires_at, get_key_candidates, set_key_preference, DEFAULT_ROUTING, DEFAULT_REGION
from .cache_manager import get_cached_match, save_cached_match, get_cached_timeline, save_cached_timeline, claim_match_owner
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
            self.key_kind, self.api_key = self._pick_first_usable_candidate(session_key)
        self._tried_values = {self.api_key} if self.api_key else set()
        if not self.api_key:
            raise RiotAPIError(get_text("err_key_missing", lang=self.lang))
        self.headers = {"X-Riot-Token": self.api_key}

    @staticmethod
    def _classify_key(value: str) -> str:
        if value and value == get_prod_key():
            return "prod"
        if value and value == get_dev_key():
            return "dev"
        return "session" if value else ""

    @staticmethod
    def _is_known_expired(kind: str) -> bool:
        """Only DEV_KEY carries a locally-known expiry we can check with no network
        call — PROD_KEY is always "permanent" and a session key's real status is
        unknown until Riot actually rejects it, so neither is ever pre-filtered here."""
        if kind != "dev":
            return False
        exp_val = get_dev_expires_at()
        return bool(exp_val) and str(exp_val).isdigit() and time.time() >= int(exp_val)

    def _pick_first_usable_candidate(self, session_key: str):
        """Skips any candidate already known to be dead instead of blindly taking
        whichever comes first in priority order. Without this, a site owner's own
        forgotten, unrefreshed DEV_KEY sitting ahead of a visitor's session key in
        that order would permanently block construction — raising "key expired" for
        EVERY visitor regardless of how valid their own pasted key is — the moment
        _key_preference ever flips to "dev" (which any single failed PROD_KEY
        request causes, and nothing ever flips it back except this exact fix)."""
        for kind, value in get_key_candidates(session_key):
            if value and not self._is_known_expired(kind):
                return kind, value
        return "", ""

    def _switch_to_alternate_key(self) -> bool:
        """On a 401/403, try the next untried, not-known-dead candidate (prod/dev/
        session) before giving up. Whichever one works becomes the preferred prod/
        dev key going forward — not a permanent blacklist of the one that failed,
        just try-order, so it gets retried again once the currently-preferred one
        fails too."""
        for kind, value in get_key_candidates(self.session_key):
            if value and value not in self._tried_values and not self._is_known_expired(kind):
                self.api_key = value
                self.key_kind = kind
                self.headers = {"X-Riot-Token": self.api_key}
                self._tried_values.add(value)
                if kind in ("prod", "dev"):
                    set_key_preference(kind)
                return True
        return False

    def _request(self, url: str) -> Any:
        if not self.api_key:
            raise RiotAPIError(get_text("err_key_missing", lang=self.lang))
        for _ in range(5):
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
                if self._switch_to_alternate_key():
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
        # A real 404 (wrong cluster for this account) comes back as None from
        # _request, not an exception — so any RiotAPIError raised here means every
        # key candidate already failed (missing/expired/invalid) or we're rate
        # limited, which no amount of cluster-hopping fixes. Let it propagate
        # instead of swallowing it into a misleading "summoner not found".
        routings = [self.routing] + [r for r in ["americas", "asia", "europe"] if r != self.routing and r != "sea"]
        for r in routings:
            url = f"https://{r}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name_encoded}/{tag_encoded}"
            data = self._request(url)
            if data and "puuid" in data:
                return data["puuid"]
        raise RiotAPIError(get_text("err_summoner_not_found", lang=self.lang, name=game_name, tag=tag_line))

    def get_recent_matches(self, puuid: str, count: int = 8, start: int = 0, queue: Optional[int] = None) -> List[str]:
        # Same reasoning as get_puuid above: a real 404 returns None here, so a
        # raised RiotAPIError always means a key problem, not a wrong cluster.
        routings = [self.routing] + [r for r in ["americas", "asia", "europe", "sea"] if r != self.routing]
        for r in routings:
            url = f"https://{r}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
            if queue:
                url += f"&queue={queue}"
            matches = self._request(url)
            if matches:
                return matches
        return []

    def get_match_detail(self, match_id: str, target_puuid: str = "") -> Dict[str, Any]:
        cached = get_cached_match(match_id)
        if cached:
            if claim_match_owner(match_id, target_puuid):
                cached["metadata"]["target_puuid"] = target_puuid
            return cached
        
        # Determine routing cluster from match_id prefix
        from .config import get_routing_for_match_id
        cluster = get_routing_for_match_id(match_id)
        
        # Clean canonical match_id (e.g. convert KR1_xxx to KR_xxx if needed)
        norm_match_id = match_id
        if match_id.upper().startswith("KR1_"):
            norm_match_id = "KR_" + match_id[4:]

        url = f"https://{cluster}.api.riotgames.com/lol/match/v5/matches/{norm_match_id}"
        # No try/except here: a RiotAPIError (missing/expired/invalid key, rate limit)
        # means every cluster would fail identically, so it should surface as-is
        # instead of being masked as "match not found" below.
        data = self._request(url)

        if not data:
            # A clean 404 (no exception) — genuinely worth trying other clusters.
            for fallback_cluster in ["americas", "asia", "europe", "sea"]:
                if fallback_cluster == cluster:
                    continue
                data = self._request(f"https://{fallback_cluster}.api.riotgames.com/lol/match/v5/matches/{norm_match_id}")
                if data:
                    break
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
        # Same reasoning as get_match_detail: let a real RiotAPIError propagate
        # instead of swallowing it and reporting a misleading "not found".
        data = self._request(url)

        if not data:
            for fallback_cluster in ["americas", "asia", "europe", "sea"]:
                if fallback_cluster == cluster:
                    continue
                data = self._request(f"https://{fallback_cluster}.api.riotgames.com/lol/match/v5/matches/{norm_match_id}/timeline")
                if data:
                    break
        if not data:
            raise RiotAPIError(get_text("err_timeline_not_found", lang=self.lang, match_id=match_id))
        save_cached_timeline(match_id, data)
        return data

