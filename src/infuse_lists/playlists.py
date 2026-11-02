"""Read/write Infuse custom playlists (com.firecore.infuse.Playlists.plist)."""
import datetime
import os
import plistlib
import uuid
from plistlib import UID

from . import paths


def _items_archive(items):
    """NSKeyedArchiver NSArray of VFSItemDescriptor, as Infuse stores a playlist's 'items'."""
    objs = ["$null", None]
    classes = {}

    def add(o):
        objs.append(o)
        return UID(len(objs) - 1)

    def klass(name):
        if name not in classes:
            classes[name] = add({"$classname": name, "$classes": [name, "NSObject"]})
        return classes[name]

    entries = []
    for m in items:
        info = {
            "NS.keys": [add("kFCFileInfoModificationDateKey"), add("kFCFileInfoIsDirKey")],
            "NS.objects": [add({"NS.time": float(m["ModDate"]), "$class": klass("NSDate")}), add(bool(m["Flags"] & 16))],
            "$class": klass("NSDictionary"),
        }
        entries.append(add({
            "kVFSID": add(m["VFS_ID"]),
            "kPath": add(m["Path"]),
            "kFileInfo": add(info),
            "$class": klass("VFSItemDescriptor"),
        }))
    objs[1] = {"NS.objects": entries, "$class": klass("NSArray")}
    archive = {"$version": 100000, "$archiver": "NSKeyedArchiver", "$top": {"root": UID(1)}, "$objects": objs}
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY)


class Playlists:
    def __init__(self, path=paths.PLAYLISTS):
        self.path = path
        if os.path.exists(path):
            with open(path, "rb") as f:
                self.outer = plistlib.load(f)
        else:
            self.outer = {
                "$version": 100000, "$archiver": "NSKeyedArchiver", "$top": {"root": UID(1)},
                "$objects": ["$null", {"NS.keys": [UID(2)], "NS.objects": [UID(3)], "$class": UID(4)},
                             "CustomPlaylists", plistlib.dumps([], fmt=plistlib.FMT_BINARY),
                             {"$classname": "NSMutableDictionary",
                              "$classes": ["NSMutableDictionary", "NSDictionary", "NSObject"]}],
            }
        objs = self.outer["$objects"]
        root = objs[self.outer["$top"]["root"].data]
        keys = [objs[u.data] for u in root["NS.keys"]]
        if "CustomPlaylists" not in keys:
            raise RuntimeError("Unexpected Playlists.plist layout (no CustomPlaylists); refusing to write.")
        self.data_index = root["NS.objects"][keys.index("CustomPlaylists")].data
        flat = plistlib.loads(objs[self.data_index])
        # Stored as a flat [id, dict, id, dict, ...] list
        pairs = list(zip(flat[::2], flat[1::2]))
        if len(flat) % 2 or not all(isinstance(k, str) and isinstance(d, dict) and d.get("id") == k for k, d in pairs):
            raise RuntimeError("Unexpected CustomPlaylists layout; refusing to write.")
        self.entries = dict(pairs)

    def existing(self):
        return {i: d.get("title", "") for i, d in self.entries.items()}

    def put(self, pid, title, items):
        pid = pid or str(uuid.uuid4()).upper()
        entry = self.entries.setdefault(pid, {"id": pid, "type": 1})
        entry["title"] = title
        entry["items"] = _items_archive(items)
        entry["date"] = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        return pid

    def delete(self, pid):
        self.entries.pop(pid, None)

    def save(self):
        flat = [x for pid, d in self.entries.items() for x in (pid, d)]
        self.outer["$objects"][self.data_index] = plistlib.dumps(flat, fmt=plistlib.FMT_BINARY)
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as f:
            plistlib.dump(self.outer, f, fmt=plistlib.FMT_BINARY)
        os.replace(tmp, self.path)
