"""Read-only access to Infuse's metadata database."""
import sqlite3
from contextlib import closing

from . import paths

# cached_cast_and_crew.Role: 1 producer, 2 director, 3 writer, 4 actor
DIRECTOR_ROLE = 2


def connect(db=None):
    con = sqlite3.connect(f"file:{db or paths.META_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def movies(con, share_ids):
    marks = ",".join("?" * len(share_ids))
    rows = con.execute(
        f"""select m.ItemID, m.VFS_ID, m.Path, m.Title, m.SortTitle, m.DurationSec, m.MetaID, m.TmdbID,
                   m.ReleaseDate, m.Genre, f.Flags,
                   coalesce(f.ModificationDate, f.UpdateDate, 0) as ModDate
            from meta_movie m join FileIndex f on f.ItemID = m.ItemID
            where m.MarkedForDeletion = 0 and f.Enabled = 1 and m.VFS_ID in ({marks})
            order by coalesce(m.SortTitle, m.Title)""",
        share_ids,
    )
    return [dict(r) for r in rows]


def directors(con, movie_list, min_movies):
    """{(person_id, name): [movies]} for directors with at least min_movies distinct films."""
    by_meta = {}
    for m in movie_list:
        by_meta.setdefault(m["MetaID"], []).append(m)
    found = {}
    rows = con.execute(
        """select c.PersonID, p.Name, c.ItemMetaID from cached_cast_and_crew c
           join cached_persons p using (PersonID)
           where c.ItemType = 'movie' and c.Role = ?""",
        (DIRECTOR_ROLE,),
    )
    for pid, name, meta_id in rows:
        items = found.setdefault((pid, name), {})
        for m in by_meta.get(meta_id, []):
            items[m["ItemID"]] = m
    return {
        key: list(items.values())
        for key, items in sorted(found.items(), key=lambda kv: kv[0][1])
        if len({m["MetaID"] for m in items.values()}) >= min_movies
    }


def check_readable(db=None):
    with closing(connect(db)) as con:
        return con.execute("select count(*) from meta_movie").fetchone()[0]
