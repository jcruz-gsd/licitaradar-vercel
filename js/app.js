/* =================================================
   LicitaRadar — app.js
   Auth helpers + API wrapper + UI utilities
   ================================================= */

const SESSION_KEY = 'lr_session';

// ── Session ──────────────────────────────────────
function getSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    if (Date.now() > s.expires) { sessionStorage.removeItem(SESSION_KEY); return null; }
    return s;
  } catch { return null; }
}

function requireAuth() {
  const s = getSession();
  if (!s) { window.location.href = '/index.html'; return null; }
  return s;
}

function setSession(user) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({
    user,
    expires: Date.now() + 8 * 3600 * 1000
  }));
}

function logout() {
  sessionStorage.removeItem(SESSION_KEY);
  window.location.href = '/index.html';
}

// ── API calls ────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

const api = {
  login:        body  => apiFetch('/api/login',        { method:'POST', body: JSON.stringify(body) }),
  stats:        ()    => apiFetch('/api/stats'),
  licitaciones: params => apiFetch('/api/licitaciones?' + new URLSearchParams(params)),
  categorias:   ()    => apiFetch('/api/categorias'),
  scan:         ()    => apiFetch('/api/scan',         { method:'POST', body: '{}' }),
};

// ── Sidebar + nav ────────────────────────────────
function initSidebar(activePage) {
  const s = requireAuth();
  if (!s) return;

  // User info
  const emailEl = document.getElementById('user-email');
  const avatarEl = document.getElementById('user-avatar');
  if (emailEl) emailEl.textContent = s.user;
  if (avatarEl) avatarEl.textContent = s.user.charAt(0).toUpperCase();

  // Active nav
  document.querySelectorAll('.nav-link[data-page]').forEach(el => {
    el.classList.toggle('active', el.dataset.page === activePage);
  });

  // Logout btn
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) logoutBtn.addEventListener('click', logout);

  // Scan btn
  const scanBtn = document.getElementById('btn-scan-sidebar');
  if (scanBtn) scanBtn.addEventListener('click', () => triggerScan(scanBtn));
}

// ── Scan ─────────────────────────────────────────
async function triggerScan(btn) {
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Escaneando…'; }
  const alertEl = document.getElementById('scan-alert');
  if (alertEl) { alertEl.style.display = 'none'; }
  try {
    const r = await api.scan();
    if (alertEl) {
      const ico = r.new > 0
        ? '<svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
        : '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
      alertEl.className = 'alert ' + (r.new > 0 ? 'alert-ok' : 'alert-info');
      alertEl.innerHTML = ico + `<div><strong>${r.new > 0 ? `${r.new} licitación(es) nueva(s) encontrada(s)` : 'Sin licitaciones nuevas'}</strong>
        · Revisadas ${r.total || 0} · Relevantes ${r.filtered || 0} · ${r.ok ? 'Correo enviado ✓' : 'Sin correo'}</div>`;
      alertEl.style.display = 'flex';
    }
    if (typeof onScanComplete === 'function') onScanComplete(r);
  } catch (e) {
    if (alertEl) {
      alertEl.className = 'alert alert-err';
      alertEl.innerHTML = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
        + `<div><strong>Error al escanear:</strong> ${e.message}</div>`;
      alertEl.style.display = 'flex';
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Escanear ahora';
    }
  }
}

// ── Helpers ──────────────────────────────────────
function fmtDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('es-CL', { day:'2-digit', month:'2-digit', year:'numeric' });
  } catch { return iso; }
}

function fmtNum(n) { return (n || 0).toLocaleString('es-CL'); }

function badgeHtml(estado) {
  const e = (estado || '').toUpperCase();
  if (e.includes('PUBLI')) return '<span class="badge badge-pub">Publicada</span>';
  if (e.includes('CERR'))  return '<span class="badge badge-cer">Cerrada</span>';
  if (e.includes('EVAL'))  return '<span class="badge badge-eval">Evaluación</span>';
  if (e.includes('ADJUD')) return '<span class="badge badge-adj">Adjudicada</span>';
  return `<span class="badge badge-def">${estado || '—'}</span>`;
}

function kwList(arr) {
  if (!arr) return '—';
  const list = Array.isArray(arr) ? arr : (arr || '').split(',');
  return list.filter(Boolean).map(k => k.trim()).slice(0,3).join(', ') || '—';
}

// Topbar last-updated
function setLastUpdated() {
  const el = document.getElementById('last-updated');
  if (el) {
    el.textContent = 'Última actualización: ' +
      new Date().toLocaleTimeString('es-CL', { hour:'2-digit', minute:'2-digit' });
  }
}

// Sidebar HTLM template (injected into pages)
function sidebarHTML() {
  return `
<aside class="sidebar">
  <div class="sidebar-brand">
    <div class="brand-icon">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    </div>
    <div>
      <div class="brand-name">LicitaRadar</div>
      <div class="brand-sub">by Global Solution Digital</div>
    </div>
  </div>

  <nav class="nav-section">
    <div class="nav-label">Menú</div>
    <a class="nav-link" data-page="dashboard" href="/dashboard.html">
      <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
      Dashboard
    </a>
    <a class="nav-link" data-page="historial" href="/historial.html">
      <svg viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
      Historial
    </a>
    <a class="nav-link" data-page="buscador" href="/buscador.html">
      <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      Buscador
    </a>
    <a class="nav-link" data-page="categorias" href="/categorias.html">
      <svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
      Categorías
    </a>
  </nav>

  <div class="sidebar-bottom">
    <div class="status-row">
      <span class="status-dot"></span>
      Sistema activo
    </div>
    <button class="btn-scan" id="btn-scan-sidebar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
      Escanear ahora
    </button>
    <div class="sidebar-user">
      <div class="user-avatar" id="user-avatar">U</div>
      <div class="user-email" id="user-email">cargando…</div>
      <button class="btn-logout" id="btn-logout" title="Cerrar sesión">↩</button>
    </div>
  </div>
</aside>`;
}

function topbarHTML() {
  return `
<header class="topbar">
  <span class="pill pill-ok"><span class="pill-dot"></span>API Mercado Público</span>
  <span class="pill pill-ok"><span class="pill-dot"></span>BD Supabase</span>
  <span class="topbar-right" style="display:flex;align-items:center;gap:14px;">
    <span id="last-updated" style="color:#94A3B8;font-size:12px;">—</span>
    <button onclick="logout()" style="display:flex;align-items:center;gap:6px;background:transparent;border:1.5px solid #E2E8F0;border-radius:7px;padding:5px 12px;font-size:12px;font-weight:600;color:#64748B;cursor:pointer;font-family:inherit;transition:all .15s;" onmouseover="this.style.borderColor='#0F1B35';this.style.color='#0F1B35'" onmouseout="this.style.borderColor='#E2E8F0';this.style.color='#64748B'">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      Cerrar sesión
    </button>
  </span>
</header>`;
}
