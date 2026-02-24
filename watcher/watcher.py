import os, time, hashlib
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")
API_KEY = os.getenv("API_KEY_INTERNAL", "internal_watcher_key_change_me")

_seen = {}

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def should_ignore(path: str) -> bool:
    name = os.path.basename(path)
    if name.startswith("~$"):
        return True
    low = name.lower()
    return low.endswith(".tmp") or low.endswith(".part")

def ingest(path: str):
    time.sleep(3)
    if not os.path.exists(path) or os.path.isdir(path):
        return
    if should_ignore(path):
        return

    try:
        h = sha256(path)
    except Exception:
        return
    if _seen.get(path) == h:
        return
    _seen[path] = h

    payload = {"api_key": API_KEY, "path": path, "folder_hint": os.path.dirname(path)}
    try:
        r = requests.post(f"{API_BASE_URL.rstrip('/')}/api/internal/ingest", json=payload, timeout=30)
        print("ingest", path, r.status_code, r.text[:200])
    except Exception as e:
        print("ingest failed", path, e)

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            ingest(event.src_path)
    def on_modified(self, event):
        if not event.is_directory:
            ingest(event.src_path)

def main():
    watch = "/watch"
    os.makedirs(watch, exist_ok=True)
    print("Watching:", watch)
    obs = Observer()
    obs.schedule(Handler(), path=watch, recursive=True)
    obs.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()

if __name__ == "__main__":
    main()
