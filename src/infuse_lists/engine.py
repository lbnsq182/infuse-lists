"""Turn the config into concrete lists, and write them to Infuse."""
from contextlib import closing

from . import backups, filters, library, shares, state
from .custom_collections import Collections
from .playlists import Playlists
from .tmdb import Tmdb

STORES = {"playlist": Playlists, "collection": Collections}


def _non_latin(name):
    return any(ord(ch) > 0x24F for ch in name)


def build(cfg):
    """Return {"playlist": {title: [movies]}, "collection": {title: [movies]}}."""
    general = cfg["general"]
    tmdb = Tmdb(general["tmdb_api_key"]) if general["tmdb_api_key"] else None
    out = {"playlist": {}, "collection": {}}
    with closing(library.connect()) as con:
        share_ids = shares.select(shares.load_shares(), general["shares"])
        movies = library.movies(con, share_ids)

        for spec in cfg["list"]:
            keep = filters.build(spec, tmdb)
            items = sorted((m for m in movies if keep(m)), key=filters.SORTS[spec["sort"]])
            out[spec["type"]][spec["name"]] = items

        d = cfg["directors"]
        if d["enabled"]:
            for (pid, name), items in library.directors(con, movies, d["min_movies"]).items():
                if d["latin_names"] and tmdb and _non_latin(name):
                    name = tmdb.person_name(pid) or name
                title = d["name_template"].format(name=name, count=len({m["MetaID"] for m in items}))
                out[d["type"]][title] = sorted(items, key=filters.SORTS[d["sort"]])
    if tmdb:
        tmdb.save()
    return out


def apply(lists, adopt=False, prune=True):
    """Write lists; returns a report {kind: {"created", "updated", "deleted", "skipped"}}."""
    backup = backups.create()
    st = state.load()
    report = {"backup": backup}
    for kind, store_cls in STORES.items():
        store = store_cls()
        try:
            existing = store.existing()
            targets, deletions, skipped = state.plan(existing, st[kind], list(lists[kind]), adopt, prune)
            owned = {i: t for i, t in st[kind].items() if i in existing and i not in deletions}
            created, updated = [], []
            for title, lid in targets.items():
                new_id = store.put(lid, title, lists[kind][title])
                (updated if lid else created).append(title)
                owned = {i: t for i, t in owned.items() if i != new_id} | {new_id: title}
            for lid in deletions:
                store.delete(lid)
            store.save()
        except Exception:
            if hasattr(store, "discard"):
                store.discard()
            raise
        st[kind] = owned
        state.save(st)
        report[kind] = {
            "created": created,
            "updated": updated,
            "deleted": [existing[i] for i in deletions],
            "skipped": skipped,
        }
    return report
