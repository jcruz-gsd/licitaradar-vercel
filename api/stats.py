"""GET /api/stats — estadísticas del dashboard + datos del gráfico."""
import json, os
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from supabase import create_client


TABLA = "licitaciones_gsd"


def get_sb():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            sb    = get_sb()
            today = datetime.now().strftime("%Y-%m-%d")
            since = (datetime.now() - timedelta(days=30)).isoformat()

            total  = sb.table(TABLA).select("id", count="exact").execute().count or 0
            today_ = (sb.table(TABLA).select("id", count="exact")
                        .gte("fecha_registro", today).execute().count or 0)
            emails = (sb.table(TABLA).select("id", count="exact")
                        .eq("notificado", True).execute().count or 0)
            active = (sb.table(TABLA).select("id", count="exact")
                        .ilike("estado", "%public%").execute().count or 0)

            # Chart: count per day last 30 days
            raw = (sb.table(TABLA).select("fecha_registro")
                     .gte("fecha_registro", since).execute().data or [])
            counts: dict = {}
            for row in raw:
                d = (row.get("fecha_registro") or "")[:10]
                if d:
                    counts[d] = counts.get(d, 0) + 1
            chart = [{"date": k, "count": v} for k, v in sorted(counts.items())]

            # Recent: last 5
            recent = (sb.table(TABLA)
                        .select("nombre,organismo,estado,palabras_clave,link,fecha_registro,codigo_externo")
                        .order("fecha_registro", desc=True)
                        .limit(5)
                        .execute().data or [])

            self._json(200, {
                "total": total, "today": today_,
                "emails": emails, "active": active,
                "chart": chart, "recent": recent,
            })
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ── helpers ──────────────────────────────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_): pass
