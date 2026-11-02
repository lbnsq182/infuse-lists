"""Read the sources ("shares") configured in Infuse and describe them in plain words."""
import plistlib
from dataclasses import dataclass

from . import paths

# FCNetworkShare.Protocol values observed in Infuse 8.5
PROTOCOLS = {2: "SMB", 9: "WebDAV"}


@dataclass
class Share:
    id: str
    name: str
    kind: str
    location: str
    syncable: bool
    movies: int = 0


def _get(objs, value):
    return objs[value.data] if isinstance(value, plistlib.UID) else value


def load_shares(con=None):
    with open(paths.VFS, "rb") as f:
        archive = plistlib.load(f)
    objs = archive["$objects"]
    root = objs[archive["$top"]["root"].data]

    shares = []
    for uid in root["NS.objects"]:
        o = objs[uid.data]
        cls = objs[o["$class"].data]["$classname"]
        sid = _get(objs, o.get("identifier"))
        name = _get(objs, o.get("name")) or ""

        if cls == "VFSLocal":
            name = "Local Files" if name == "vfLocalFiles" else name
            kind, location, syncable = "Local files", "Infuse's own folder on this Mac", False
        elif cls == "VFSBookmarks":
            kind, location, syncable = "Mac folders", "folders added from this Mac", False
        elif cls == "VFSRemote":
            s = _get(objs, o.get("Share")) or {}
            proto = PROTOCOLS.get(s.get("Protocol"), f"protocol {s.get('Protocol')}")
            user = _get(objs, s.get("Username")) or ""
            host = _get(objs, s.get("Host")) or "?"
            port = s.get("Port")
            base = _get(objs, s.get("BasePath")) or ""
            location = f"{user + '@' if user else ''}{host}{f':{port}' if port else ''}{base if base not in ('', '/') else ''}"
            kind, syncable = f"{proto} network share", True
        else:
            kind = {"VFSLibrary": "Library (virtual)", "VFSLinks": "Links (virtual)"}.get(cls, cls)
            location, syncable = "", False
        shares.append(Share(sid, name, kind, location, syncable))

    if con is not None:
        counts = dict(con.execute("select VFS_ID, count(*) from meta_movie where MarkedForDeletion = 0 group by VFS_ID"))
        for s in shares:
            s.movies = counts.get(s.id, 0)
    return shares


def select(shares, wanted):
    """Resolve the config value ("auto" or a list of IDs/names) to share IDs."""
    if wanted == "auto":
        return [s.id for s in shares if s.syncable]
    by_key = {s.id.lower(): s for s in shares} | {s.name.lower(): s for s in shares}
    unknown = [w for w in wanted if w.lower() not in by_key]
    if unknown:
        raise ValueError(f"Unknown share(s) in config: {', '.join(unknown)}. Run `infuse-lists shares`.")
    return [by_key[w.lower()].id for w in wanted]
