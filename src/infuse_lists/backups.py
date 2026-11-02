"""Snapshot Infuse's list files before every write, and restore them on demand."""
import datetime
import os
import shutil
import sqlite3

from . import paths

KEEP = 20


def create():
    name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = os.path.join(paths.BACKUPS, name)
    os.makedirs(target)
    src = sqlite3.connect(f"file:{paths.META_DB}?mode=ro", uri=True)
    with sqlite3.connect(os.path.join(target, os.path.basename(paths.META_DB))) as dst:
        src.backup(dst)
    src.close()
    if os.path.exists(paths.PLAYLISTS):
        shutil.copy2(paths.PLAYLISTS, target)
    for old in available()[KEEP:]:
        shutil.rmtree(os.path.join(paths.BACKUPS, old), ignore_errors=True)
    return target


def available():
    try:
        return sorted(os.listdir(paths.BACKUPS), reverse=True)
    except FileNotFoundError:
        return []


def restore(name):
    source = os.path.join(paths.BACKUPS, name)
    if not os.path.isdir(source):
        raise FileNotFoundError(f"No backup named {name}")
    db = os.path.join(source, os.path.basename(paths.META_DB))
    with sqlite3.connect(db) as src, sqlite3.connect(paths.META_DB) as dst:
        src.backup(dst)
    plist = os.path.join(source, os.path.basename(paths.PLAYLISTS))
    if os.path.exists(plist):
        shutil.copy2(plist, paths.PLAYLISTS)
