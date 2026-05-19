"""POST /api/scan — ejecuta escaneo completo: fetch → filtrar → guardar → email."""
import json, os, smtplib, logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler

import requests
from supabase import create_client


log   = logging.getLogger(__name__)
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

# Términos que DESCARTAN una licitación aunque haya match de keyword
EXCLUSION_KEYWORDS = [
    "inmueble", "edificio", "remodelación", "ampliación", "construcción",
    "ascensor", "caldera", "gasfitería", "gasfiter", "plomería",
    "sanitario", "cañería", "pintura", "techumb", "paviment",
    "jardinería", "aseo", "limpieza", "fumigación",
    "vehículo", "ambulancia", "camión", "furgón", "bus",
    "alimento", "alimentación", "colación", "catering",
    "dental", "odontológico", "médico", "clínico", "fármaco",
    "vestuario", "uniforme", "calzado", "textil",
    "mueble", "mobiliario", "silla", "escritorio de oficina",
    "arriendo de inmueble", "comodato de inmueble",
]

ALL_KEYWORDS = [kw for kws in CATEGORIAS.values() for kw in kws]


def get_keywords_config(cfg):
    """Lee categorías y exclusiones desde app_config.
    Si no hay config guardada, usa los valores hardcodeados como fallback."""
    categorias  = CATEGORIAS
    exclusiones = EXCLUSION_KEYWORDS
    if cfg.get("keywords_json"):
        try:
            categorias = json.loads(cfg["keywords_json"])
        except Exception:
            pass
    if cfg.get("exclusion_keywords"):
        exclusiones = [k.strip() for k in cfg["exclusion_keywords"].split(",") if k.strip()]
    return categorias, exclusiones


def get_sb():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def fetch_lics(fecha):
    ticket = os.environ.get("MERCADO_PUBLICO_TICKET", "")
    url    = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
    try:
        r = requests.get(url, params={"fecha": fecha, "ticket": ticket}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("Listado") or []
    except Exception as e:
        log.error("fetch_lics: %s", e)
        return []


def do_filter(licitaciones, categorias=None, exclusiones=None):
    if categorias is None:
        categorias = CATEGORIAS
    if exclusiones is None:
        exclusiones = EXCLUSION_KEYWORDS
    all_kws = [kw for kws in categorias.values() for kw in kws]
    out = []
    for l in licitaciones:
        nombre = str(l.get("Nombre", "")).lower()
        desc   = str(l.get("Descripcion", "")).lower()
        text   = nombre + " " + desc

        # 1. Verificar que tenga al menos un keyword relevante
        matched = [kw for kw in all_kws if kw in text]
        if not matched:
            continue

        # 2. Descartar si contiene palabras de exclusión
        if any(ex in text for ex in exclusiones):
            log.info("Descartada por exclusión: %s", l.get("Nombre", ""))
            continue

        l["_kw"] = matched
        for cat, kws in categorias.items():
            if any(k in matched for k in kws):
                l["_cat"] = cat
                break
        else:
            l["_cat"] = "General"
        out.append(l)
    return out


def save_new(filtered, sb):
    nuevas = []
    for l in filtered:
        cod = l.get("CodigoExterno", "")
        if not cod:
            continue
        try:
            exists = sb.table(TABLA).select("id").eq("codigo_externo", cod).execute().data
            if exists:
                continue
        except Exception as e:
            log.error(e)
            continue
        rec = {
            "codigo_externo":    cod,
            "nombre":            l.get("Nombre", "Sin nombre"),
            "descripcion":       l.get("Descripcion", ""),
            "estado":            l.get("Estado", ""),
            "fecha_publicacion": l.get("FechaCierre", ""),
            "organismo":         l.get("NombreOrganismo", l.get("Nombre", "")),
            "monto_estimado":    None,
            "link":              f"https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={cod}",
            "palabras_clave":    l.get("_kw", []),
            "notificado":        False,
        }
        try:
            sb.table(TABLA).insert(rec).execute()
            rec["_cat"] = l.get("_cat", "General")
            nuevas.append(rec)
        except Exception as e:
            log.error(e)
    return nuevas


def get_config(sb):
    """Lee configuración desde app_config, con fallback a env vars."""
    try:
        rows = sb.table("app_config").select("key,value").execute().data or []
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}

