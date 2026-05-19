"""GET /api/categorias — distribución por categoría tecnológica."""
import json, os
from http.server import BaseHTTPRequestHandler
from supabase import create_client


TABLA = "licitaciones_gsd"

CATEGORIAS = {
    "Software y soluciones": [
        "software", "solución tecnológica", "solución digital", "desarrollo web",
        "aplicación", "plataforma digital", "transformación digital",
        "sistema informático", "sistema de información",
    ],
    "Equipos y hardware": [
        "computador", "laptop", "notebook", "tablet", "pantalla", "televisor",
        "monitor", "impresora", "equipo computacional", "equipamiento tecnológico",
        "equipos de computación", "hardware", "dispositivos tecnológicos",
    ],
    "Servicios TI": [
        "soporte técnico", "mantención", "infraestructura ti", "redes",
        "ciberseguridad", "helpdesk", "mesa de ayuda", "licencias de software",
    ],
    "Telecomunicaciones": [
        "telecomunicaciones", "telefonía", "internet", "fibra óptica",
        "conectividad", "banda ancha", "comunicaciones",
    ],
}


def get_sb():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            sb  = get_sb()
            raw = sb.table(TABLA).select("palabras_clave").execute().data or []

            # Build count per category
            counts = {cat: 0 for cat in CATEGORIAS}
            for row in raw:
                kws = row.get("palabras_clave") or []
                if isinstance(kws, str):
                    kws = [k.strip() for k in kws.split(",") if k.strip()]
                kw_lower = [k.lower() for k in kws]
                for cat, keywords in CATEGORIAS.items():
                    if any(kw in kw_lower for kw in keywords):
                        counts[cat] += 1

            categories = [
                {"name": cat, "count": counts[cat], "keywords": kws}
                for cat, kws in CATEGORIAS.items()
            ]
            self._json(200, {"categories": categories})
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
