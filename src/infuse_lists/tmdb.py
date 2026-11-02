"""Optional TMDB lookups (original language, production countries, Latin person names), cached on disk."""
import json
import os
import time
import urllib.error
import urllib.request

from . import paths

API = "https://api.themoviedb.org/3"
CACHE_FILE = os.path.join(paths.CACHE, "tmdb.json")
MAX_AGE = 90 * 86400


class Tmdb:
    def __init__(self, key):
        self.key = key
        self.cache = {"movie": {}, "person": {}}
        try:
            with open(CACHE_FILE) as f:
                self.cache.update(json.load(f))
        except (OSError, ValueError):
            pass
        self.dirty = False

    def _get(self, path):
        url = f"{API}{path}"
        headers = {"Accept": "application/json"}
        # v4 read-access tokens are long JWTs; v3 keys are 32 hex chars
        if len(self.key) > 40:
            headers["Authorization"] = f"Bearer {self.key}"
        else:
            url += f"?api_key={self.key}"
        req = urllib.request.Request(url, headers=headers)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code == 401:
                    raise SystemExit("TMDB rejected the API key (401). Check tmdb_api_key in your config.")
                if e.code == 429 and attempt < 2:
                    time.sleep(2)
                    continue
                raise
        return None

    def _cached(self, kind, key, fetch):
        entry = self.cache[kind].get(str(key))
        if entry and time.time() - entry.get("_at", 0) < MAX_AGE:
            return entry
        data = fetch() or {}
        data["_at"] = time.time()
        self.cache[kind][str(key)] = data
        self.dirty = True
        return data

    def movie(self, tmdb_id):
        if not tmdb_id:
            return {}

        def fetch():
            d = self._get(f"/movie/{tmdb_id}")
            if not d:
                return {}
            return {
                "original_language": d.get("original_language"),
                "countries": sorted({c["iso_3166_1"] for c in d.get("production_countries", [])}
                                    | set(d.get("origin_country", []))),
            }

        return self._cached("movie", tmdb_id, fetch)

    def person_name(self, person_id):
        def fetch():
            d = self._get(f"/person/{person_id}")
            return {"name": d.get("name")} if d else {}

        return self._cached("person", person_id, fetch).get("name")

    def save(self):
        if self.dirty:
            os.makedirs(paths.CACHE, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f)
            self.dirty = False
