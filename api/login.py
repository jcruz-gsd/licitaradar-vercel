"""POST /api/login — valida credenciales.
   Primero verifica variables de entorno (admin master),
   luego busca en la tabla app_users de Supabase."""
import json, os, hashlib
from http.server import BaseHTTPRequestHandler

def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length) or "{}")
            email  = (body.get("email")    or "").strip().lower()
            pwd    = (body.get("password") or "").strip()

            # 1. Verificar credenciales master (env vars)
            env_email = (os.environ.get("APP_EMAIL")    or "").strip().lower()
            env_pwd   = (os.environ.get("APP_PASSWORD") or "").strip()
            if email == env_email and pwd == env_pwd:
                return self._json(200, {"ok": True, "user": email, "rol": "admin"})

            # 2. Verificar en tabla app_users de Supabase
            try:
                from supabase import create_client
                sb  = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
                row = (sb.table("app_users")
                         .select("email,nombre,rol,activo")
                         .eq("email", email)
                         .eq("password", hash_pwd(pwd))
                         .eq("activo", True)
                         .execute().data)
                if row:
                    u = row[0]
                    return self._json(200, {
                        "ok":     True,
                        "user":   u["email"],
                        "nombre": u.get("nombre", ""),
                        "rol":    u.get("rol", "usuario"),
                    })
            except Exception:
                pass  # Si falla Supabase, solo aplica el login master

            self._json(401, {"ok": False, "error": "Correo o contraseña incorrectos."})

        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors(); self.end_headers(); self.wfile.write(body)

    def log_message(self, *_): pass
