"""POST /api/login — valida credenciales contra variables de entorno."""
import json, os
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length) or "{}")
            email  = (body.get("email") or "").strip().lower()
            pwd    = (body.get("password") or "").strip()

            expected_email = (os.environ.get("APP_EMAIL") or "").strip().lower()
            expected_pwd   = (os.environ.get("APP_PASSWORD") or "").strip()

            if email == expected_email and pwd == expected_pwd:
                self._json(200, {"ok": True, "user": email})
            else:
                self._json(401, {"ok": False, "error": "Correo o contraseña incorrectos."})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})

    # ── helpers ──────────────────────────────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_): pass
