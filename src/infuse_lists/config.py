"""Load and validate ~/.config/infuse-lists/config.toml."""
import os
import shutil
import tomllib
from importlib import resources

from . import paths

LIST_KEYS = {
    "name", "type", "sort", "duration_min", "duration_max", "year_min", "year_max",
    "genre", "audio_language", "original_language", "country",
}
DIRECTOR_KEYS = {"enabled", "type", "min_movies", "name_template", "sort", "latin_names"}


def init(force=False):
    if os.path.exists(paths.CONFIG) and not force:
        return False
    os.makedirs(os.path.dirname(paths.CONFIG), exist_ok=True)
    with resources.as_file(resources.files("infuse_lists").joinpath("config.example.toml")) as src:
        shutil.copy(src, paths.CONFIG)
    return True


def load(path=None):
    path = path or paths.CONFIG
    if not os.path.exists(path):
        raise SystemExit(f"No config at {path}. Run `infuse-lists init` first.")
    with open(path, "rb") as f:
        cfg = tomllib.load(f)

    general = cfg.setdefault("general", {})
    general.setdefault("shares", "auto")
    general.setdefault("default_type", "playlist")
    general.setdefault("prune", True)
    general.setdefault("quit_infuse_when_scheduled", True)
    general["tmdb_api_key"] = os.environ.get("TMDB_API_KEY") or general.get("tmdb_api_key") or ""

    names = set()
    for spec in cfg.setdefault("list", []):
        unknown = set(spec) - LIST_KEYS
        if unknown:
            raise SystemExit(f"List '{spec.get('name')}': unknown option(s) {', '.join(sorted(unknown))}")
        if not spec.get("name"):
            raise SystemExit("Every [[list]] needs a name.")
        if spec["name"] in names:
            raise SystemExit(f"Duplicate list name '{spec['name']}'")
        names.add(spec["name"])
        spec.setdefault("type", general["default_type"])
        spec.setdefault("sort", "title")
        _check_type(spec["type"], spec["name"])

    d = cfg.setdefault("directors", {})
    unknown = set(d) - DIRECTOR_KEYS
    if unknown:
        raise SystemExit(f"[directors]: unknown option(s) {', '.join(sorted(unknown))}")
    d.setdefault("enabled", False)
    d.setdefault("type", "collection")
    d.setdefault("min_movies", 2)
    d.setdefault("name_template", "{name}")
    d.setdefault("sort", "year")
    d.setdefault("latin_names", True)
    _check_type(d["type"], "[directors]")
    return cfg


def _check_type(t, where):
    if t not in ("playlist", "collection"):
        raise SystemExit(f"{where}: type must be 'playlist' or 'collection', not '{t}'")
