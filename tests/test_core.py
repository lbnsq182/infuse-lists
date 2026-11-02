import os
import plistlib
import tempfile
import unittest

from infuse_lists import filters, state
from infuse_lists.playlists import Playlists


def movie(**kw):
    m = {"ItemID": "A", "VFS_ID": "S", "Path": "/x.mkv", "Title": "X", "SortTitle": None, "DurationSec": 5400,
         "MetaID": "1", "TmdbID": "1", "ReleaseDate": 0, "Genre": "Drama", "Flags": 0, "ModDate": 800000000.0}
    m.update(kw)
    return m


class AudioTags(unittest.TestCase):
    def test_languages(self):
        cases = {
            "/Movie.2020.FRENCH.1080p.mkv": {"fr"},
            "/Movie.2020.TRUEFRENCH.mkv": {"fr"},
            "/Film (2021) MULTI VFF 1080p.mkv": {"fr"},
            "/Film.2019.GERMAN.DL.1080p.mkv": {"de"},
            "/Film.2019.DUTCH.1080p.mkv": {"nl"},
            "/Pelicula.2018.SPANISH.1080p.mkv": {"es"},
            "/Pelicula.2018.Castellano.mkv": {"es"},
            "/Movie.2020.1080p.WEB-DL.mkv": set(),
            "/Frenchman's.Creek.1944.mkv": set(),
        }
        for path, expected in cases.items():
            self.assertEqual(filters.audio_languages_from_name(path), expected, path)


class Filters(unittest.TestCase):
    def test_duration_bounds(self):
        keep = filters.build({"name": "t", "duration_min": 60, "duration_max": 100})
        self.assertTrue(keep(movie(DurationSec=60 * 60)))
        self.assertFalse(keep(movie(DurationSec=100 * 60)))
        self.assertFalse(keep(movie(DurationSec=0)))

    def test_genre(self):
        keep = filters.build({"name": "t", "genre": ["comedy"]})
        self.assertTrue(keep(movie(Genre="Drama,Comedy")))
        self.assertFalse(keep(movie(Genre="Drama")))

    def test_tmdb_required(self):
        with self.assertRaises(ValueError):
            filters.build({"name": "t", "original_language": "fr"})

    def test_unsupported_language(self):
        with self.assertRaises(ValueError):
            filters.build({"name": "t", "audio_language": "it"})


class Plan(unittest.TestCase):
    def test_never_touches_foreign_lists(self):
        existing = {"1": "Mine", "2": "Theirs", "3": "Old"}
        owned = {"1": "Mine", "3": "Old"}
        targets, deletions, skipped = state.plan(existing, owned, ["Mine", "Theirs", "New"])
        self.assertEqual(targets, {"Mine": "1", "New": None})
        self.assertEqual(skipped, ["Theirs"])
        self.assertEqual(deletions, ["3"])

    def test_adopt_and_no_prune(self):
        targets, deletions, _ = state.plan({"2": "Theirs", "3": "Old"}, {"3": "Old"}, ["Theirs"], adopt=True, prune=False)
        self.assertEqual(targets, {"Theirs": "2"})
        self.assertEqual(deletions, [])


class PlaylistFile(unittest.TestCase):
    def test_roundtrip_from_scratch(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "Playlists.plist")
            store = Playlists(path)
            pid = store.put(None, "Test", [movie(), movie(ItemID="B", Path="/dir", Flags=17)])
            store.save()

            again = Playlists(path)
            self.assertEqual(again.existing(), {pid: "Test"})
            items = plistlib.loads(again.entries[pid]["items"])["$objects"]
            paths = [o for o in items if isinstance(o, str) and o.startswith("/")]
            self.assertEqual(paths, ["/x.mkv", "/dir"])

            again.delete(pid)
            again.save()
            self.assertEqual(Playlists(path).existing(), {})


if __name__ == "__main__":
    unittest.main()
