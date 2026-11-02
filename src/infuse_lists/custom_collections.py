"""Read/write Infuse custom collections (tables in com.firecore.media.meta.db)."""
import plistlib
import sqlite3
import time
import uuid
from plistlib import UID

from . import paths


def _file_info(m):
    objs = [
        "$null",
        {"NS.keys": [UID(2), UID(3)], "NS.objects": [UID(4), UID(5)], "$class": UID(7)},
        "kFCFileInfoIsDirKey",
        "kFCFileInfoModificationDateKey",
        bool(m["Flags"] & 16),
        {"NS.time": float(m["ModDate"]), "$class": UID(6)},
        {"$classname": "NSDate", "$classes": ["NSDate", "NSObject"]},
        {"$classname": "NSDictionary", "$classes": ["NSDictionary", "NSObject"]},
    ]
    archive = {"$version": 100000, "$archiver": "NSKeyedArchiver", "$top": {"root": UID(1)}, "$objects": objs}
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY)


class Collections:
    def __init__(self, db=paths.META_DB):
        self.con = sqlite3.connect(db)
        self.con.execute("begin")
        # Items left behind by collections deleted in the app
        self.con.execute(
            "delete from custom_collection_items where CollectionId not in (select CollectionId from custom_collections)"
        )

    def existing(self):
        return dict(self.con.execute("select CollectionId, Title from custom_collections"))

    def put(self, cid, title, items):
        cid = cid or str(uuid.uuid4()).upper()
        self.con.execute("delete from custom_collection_items where CollectionId = ?", (cid,))
        self.con.execute(
            "insert or replace into custom_collections (CollectionId, Type, Title, ModificationDate, ThumbState)"
            " values (?, 1, ?, ?, 0)",
            (cid, title, time.time()),
        )
        self.con.executemany(
            "insert into custom_collection_items (CollectionId, ItemOrder, ItemType, Title, ItemID, Season,"
            " VFS_ID, Path, FileInfo) values (?, ?, 'Video', ?, ?, NULL, ?, ?, ?)",
            [(cid, i, m["Title"], m["ItemID"], m["VFS_ID"], m["Path"], _file_info(m)) for i, m in enumerate(items)],
        )
        return cid

    def delete(self, cid):
        self.con.execute("delete from custom_collection_items where CollectionId = ?", (cid,))
        self.con.execute("delete from custom_collections where CollectionId = ?", (cid,))

    def save(self):
        self.con.commit()
        self.con.close()

    def discard(self):
        self.con.rollback()
        self.con.close()
