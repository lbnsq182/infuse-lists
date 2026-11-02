"""Track which Infuse lists this tool created, so user-made lists are never touched."""
import json
import os

from . import paths


def load():
    try:
        with open(paths.STATE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    return {"playlist": data.get("playlist", {}), "collection": data.get("collection", {})}


def save(state):
    os.makedirs(paths.SUPPORT, exist_ok=True)
    tmp = paths.STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, paths.STATE)


def plan(existing, owned, titles, adopt=False, prune=True):
    """Decide what to do with each wanted title.

    existing: {id: title} currently in Infuse; owned: {id: title} created by this tool.
    Returns (targets {title: id or None for new}, deletions [id], skipped [title]).
    """
    owned = {i: t for i, t in owned.items() if i in existing}
    owned_by_title = {t: i for i, t in owned.items()}
    foreign_by_title = {t: i for i, t in existing.items() if i not in owned}

    targets, skipped = {}, []
    for title in titles:
        if title in owned_by_title:
            targets[title] = owned_by_title[title]
        elif title in foreign_by_title:
            if adopt:
                targets[title] = foreign_by_title[title]
            else:
                skipped.append(title)
        else:
            targets[title] = None

    kept = set(targets.values())
    deletions = [i for i in owned if i not in kept] if prune else []
    return targets, deletions, skipped
