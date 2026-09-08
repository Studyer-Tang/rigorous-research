"""Loopback-only research workbench, using the same kernel as CLI and MCP."""

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .core import Study
from .mcp_server import study_path
from .runner import run


def make_server(root, port=8765, propose=None):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    running = set()
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value, content_type="application/json; charset=utf-8"):
            raw = (
                value.encode("utf-8")
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False).encode("utf-8")
            )
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'self'; script-src 'nonce-{token}'; style-src 'nonce-{token}'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            )
            self.end_headers()
            self.wfile.write(raw)

        def allowed(self, write=False):
            authority = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != authority:
                return False
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{authority}":
                return False
            return not write or (
                self.headers.get("X-Research-Token") == token and self.headers.get("Content-Type") == "application/json"
            )

        def do_GET(self):
            if not self.allowed():
                self.reply(403, {"error": "request origin not allowed"})
                return
            query = urlparse(self.path)
            try:
                if query.path == "/":
                    html = (
                        Path(__file__)
                        .with_name("workbench.html")
                        .read_text(encoding="utf-8")
                        .replace("__SESSION_TOKEN__", token)
                    )
                    self.reply(200, html, "text/html; charset=utf-8")
                elif query.path == "/api/studies":
                    with lock:
                        active = sorted(running)
                    self.reply(
                        200,
                        {
                            "studies": [
                                p.name
                                for p in sorted(root.iterdir())
                                if not p.is_symlink() and (p / "agent.sqlite3").is_file()
                            ],
                            "api_enabled": propose is not None,
                            "running": active,
                        },
                    )
                elif query.path in {"/api/context", "/api/export"}:
                    slug = parse_qs(query.query).get("study", [""])[0]
                    study = Study(study_path(root, slug))
                    self.reply(200, study.context() if query.path.endswith("context") else study.export())
                else:
                    self.reply(404, {"error": "not found"})
            except (ValueError, OSError) as exc:
                self.reply(400, {"error": str(exc)})

        def do_POST(self):
            if not self.allowed(write=True):
                self.reply(403, {"error": "request origin or session token not allowed"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1000000:
                    raise ValueError("request size must be in 1–1000000 bytes")
                data = json.loads(self.rfile.read(length))
                path = study_path(root, data["study"])
                if self.path == "/api/create":
                    result = Study.create(
                        root, data["study"], data["objective"], data.get("domain", "mathematics")
                    ).state()
                elif self.path == "/api/pause":
                    result = Study(path).pause(data["paused"])
                elif self.path == "/api/asset":
                    result = Study(path).add_asset(data["label"], data["values"])
                elif self.path == "/api/run":
                    if propose is None:
                        raise ValueError("Start the server with a selected API model, or use Codex MCP/CLI tools")
                    study = Study(path)
                    slug = data["study"]
                    with lock:
                        if slug in running:
                            raise ValueError("study already running")
                        running.add(slug)

                    def work():
                        try:
                            run(study, propose)
                        except Exception as exc:
                            study.event("runner_error", {"type": type(exc).__name__})
                        finally:
                            with lock:
                                running.discard(slug)

                    threading.Thread(target=work, daemon=True).start()
                    result = {"started": True, "steps": 12, "seconds": 600}
                else:
                    self.reply(404, {"error": "not found"})
                    return
                self.reply(200, result)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.reply(400, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def serve(root, port=8765, propose=None):
    try:
        server = make_server(root, port, propose)
    except OSError:
        if port != 8765:
            raise
        server = make_server(root, 0, propose)
        print("Default port unavailable; selected a free local port.", flush=True)
    print(f"Research workbench: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
