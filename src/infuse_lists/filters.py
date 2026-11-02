"""List filters. Each list in the config combines any of these (all must match)."""
import datetime
import re

# Release-name tags announcing an audio track in that language
AUDIO_TAGS = {
    "fr": r"(true)?french|vff|vfq|vfi|vf2|vof|vf",
    "de": r"german|deutsch|ger",
    "en": r"english|eng",
    "nl": r"dutch|flemish|nl",
    "es": r"spanish|espa[nñ]ol|castellano|latino|esp|spa",
}
SUPPORTED_LANGUAGES = tuple(AUDIO_TAGS)
_TAG_RE = {k: re.compile(rf"(?i)(?<![a-z0-9])(?:{v})(?![a-z0-9])") for k, v in AUDIO_TAGS.items()}


def audio_languages_from_name(path):
    return {lang for lang, rx in _TAG_RE.items() if rx.search(path)}


def year(m):
    ts = m.get("ReleaseDate")
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).year


def _as_list(v):
    return [v] if isinstance(v, str) else list(v or [])


def validate(spec):
    for key in ("original_language", "audio_language"):
        for lang in _as_list(spec.get(key)):
            if lang not in SUPPORTED_LANGUAGES:
                raise ValueError(f"List '{spec['name']}': unsupported {key} '{lang}' (use {', '.join(SUPPORTED_LANGUAGES)})")


def needs_tmdb(spec):
    return bool(spec.get("original_language") or spec.get("country"))


def build(spec, tmdb=None):
    """Return a predicate movie -> bool for one [[list]] entry."""
    validate(spec)
    checks = []

    lo, hi = spec.get("duration_min"), spec.get("duration_max")
    if lo is not None or hi is not None:
        def duration(m, lo=lo, hi=hi):
            minutes = (m["DurationSec"] or 0) / 60
            return minutes > 0 and (lo is None or minutes >= lo) and (hi is None or minutes < hi)
        checks.append(duration)

    if spec.get("year_min") or spec.get("year_max"):
        def years(m, lo=spec.get("year_min"), hi=spec.get("year_max")):
            y = year(m)
            return y is not None and (lo is None or y >= lo) and (hi is None or y <= hi)
        checks.append(years)

    if spec.get("genre"):
        wanted = {g.lower() for g in _as_list(spec["genre"])}
        checks.append(lambda m: bool(wanted & {g.strip().lower() for g in (m["Genre"] or "").split(",")}))

    if spec.get("audio_language"):
        wanted = set(_as_list(spec["audio_language"]))
        checks.append(lambda m: bool(wanted & audio_languages_from_name(m["Path"])))

    if needs_tmdb(spec):
        if tmdb is None:
            raise ValueError(f"List '{spec['name']}' uses original_language/country, which needs tmdb_api_key in the config.")
        if spec.get("original_language"):
            wanted = set(_as_list(spec["original_language"]))
            checks.append(lambda m: tmdb.movie(m["TmdbID"]).get("original_language") in wanted)
        if spec.get("country"):
            wanted = {c.upper() for c in _as_list(spec["country"])}
            checks.append(lambda m: bool(wanted & set(tmdb.movie(m["TmdbID"]).get("countries", []))))

    return lambda m: all(c(m) for c in checks)


SORTS = {
    "title": lambda m: (m["SortTitle"] or m["Title"] or "").lower(),
    "year": lambda m: (m["ReleaseDate"] or 0, (m["Title"] or "").lower()),
    "duration": lambda m: (m["DurationSec"] or 0),
}
