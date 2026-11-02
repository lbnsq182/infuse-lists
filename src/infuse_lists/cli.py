"""Command-line interface: infuse-lists <command>."""
import argparse
import os
import sys
import time
from contextlib import closing

from . import __version__, backups, config, engine, library, paths, schedule, shares


def cmd_init(args):
    if config.init(force=args.force):
        print(f"Created {paths.CONFIG}\nEdit it, then run `infuse-lists shares` and `infuse-lists preview`.")
    else:
        print(f"{paths.CONFIG} already exists (use --force to overwrite).")


def cmd_shares(args):
    with closing(library.connect()) as con:
        found = shares.load_shares(con)
    print(f"{'NAME':<22} {'TYPE':<22} {'MOVIES':>6}  {'AUTO':<4}  {'ID':<36}  LOCATION")
    for s in found:
        print(f"{s.name[:22]:<22} {s.kind[:22]:<22} {s.movies:>6}  {'yes' if s.syncable else 'no':<4}  {s.id:<36}  {s.location}")
    print('\nAUTO = used when config has shares = "auto". To pick explicitly, set e.g. shares = ["<NAME>"].')


def cmd_doctor(args):
    ok = True

    def line(good, text):
        nonlocal ok
        ok &= good
        print(f"[{'ok' if good else '!!'}] {text}")

    version = paths.infuse_version()
    line(bool(version), f"Infuse installed: {version or 'not found in /Applications'}")
    line(paths.version_supported(version), f"Infuse version tested with this tool ({', '.join(paths.TESTED_VERSIONS)}.x)")
    line(os.path.exists(paths.META_DB), f"Infuse library found: {paths.META_DB}")
    try:
        line(True, f"Library readable: {library.check_readable()} movie files")
    except Exception as e:
        line(False, f"Cannot read the library ({e}). Grant Full Disk Access to {schedule.python_binary()}")
    line(os.path.exists(paths.CONFIG), f"Config: {paths.CONFIG}")
    if os.path.exists(paths.CONFIG):
        cfg = config.load()
        line(True, f"TMDB key: {'set' if cfg['general']['tmdb_api_key'] else 'not set (original_language/country unavailable)'}")
        try:
            ids = shares.select(shares.load_shares(), cfg["general"]["shares"])
            line(bool(ids), f"Shares selected: {len(ids)}")
        except ValueError as e:
            line(False, str(e))
    print(f"[--] Infuse running: {'yes (close it before apply)' if paths.infuse_running() else 'no'}")
    print(f"[--] Schedule installed: {'yes' if schedule.installed() else 'no'}")
    sys.exit(0 if ok else 1)


def _show(lists, verbose):
    total = 0
    for kind, by_title in lists.items():
        for title, items in by_title.items():
            total += 1
            print(f"{kind:<10} {len(items):>4}  {title}")
            if verbose:
                for m in items:
                    print(f"{'':16}{(m['DurationSec'] or 0) / 60:4.0f} min  {m['Title']}")
    print(f"\n{total} list(s)")


def cmd_preview(args):
    _show(engine.build(config.load()), args.verbose)


def cmd_apply(args):
    print(f"=== infuse-lists {__version__} - {time.ctime()}", flush=True)
    cfg = config.load()
    version = paths.infuse_version()
    if not paths.version_supported(version) and not args.force:
        sys.exit(f"Infuse {version} has not been tested with this tool. Use --force to write anyway (backups are kept).")

    reopen = False
    if paths.infuse_running():
        if not (args.scheduled and cfg["general"]["quit_infuse_when_scheduled"]):
            sys.exit("Infuse is running. Quit it first (it overwrites its files on exit).")
        if not paths.quit_infuse():
            sys.exit("Infuse did not quit; nothing written.")
        reopen = True
    try:
        lists = engine.build(cfg)
        report = engine.apply(lists, adopt=args.adopt, prune=cfg["general"]["prune"])
    finally:
        if reopen:
            paths.open_infuse()

    print(f"Backup: {report['backup']}")
    for kind in engine.STORES:
        r = report[kind]
        print(f"{kind}s: {len(r['created'])} created, {len(r['updated'])} updated, {len(r['deleted'])} deleted")
        for label in ("created", "deleted"):
            if r[label]:
                print(f"  {label}: {', '.join(r[label])}")
        if r["skipped"]:
            print(f"  skipped (a list with this name was made in Infuse; use --adopt to take it over): {', '.join(r['skipped'])}")


def cmd_schedule(args):
    hour, minute = (int(x) for x in args.time.split(":"))
    schedule.install(args.day, hour, minute, every_day=args.daily)
    when = "every day" if args.daily else f"every {args.day.capitalize()}"
    print(f"Scheduled {when} at {hour:02d}:{minute:02d}. Log: {paths.LOG}")
    print(f"\nRequired once: System Settings > Privacy & Security > Full Disk Access > + > Cmd-Shift-G and add:\n  {schedule.python_binary()}")
    print("Then test with: infuse-lists schedule --run-now")


def cmd_run_now(args):
    schedule.run_now()
    print(f"Started. Follow progress in {paths.LOG}")


def cmd_unschedule(args):
    schedule.uninstall()
    print("Schedule removed.")


def cmd_restore(args):
    names = backups.available()
    if not args.name:
        print("\n".join(names) or "No backups yet.")
        return
    if paths.infuse_running():
        sys.exit("Quit Infuse first.")
    backups.restore(names[0] if args.name == "latest" and names else args.name)
    print("Restored.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="infuse-lists", description="Build Infuse playlists and collections from your library.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--config", help=f"config file (default: {paths.CONFIG})")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create the config file")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_init)
    sub.add_parser("shares", help="list Infuse sources with readable labels").set_defaults(func=cmd_shares)
    sub.add_parser("doctor", help="check that everything is set up").set_defaults(func=cmd_doctor)
    s = sub.add_parser("preview", help="show the lists that would be written (read-only)")
    s.add_argument("-v", "--verbose", action="store_true", help="also list the movies")
    s.set_defaults(func=cmd_preview)
    s = sub.add_parser("apply", help="write the lists to Infuse (Infuse must be closed)")
    s.add_argument("--adopt", action="store_true", help="take over same-named lists made in Infuse")
    s.add_argument("--force", action="store_true", help="write even on an untested Infuse version")
    s.add_argument("--scheduled", action="store_true", help=argparse.SUPPRESS)
    s.set_defaults(func=cmd_apply)
    s = sub.add_parser("schedule", help="run apply automatically (launchd)")
    s.add_argument("--day", default="sunday", choices=schedule.DAYS)
    s.add_argument("--time", default="04:00", help="HH:MM, 24h")
    s.add_argument("--daily", action="store_true")
    s.add_argument("--run-now", action="store_true", help="trigger the installed schedule once")
    s.set_defaults(func=lambda a: cmd_run_now(a) if a.run_now else cmd_schedule(a))
    sub.add_parser("unschedule", help="remove the automatic run").set_defaults(func=cmd_unschedule)
    s = sub.add_parser("restore", help="list backups, or restore one ('latest' or a name)")
    s.add_argument("name", nargs="?")
    s.set_defaults(func=cmd_restore)

    args = p.parse_args(argv)
    if args.config:
        paths.CONFIG = os.path.abspath(os.path.expanduser(args.config))
    args.func(args)


if __name__ == "__main__":
    main()
