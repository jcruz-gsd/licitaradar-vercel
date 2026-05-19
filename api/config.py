"""GET /api/config — leer configuración
   POST /api/config — guardar configuración"""
import json, os
from http.server import BaseHTTPRequestHandler
from supabase import create_client

TABLA = "app_config"

def get_sb():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        try:
            sb   = get_sb()
            rows = sb.table(TABLA).select("key,value").execute().data or []
            cfg  = {r["key"]: r["value"] for r in rows}
            self._json(200, cfg)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length) or "{}")
            sb     = get_sb()
            for key, value in body.items():
                sb.table(TABLA).upsert(
                    {"key": key, "value": str(value),
                     "updated_at": "now()"},
                    on_conflict="key"
                ).execute()
            self._json(200, {"ok": True})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors(); self.end_headers(); self.wfile.write(body)

    def log_message(self, *_): pass
