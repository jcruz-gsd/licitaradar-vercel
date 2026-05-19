"""GET /api/categorias — distribución por categoría tecnológica."""
import json, os
from http.server import BaseHTTPRequestHandler
from supabase import create_client


TABLA = "licitaciones_gsd"

CATEGORIAS = {
    "Software y soluciones": [
        "software", "solución tecnológica", "solución digital",
        "desarrollo web", "desarrollo de software", "aplicación móvil",
        "plataforma digital", "transformación digital",
        "sistema informático", "sistema de información",
        "erp", "crm", "business intelligence", "app móvil",
        "sistema de gestión", "portal web",
    ],
    "Equipos y hardware": [
        "computador", "laptop", "notebook", "tablet",
        "monitor", "impresora", "equipo computacional",
        "equipamiento tecnológico", "equipos de computación",
        "hardware", "dispositivos tecnológicos", "servidor",
        "storage", "ups computacional", "data center",
        "equipo informático", "pc escritorio", "all in one",
    ],
    "Servicios TI": [
        "soporte técnico informático", "soporte ti",
        "mantención de equipos computacionales", "mantención de sistemas",
        "mantención de red", "mantención correctiva de equipos",
        "infraestructura ti", "redes informáticas", "redes de datos",
        "ciberseguridad", "seguridad informática", "helpdesk",
        "mesa de ayuda", "licencias de software", "cloud computing",
        "hosting", "datacenter", "virtualización", "backup",
        "soporte de software", "administración de sistemas",
    ],
    "Telecomunicaciones": [
        "telecomunicaciones", "telefonía ip", "internet",
        "fibra óptica", "conectividad", "banda ancha",
        "voip", "comunicaciones unificadas", "red wan",
        "red lan", "enlace dedicado",
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
