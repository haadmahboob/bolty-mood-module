"""Tiny local server for the reel recorder.
Serves this folder and saves POST /upload?name=<file> into this folder."""
import http.server, os, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def do_POST(self):
        q = urllib.parse.urlparse(self.path)
        name = os.path.basename(urllib.parse.parse_qs(q.query).get("name", ["reel.webm"])[0])
        if q.path != "/upload" or not (name.startswith("bolty-reel") or name.startswith("check-")):
            self.send_error(400)
            return
        n = int(self.headers.get("Content-Length", 0))
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(self.rfile.read(n))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"saved {name} {n} bytes".encode())


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
