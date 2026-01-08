import argparse
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from datetime import datetime, timezone


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path) -> dict:
    st = path.stat()
    return {
        "path": str(path),
        "size": st.st_size,
        "mtime": st.st_mtime,
        "sha256": sha256_file(path),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_db(db_path: Path) -> dict:
    if db_path.exists():
        return json.loads(db_path.read_text(encoding="utf-8"))
    return {"created_at": now_iso(), "files": {}}


def save_db(db_path: Path, db: dict) -> None:
    tmp = db_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(db_path)


def log_line(log_path: Path, msg: str) -> None:
    line = f"{now_iso()}  {msg}\n"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")


def should_ignore(path: Path, ignore_hidden: bool) -> bool:
    name = path.name
    if ignore_hidden and name.startswith("."):
        return True
    return False


def is_regular_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def build_baseline(targets: list[Path], db_path: Path, log_path: Path, ignore_hidden: bool) -> None:
    db = {"created_at": now_iso(), "files": {}}
    count = 0

    for t in targets:
        t = t.resolve()
        if t.is_file():
            files = [t]
        else:
            files = [p for p in t.rglob("*") if p.is_file()]

        for p in files:
            if should_ignore(p, ignore_hidden):
                continue
            try:
                db["files"][str(p.resolve())] = file_record(p.resolve())
                count += 1
            except (OSError, PermissionError) as e:
                log_line(log_path, f"BASELINE_SKIP path={p} err={e}")

    save_db(db_path, db)
    log_line(log_path, f"BASELINE_DONE files={count} db={db_path}")


class FIMHandler(FileSystemEventHandler):
    def __init__(self, db_path: Path, log_path: Path, ignore_hidden: bool):
        self.db_path = db_path
        self.log_path = log_path
        self.ignore_hidden = ignore_hidden
        self.db = load_db(db_path)

    def _update_file(self, path: Path, action: str) -> None:
        path = path.resolve()
        if should_ignore(path, self.ignore_hidden):
            return
        if not is_regular_file(path):
            return

        try:
            rec = file_record(path)
        except (OSError, PermissionError) as e:
            log_line(self.log_path, f"{action}_SKIP path={path} err={e}")
            return

        old = self.db["files"].get(str(path))
        self.db["files"][str(path)] = rec
        save_db(self.db_path, self.db)

        if old is None:
            log_line(self.log_path, f"CREATED path={path} sha256={rec['sha256']}")
        else:
            if old["sha256"] != rec["sha256"]:
                log_line(self.log_path, f"MODIFIED path={path} old={old['sha256']} new={rec['sha256']}")
            else:
                # metadata change only (mtime/size)
                log_line(self.log_path, f"TOUCHED path={path} sha256={rec['sha256']}")

    def _remove_file(self, path: Path, action: str) -> None:
        path = path.resolve()
        if should_ignore(path, self.ignore_hidden):
            return

        old = self.db["files"].pop(str(path), None)
        save_db(self.db_path, self.db)

        if old is not None:
            log_line(self.log_path, f"{action} path={path} last_sha256={old['sha256']}")
        else:
            log_line(self.log_path, f"{action} path={path} last_sha256=UNKNOWN")

    # Events
    def on_created(self, event):
        if not event.is_directory:
            self._update_file(Path(event.src_path), "CREATE")

    def on_modified(self, event):
        if not event.is_directory:
            self._update_file(Path(event.src_path), "MODIFY")

    def on_moved(self, event):
        if event.is_directory:
            return
        src = Path(event.src_path)
        dst = Path(event.dest_path)
        # remove old, add new
        self._remove_file(src, "RENAMED_FROM")
        self._update_file(dst, "RENAMED_TO")

    def on_deleted(self, event):
        if not event.is_directory:
            self._remove_file(Path(event.src_path), "DELETED")


def run_monitor(targets: list[Path], db_path: Path, log_path: Path, ignore_hidden: bool) -> None:
    handler = FIMHandler(db_path=db_path, log_path=log_path, ignore_hidden=ignore_hidden)
    observer = Observer()

    for t in targets:
        t = t.resolve()
        watch_dir = t if t.is_dir() else t.parent
        observer.schedule(handler, str(watch_dir), recursive=True)
        log_line(log_path, f"WATCHING dir={watch_dir}")

    observer.start()
    log_line(log_path, "MONITOR_STARTED")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_line(log_path, "MONITOR_STOPPING")
        observer.stop()

    observer.join()
    log_line(log_path, "MONITOR_STOPPED")


def main():
    ap = argparse.ArgumentParser(description="Simple File Integrity Monitor (FIM)")
    ap.add_argument("targets", nargs="+", help="Files/folders to monitor")
    ap.add_argument("--db", default="fim_db.json", help="Baseline DB JSON path")
    ap.add_argument("--log", default="fim.log", help="Log file path")
    ap.add_argument("--baseline", action="store_true", help="Build baseline and exit")
    ap.add_argument("--ignore-hidden", action="store_true", help="Ignore dotfiles like .env, .git")
    args = ap.parse_args()

    targets = [Path(t) for t in args.targets]
    db_path = Path(args.db)
    log_path = Path(args.log)

    if args.baseline:
        build_baseline(targets, db_path, log_path, args.ignore_hidden)
        return

    # Ensure baseline exists
    if not db_path.exists():
        log_line(log_path, f"NO_BASELINE db={db_path} -> building baseline first")
        build_baseline(targets, db_path, log_path, args.ignore_hidden)

    run_monitor(targets, db_path, log_path, args.ignore_hidden)


if __name__ == "__main__":
    main()
