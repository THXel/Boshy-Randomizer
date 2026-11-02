"""Local, read-only browser/OBS tracker. No PinguLexa or game engine imports."""

import argparse
import json
import mimetypes
import math
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from tracker.source import ROWS, read_feed
from tracker.details import present as present_details

PORT = 18765
URL = f"http://127.0.0.1:{PORT}/"
WEB = Path(__file__).parent / "web"
from app_paths import REPO

ASSETS = REPO / "assets"
FIELDS = (
    "updated_at",
    "mode",
    "play_mode",
    "phase",
    "run_id",
    "slot",
    "seed",
    "share_seed",
    "character",
    "difficulty",
    "location",
    "elapsed",
    "timer_running",
    "deaths",
    "checks_done",
    "checks_total",
    "language",
)


class Assets:
    def __init__(self, root=ASSETS):
        self.files = {}
        self.names = {}
        self.frames = {}
        for folder in ("Custom/trophies", "menu-character-icons", "loading-icons"):
            for path in sorted((root / folder).glob("*")):
                if path.suffix.lower() not in (".png", ".webp"):
                    continue
                key = f"/icons/{len(self.files)}{path.suffix.lower()}"
                self.files[key] = path
                self.names.setdefault(path.stem.casefold(), key)
                if folder == "loading-icons":
                    self.frames[path.name] = key
        self.fallback = self.names.get("trophy", self.names.get("boshy", ""))
        self.logo = root / "Custom/boshy_randomizer.png"
        if self.logo.is_file():
            self.files["/logo.png"] = self.logo
        try:
            self.index = json.loads((root / "loading-icons/index.json").read_text())
        except (OSError, ValueError):
            self.index = {}

    def icon(self, row):
        if row.get("frame") is not None:
            entry = self.index.get(str(row["frame"]), {})
            path = self.frames.get(entry.get("icon"))
            if path:
                return path
        name = row.get("name", "").casefold()
        name = {"secret mario": "mario"}.get(name, name)
        return self.names.get(name, self.fallback)

    def row(self, row):
        return dict(
            name=row["name"],
            kind=row.get("kind", "item"),
            done=row["done"],
            current=bool(row.get("current")),
            icon=self.icon(row),
        )


def present(data, assets):
    if data is None:
        return dict(connected=False)
    state = {key: data[key] for key in FIELDS if key in data}
    state["connected"] = True
    state.update(present_details(data))
    for key in ROWS:
        state[key] = [assets.row(row) for row in data.get(key, [])]
    state["events"] = []
    events = data.get("events", [])
    if isinstance(events, list):
        for event in events[-64:]:
            if (
                isinstance(event, dict)
                and isinstance(event.get("id"), str)
                and isinstance(event.get("name"), str)
                and event.get("run_id") == data.get("run_id")
                and event.get("kind") in ("item", "character", "boss")
                and isinstance(event.get("time"), (int, float))
                and math.isfinite(event["time"])
            ):
                state["events"].append(
                    {
                        **{key: event[key] for key in ("id", "kind", "name", "time")},
                        "icon": assets.icon(event),
                    }
                )
    return state


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=PORT, *, source=read_feed, assets=None):
        self.source = source
        self.assets = assets or Assets()
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        port = self.server.server_port
        allowed = (f"127.0.0.1:{port}", f"localhost:{port}")
        origin = self.headers.get("Origin")
        if self.headers.get("Host") not in allowed or (
            origin and origin not in tuple("http://" + host for host in allowed)
        ):
            self.send_error(403)
            return
        path = urlsplit(self.path).path
        if path == "/health":
            self.respond(
                json.dumps(dict(application="boshy-fusion-tracker", schema=1)).encode(),
                "application/json",
            )
        elif path == "/state":
            data = present(self.server.source(), self.server.assets)
            self.respond(
                json.dumps(data, ensure_ascii=False, allow_nan=False).encode(),
                "application/json",
            )
        else:
            routes = {
                "/": WEB / "index.html",
                "/overlay": WEB / "index.html",
                "/app.js": WEB / "app.js",
                "/style.css": WEB / "style.css",
                **self.server.assets.files,
            }
            file = routes.get(path)
            if file is None or not file.is_file():
                self.send_error(404)
                return
            self.respond(
                file.read_bytes(),
                mimetypes.guess_type(str(file))[0] or "application/octet-stream",
            )

    def respond(self, data, content_type):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            content_type
            + (
                "; charset=utf-8"
                if content_type.startswith(("text/", "application/json"))
                else ""
            ),
        )
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'self'",
        )
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


def existing(port=PORT):
    try:
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
            return json.load(response).get("application") == "boshy-fusion-tracker"
    except (OSError, ValueError, AttributeError):
        return False


def start(port=PORT):
    """One browser endpoint per desktop; an occupied unrelated port is an error."""
    try:
        server = Server(port)
    except OSError:
        if existing(port):
            return None
        raise
    thread = threading.Thread(
        target=server.serve_forever, daemon=True, name="boshy-tracker-http"
    )
    thread.start()
    return server


def stop(server):
    if server:
        server.shutdown()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="Open the desktop tracker")
    args = parser.parse_args()
    server = start()
    if args.open:
        webbrowser.open(URL)
    print(URL, flush=True)
    if server:
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            stop(server)


if __name__ == "__main__":
    main()