def send_email(nuevas, fecha, cfg=None):
    e_from = os.environ.get("EMAIL_SENDER", "")
    e_pass = os.environ.get("EMAIL_PASSWORD", "")
    # Destinatarios: desde config DB o env var
    if cfg and cfg.get("email_receivers"):
        e_to = cfg["email_receivers"]
    else:
        e_to = os.environ.get("EMAIL_RECEIVER", "")
    # Asunto personalizable
    subject_prefix = (cfg or {}).get("email_subject_prefix", "LicitaRadar")
    if not all([e_from, e_pass, e_to]):
        return False

    rows = "".join(f"""
    <tr>
      <td style="padding:10px 16px;border-bottom:1px solid #F1F5F9;font-size:13px;color:#374151;">{l.get('organismo','—')}</td>
      <td style="padding:10px 16px;border-bottom:1px solid #F1F5F9;">
        <a href="{l.get('link','#')}" style="font-size:13px;font-weight:600;color:#162047;text-decoration:none;">{l.get('nombre','')}</a>
      </td>
      <td style="padding:10px 16px;border-bottom:1px solid #F1F5F9;font-size:12px;color:#64748B;">{', '.join(l.get('palabras_clave',[]))}</td>
    </tr>""" for l in nuevas)

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"></head>
<body style="background:#F1F5F9;font-family:'Segoe UI',Arial,sans-serif;padding:32px 20px;">
<div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,.08);">
  <div style="background:#162047;padding:28px 32px;">
    <div style="font-size:11px;font-weight:700;color:#00C4D4;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">LICITARADAR · GLOBAL SOLUTION DIGITAL SPA</div>
    <div style="font-size:20px;font-weight:700;color:#fff;">{len(nuevas)} nueva(s) licitación(es) detectada(s)</div>
    <div style="font-size:13px;color:rgba(255,255,255,.5);margin-top:4px;">{fecha}</div>
  </div>
  <div style="padding:28px 32px 8px;">
    <table style="width:100%;border-collapse:collapse;">
      <thead><tr style="border-bottom:2px solid #E2E8F0;">
        <th style="padding:8px 16px;font-size:11px;font-weight:600;color:#94A3B8;text-align:left;text-transform:uppercase;letter-spacing:.5px;">Organismo</th>
        <th style="padding:8px 16px;font-size:11px;font-weight:600;color:#94A3B8;text-align:left;text-transform:uppercase;letter-spacing:.5px;">Licitación</th>
        <th style="padding:8px 16px;font-size:11px;font-weight:600;color:#94A3B8;text-align:left;text-transform:uppercase;letter-spacing:.5px;">Palabras clave</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div style="padding:20px 32px;border-top:1px solid #F1F5F9;margin-top:12px;">
    <p style="font-size:12px;color:#94A3B8;margin:0;">Mensaje automático generado por LicitaRadar. No respondas a este correo.</p>
  </div>
</div></body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{subject_prefix} — {len(nuevas)} licitación(es) nueva(s) · {fecha}"
    msg["From"]    = e_from
    msg["To"]      = e_to
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.ehlo(); s.starttls()
            s.login(e_from, e_pass)
            s.send_message(msg)
        return True
    except Exception as e:
        log.error("email: %s", e)
        return False


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            sb   = get_sb()
            cfg  = get_config(sb)
            hoy  = datetime.now().strftime("%d%m%Y")
            leg  = datetime.now().strftime("%d/%m/%Y %H:%M")
            all_ = fetch_lics(hoy)
            cats, excl = get_keywords_config(cfg)
            fil  = do_filter(all_, cats, excl)
            new  = save_new(fil, sb)
            ok   = False
            if new:
                ok = send_email(new, leg, cfg)
                if ok:
                    codigos = [n["codigo_externo"] for n in new]
                    for c in codigos:
                        try:
                            sb.table(TABLA).update({"notificado": True}).eq("codigo_externo", c).execute()
                        except Exception:
                            pass
            self._json(200, {
                "ok":       ok,
                "total":    len(all_),
                "filtered": len(fil),
                "new":      len(new),
            })
        except Exception as e:
            self._json(500, {"error": str(e)})

    # ── helpers ──────────────────────────────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
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
