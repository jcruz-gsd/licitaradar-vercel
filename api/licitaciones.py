"""GET /api/licitaciones — lista paginada con filtros opcionales."""
import json, os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from supabase import create_client


TABLA    = "licitaciones_gsd"
PER_PAGE = 10


def get_sb():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            params   = parse_qs(urlparse(self.path).query)
            page     = max(1, int(params.get("page",     ["1"])[0]))
            per_page = max(1, min(100, int(params.get("per_page", [str(PER_PAGE)])[0])))
            q        = params.get("q",      [""])[0].strip()
            estado   = params.get("estado", [""])[0].strip()

            offset = (page - 1) * per_page
            sb     = get_sb()

            query = (sb.table(TABLA)
                       .select("codigo_externo,nombre,organismo,estado,"
                               "fecha_publicacion,palabras_clave,link,"
                               "fecha_registro,notificado",
                               count="exact")
                       .order("fecha_registro", desc=True)
                       .range(offset, offset + per_page - 1))

            if q:
                # Busca en nombre, organismo y descripcion
                query = query.or_(
                    f"nombre.ilike.*{q}*,"
                    f"organismo.ilike.*{q}*,"
                    f"descripcion.ilike.*{q}*"
                )
            if estado:
                query = query.ilike("estado", f"%{estado}%")

            result = query.execute()
            self._json(200, {
                "data":  result.data or [],
                "total": result.count or 0,
                "page":  page,
                "pages": max(1, -(-( result.count or 0) // per_page)),
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
