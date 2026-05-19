"""GET  /api/users         — listar usuarios
   POST /api/users         — crear usuario  {email, password, nombre, rol}
   POST /api/users?del=1   — desactivar     {email}
   POST /api/users?pwd=1   — cambiar clave  {email, password}"""
import json, os, hashlib
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from supabase import create_client

TABLA = "app_users"

def get_sb():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        try:
            sb   = get_sb()
            rows = (sb.table(TABLA)
                      .select("id,email,nombre,rol,activo,created_at")
                      .order("created_at", desc=False)
                      .execute().data or [])
            self._json(200, {"users": rows})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_POST(self):
        try:
            params = parse_qs(urlparse(self.path).query)
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length) or "{}")
            sb     = get_sb()

            # Desactivar usuario
            if "del" in params:
                email = body.get("email", "").strip().lower()
                sb.table(TABLA).update({"activo": False}).eq("email", email).execute()
                return self._json(200, {"ok": True})

            # Cambiar contraseña
            if "pwd" in params:
                email = body.get("email", "").strip().lower()
                pwd   = body.get("password", "").strip()
                if not pwd or len(pwd) < 6:
                    return self._json(400, {"error": "La contraseña debe tener al menos 6 caracteres."})
                sb.table(TABLA).update({"password": hash_pwd(pwd)}).eq("email", email).execute()
                return self._json(200, {"ok": True})

            # Crear usuario
            email  = body.get("email",    "").strip().lower()
            pwd    = body.get("password", "").strip()
            nombre = body.get("nombre",   "").strip()
            rol    = body.get("rol",      "usuario").strip()

            if not email or not pwd:
                return self._json(400, {"error": "Email y contraseña son obligatorios."})
            if len(pwd) < 6:
                return self._json(400, {"error": "La contraseña debe tener al menos 6 caracteres."})

            exists = sb.table(TABLA).select("id").eq("email", email).execute().data
            if exists:
                return self._json(409, {"error": "Ya existe un usuario con ese correo."})

            sb.table(TABLA).insert({
                "email":    email,
                "password": hash_pwd(pwd),
                "nombre":   nombre,
                "rol":      rol,
                "activo":   True,
            }).execute()
            self._json(201, {"ok": True})

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
