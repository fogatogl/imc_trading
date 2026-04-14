"""Serve backtests/ with CORS headers for the IMC visualizer."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 8765
DIRECTORY = Path(__file__).parent / "imc_commun" / "backtests"


class CORSHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # silence request logs


handler = partial(CORSHandler, directory=str(DIRECTORY))
server = HTTPServer(("127.0.0.1", PORT), handler)
print(f"Serving {DIRECTORY} at http://127.0.0.1:{PORT}/")
server.serve_forever()
