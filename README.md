# infuse-lists

Automatically build **playlists** and **collections** in [Infuse](https://firecore.com/infuse) on macOS from your own library's metadata:

- movies under a given duration ("Under 100 minutes")
- movies by language — French, German, English, Dutch, Spanish — or by production country
- one collection per director who has at least *N* films in your library
- filters by genre and release year

Lists are rebuilt on a schedule (e.g. every Sunday night), so new movies show up in them automatically. Playlists then sync to your iPhone, iPad and Apple TV through Infuse's own iCloud sync.

> [!WARNING]
> **Unofficial.** This tool is not affiliated with or endorsed by Firecore. It edits Infuse's internal files, whose format is undocumented and may change in any update. It backs up those files before every write and refuses to write on untested Infuse versions, but use it at your own risk.

---

## Requirements

- macOS with **Infuse 8.5** (Mac App Store version, in `/Applications`)
- Infuse **Library** mode enabled with your movies indexed (the tool reads Infuse's metadata; it never scans files itself)
- Python **3.11+** (`python3 --version`; install with `brew install python` if needed)
- [pipx](https://pipx.pypa.io) (`brew install pipx && pipx ensurepath`)
- Optional: a free [TMDB API key](https://www.themoviedb.org/settings/api) for original-language and country filters

## Install

```sh
pipx install git+https://github.com/lbnsq182/infuse-lists
infuse-lists init          # creates ~/.config/infuse-lists/config.toml
```

The first time a command reads Infuse's data, macOS may ask to allow your terminal to *access data from other apps* — click **Allow**.

## Quick start

```sh
infuse-lists shares        # 1. see your Infuse sources, pick the ones to use
open -e ~/.config/infuse-lists/config.toml   # 2. edit your lists
infuse-lists preview       # 3. see what would be created (read-only)
infuse-lists doctor        # 4. check the setup
# 5. quit Infuse, then:
infuse-lists apply
infuse-lists schedule      # 6. optional: run automatically every Sunday at 04:00
```

## Commands

| Command | What it does |
|---|---|
| `infuse-lists init [--force]` | Create the config file from the commented template |
| `infuse-lists shares` | List Infuse sources with a readable name, type, location and movie count |
| `infuse-lists doctor` | Check Infuse version, data access, config, selected shares, schedule |
| `infuse-lists preview [-v]` | Show the lists that would be written and their sizes (`-v`: also the movies). Read-only |
| `infuse-lists apply [--adopt] [--force]` | Back up, then write the lists. **Infuse must be closed** |
| `infuse-lists schedule [--day sunday] [--time 04:00] [--daily]` | Install a background job (launchd) that runs `apply` |
| `infuse-lists schedule --run-now` | Trigger the installed job once, to test it |
| `infuse-lists unschedule` | Remove the background job |
| `infuse-lists restore [latest\|NAME]` | List backups, or restore one (Infuse must be closed) |

All commands accept `--config PATH` to use another config file.

### `infuse-lists shares`

```
NAME            TYPE                  MOVIES  AUTO  ID                                    LOCATION
Local Files     Local files               16  no    685560B6-…                            Infuse's own folder on this Mac
Mac             Mac folders                0  no    D16A47C5-…                            folders added from this Mac
My NAS          WebDAV network share     492  yes   7748FD97-…                            me@nas.example.com:5006
```

With `shares = "auto"` the tool uses every network share (the `AUTO = yes` rows). To choose, list names or IDs:

```toml
shares = ["My NAS"]
```

Movies from **Local Files** and **Mac folders** are excluded by default: Infuse rejects a whole playlist if it contains one of them.

## Configuration

`~/.config/infuse-lists/config.toml` — the template created by `init` documents every option.

```toml
[general]
shares = "auto"
default_type = "playlist"          # or "collection"
prune = true                       # delete lists this tool made that are no longer configured
quit_infuse_when_scheduled = true
tmdb_api_key = ""                  # or env var TMDB_API_KEY

[[list]]
name = "Under 100 minutes"
duration_max = 100                 # minutes, exclusive
sort = "duration"

[[list]]
name = "Films français"
original_language = "fr"           # needs tmdb_api_key

[[list]]
name = "Nederlandse films"
original_language = "nl"
country = ["NL", "BE"]

[directors]
enabled = true
type = "collection"
min_movies = 2
name_template = "{name}"           # placeholders: {name}, {count}
```

### List options

| Option | Example | Notes |
|---|---|---|
| `name` | `"Under 100 minutes"` | Required, unique |
| `type` | `"playlist"` / `"collection"` | Default: `general.default_type` |
| `sort` | `"title"` / `"year"` / `"duration"` | Default: `"title"` |
| `duration_min`, `duration_max` | `60`, `100` | Minutes. Min inclusive, max exclusive |
| `year_min`, `year_max` | `1980`, `1989` | Release year, inclusive |
| `genre` | `"Comedy"` or `["Comedy", "Drama"]` | Genre names as shown in Infuse |
| `audio_language` | `"fr"` or `["de", "nl"]` | Detected from release-name tags, no TMDB needed |
| `original_language` | `"es"` | Film's original language, needs TMDB |
| `country` | `"FR"` or `["NL", "BE"]` | Production/origin country (ISO code), needs TMDB |

All filters given in a list must match.

### Languages

Supported codes: `fr` French · `de` German · `en` English · `nl` Dutch · `es` Spanish.

- **`original_language`** (recommended) asks TMDB which language the film was shot in. Accurate, needs `tmdb_api_key`. Results are cached in `~/Library/Caches/infuse-lists/`.
- **`audio_language`** looks for tags in file names: `FRENCH`, `TRUEFRENCH`, `VFF`, `VFQ`, `VOF`, `VF2` · `GERMAN`, `DEUTSCH` · `ENGLISH` · `DUTCH`, `FLEMISH` · `SPANISH`, `CASTELLANO`, `LATINO`. It finds dubbed versions too, and misses files without tags (most English releases have none).

### Directors

With `[directors] enabled = true`, every director with at least `min_movies` distinct films in the selected shares gets a list, sorted by release year. New directors appear automatically on the next run; directors who drop below the threshold are removed (with `prune = true`). With a TMDB key, non-Latin names (e.g. `박찬욱`) are replaced by their TMDB name (`Park Chan-wook`).

## Playlists vs. collections

| | Playlists | Collections |
|---|---|---|
| Where | *Playlists* section | *Library › Collections*, and grouped among movies |
| iCloud sync to other devices | **Yes** | Not reliable for collections created outside the app |
| Order | As written by the tool | As written by the tool |

Use playlists when you want the lists on every device.

## Automatic runs

```sh
infuse-lists schedule --day sunday --time 04:00
```

macOS blocks background jobs from reading other apps' data until you allow it **once**:

1. *System Settings › Privacy & Security › Full Disk Access*
2. Click **+**, press **⌘⇧G**, paste the Python path printed by `infuse-lists schedule`, enable it
3. Test: `infuse-lists schedule --run-now`, then check `~/Library/Logs/infuse-lists.log`

At run time, if Infuse is open it is quit, the lists are written, and Infuse is reopened (set `quit_infuse_when_scheduled = false` to skip the run instead). If the Mac sleeps at the scheduled time, the job runs at the next wake.

## Safety

- **Your lists are never touched.** The tool records the lists it creates (`~/Library/Application Support/infuse-lists/state.json`) and only updates or deletes those. If a list with the same name already exists in Infuse, it is skipped, unless you pass `--adopt` to take it over.
- **Backups before every write** of both Infuse files, in `~/Library/Application Support/infuse-lists/backups/` (last 20 kept). Restore with `infuse-lists restore latest`.
- **Version check**: on an Infuse version other than the tested ones, `apply` refuses to write unless `--force`.
- **Read-only** everywhere except `apply` and `restore`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Infuse is running` | Quit Infuse (⌘Q) before `apply`; it rewrites its files on exit |
| `Cannot read the library` / `Operation not permitted` | Allow access when macOS asks, or grant Full Disk Access to the Python path shown by `doctor` |
| A playlist does not appear in Infuse | Run `infuse-lists shares` and remove *Local Files* / *Mac folders* from `shares` |
| Lists don't reach iPhone / Apple TV | Same Infuse version on all devices; iCloud sync enabled in *Infuse › Settings › Sync*; prefer playlists |
| `has not been tested with this tool` | Infuse was updated. Try `preview`, then `apply --force` and check the result (restore if needed); please open an issue |
| Scheduled run did nothing | Check `~/Library/Logs/infuse-lists.log`; re-grant Full Disk Access after a Python upgrade |

## Uninstall

```sh
infuse-lists unschedule
pipx uninstall infuse-lists
rm -rf ~/.config/infuse-lists ~/Library/Application\ Support/infuse-lists ~/Library/Caches/infuse-lists
```

Lists already written stay in Infuse; delete them in the app.

## How it works

Infuse stores its library index in `com.firecore.media.meta.db` (SQLite) and custom playlists in `com.firecore.infuse.Playlists.plist`, both under `~/Library/Containers/com.firecore.infuse/Data/Library/Preferences/InternalPrefs/`. The tool reads movies, durations, genres and crew from the database, then writes playlists (NSKeyedArchiver-encoded file references) to the plist and collections to the `custom_collections` tables. Infuse picks them up on its next launch and syncs playlists through iCloud.

## Development

```sh
git clone https://github.com/lbnsq182/infuse-lists && cd infuse-lists
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
```

Tests use synthetic data only. Please never commit a real Infuse database: it contains your library and share addresses.

## License

MIT — see [LICENSE](LICENSE). Movie metadata comes from [TMDB](https://www.themoviedb.org/) via Infuse; this product uses the TMDB API but is not endorsed or certified by TMDB.
