"""Serve only the standalone demo department sites on localhost:5500."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PORTALS = {
    "Bijli_vibhag": ROOT / "Bijli_vibhag",
    "jal vibhag": ROOT / "jal vibhag",
    "pwd": ROOT / "pwd",
    "shiksha_vibhag": ROOT / "shiksha_vibhag",
}


class PortalHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        parts = PurePosixPath(unquote(urlsplit(path).path).lstrip("/")).parts
        if not parts or parts[0] not in PORTALS:
            return str(ROOT / "__department_portal_not_found__")

        portal_root = PORTALS[parts[0]].resolve()
        requested = portal_root.joinpath(*parts[1:]).resolve()
        try:
            requested.relative_to(portal_root)
        except ValueError:
            return str(ROOT / "__department_portal_not_found__")
        return str(requested)

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/":
            links = "".join(
                f'<li><a href="/{name}/">{name}</a></li>' for name in PORTALS
            )
            body = (
                "<!doctype html><meta charset='utf-8'><title>Department demo portals</title>"
                "<h1>Nagrik Aawaz department demo portals</h1><ul>"
                f"{links}</ul>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5500), PortalHandler)
    print("Department demo portals: http://127.0.0.1:5500/")
    server.serve_forever()
