/**
 * settings.js — User Settings Page
 * ---------------------------------
 * Lets the user configure:
 *   - drname   : Doctor/business display name
 *   - msg      : Default message template (e.g. for appointment SMS)
 *   - pkey     : External API key (custom integrations)
 *   - code     : Activation / embed code (hidden by default)
 *   - send     : Toggle for auto-sending messages (checkbox cbx-3)
 *
 * Plan gating:
 *   - "sec" plan hides the code section entirely (#ccc element).
 *
 * Domain variants:
 *   - "lab" domain changes icons, titles, and links to lab-specific pages.
 *
 * Settings are stored in user.metadata.settings on the backend.
 * If no settings exist yet, defaults are created locally.
 */

const API_TIMEOUT_MS = 10_000;

// ---------------------------------------------
//  SAFE FETCH
// ---------------------------------------------
async function safe_fetch(url, opts = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  opts.signal = controller.signal;

  try {
    const res = await fetch(url, opts);
    clearTimeout(timeout);

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      const err = new Error(`HTTP ${res.status} ${res.statusText}`);
      err.status = res.status;
      err.body = text;
      throw err;
    }

    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  } catch (err) {
    clearTimeout(timeout);
    throw err;
  }
}

// POST helper that goes through safe_fetch (timeout included)
async function safePost(url, body) {
  return safe_fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------
//  AUTH / DOMAIN / PLAN
// ---------------------------------------------
async function get_user_id() {
  const data = await safe_fetch('/api/auth/me', { method: 'GET' });
  return data.data.id;
}

async function get_user(user_id, domain = '') {
  const data = await safe_fetch(`/api/binder/user?user_id=${user_id}&domain=${domain}`, { method: 'GET' });
  return data.data;
}

async function get_domain() {
  try {
    const data = await safe_fetch('/api/binder/get_domain', { method: 'GET' });
    if (data && (typeof data.data === 'string' || typeof data.domain === 'string')) {
      return data.data || data.domain;
    }
  } catch (err) {
    // FIX: was a silent empty catch — now logs so failures are visible during debugging
    console.error('get_domain failed:', err);
  }
  return null;
}

async function get_plan_status() {
  try {
    const data = await safe_fetch('/api/binder/get_plan_status', { method: 'GET' });
    if (!data) return null;
    const payload = data.data || data;
    return { days: Number(payload.days || 0), plan: payload.plan || null };
  } catch {
    return null;
  }
}

// ---------------------------------------------
//  USAGE TRACKER
// ---------------------------------------------
function startUsageTracker(endpoint) {
  let totalActiveSeconds = 0;
  let active = true;

  document.addEventListener('visibilitychange', () => { active = !document.hidden; });
  window.addEventListener('blur',  () => { active = false; });
  window.addEventListener('focus', () => { active = true; });

  setInterval(() => { if (active) totalActiveSeconds += 1; }, 1000);

  function sendFinal() {
    if (totalActiveSeconds <= 0) return;
    const blob = new Blob([JSON.stringify({ seconds: totalActiveSeconds })], { type: 'application/json' });
    navigator.sendBeacon(endpoint, blob);
  }

  window.addEventListener('beforeunload', sendFinal);
  return { getSeconds: () => totalActiveSeconds, flush: sendFinal };
}

// ---------------------------------------------
//  TOAST
// ---------------------------------------------
function showToast(text, ms = 1800) {
  const toast = document.getElementById('toast');
  toast.textContent = text;
  toast.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => toast.classList.remove('show'), ms);
}

// ---------------------------------------------
//  MODULE STATE
// ---------------------------------------------
let _user    = {};
let _user_id = '';
let _domain  = '';

// ---------------------------------------------
//  SAVE SETTINGS
//  FIX: was writing fields onto the root _user object.
//  Settings belong under _user.metadata.settings,
//  which is where the backend reads and stores them.
//  FIX: was using raw fetch with no timeout — now uses safePost.
// ---------------------------------------------
async function savePatientInfo() {
  if (!_user.metadata) _user.metadata = {};
  if (!_user.metadata.settings) _user.metadata.settings = {};

  _user.metadata.settings.drname = document.getElementById('drname').value;
  _user.metadata.settings.msg    = document.getElementById('msg').value;
  _user.metadata.settings.pkey   = document.getElementById('pkey').value;
  _user.metadata.settings.send   = document.getElementById('cbx-3').checked;

  // Only save the code field if the user has access to it
  const codeEl = document.getElementById('code');
  if (codeEl && codeEl.type !== 'hidden') {
    if (!_user.metadata.settings.ac) _user.metadata.settings.ac = {};
    _user.metadata.settings.ac.code = codeEl.value;
  }

  try {
    await safePost('/api/binder/user', { user_id: _user_id, user: _user });
    showToast('Settings saved');
  } catch (err) {
    console.error('savePatientInfo failed:', err);
    showToast('Save failed');
  }
}

// ---------------------------------------------
//  INIT
// ---------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  startUsageTracker('/api/binder/track_time');

  // Menu toggle
  const menuBtn = document.querySelector('.hamburger-menu');
  const menuBar = document.getElementById('menuBar');
  if (menuBtn && menuBar) {
    menuBtn.addEventListener('click', () => menuBar.classList.toggle('menu-active'));
  }

  // FIX: entire init is wrapped in try/catch so a single failed await
  // doesn't silently skip the rest of the page setup
  try {
    // FIX: get_plan_status can return null — was dereferenced without a null check before
    const planRes  = await get_plan_status();
    const plan     = planRes?.plan ?? 'free';

    _user_id = await get_user_id();
    _domain  = await get_domain() ?? '';
    _user    = await get_user(_user_id, _domain);

    // Plan gate — FIX: was wrapped in try/catch hiding a non-throwing call;
    // replaced with a simple null check
    if (plan === 'sec') {
      const ccc = document.getElementById('ccc');
      if (ccc) ccc.style.display = 'none';
    }

    // Load settings or build defaults
    let sett = (_user.metadata && _user.metadata.settings) || null;

    if (!sett) {
      sett = {
        send:  false,
        pkey:  '',
        drname: _user.name,
        msg:   '',
        ac:    { code: '/* no code yet */' },
      };
    }

    // Populate form — FIX: `!!sett.send ?? false` was redundant; `!!` already
    // produces a boolean so `?? false` could never fire. Simplified to `!!sett.send`
    document.getElementById('cbx-3').checked      = !!sett.send;
    document.getElementById('pkey').value         = sett.pkey   ?? '';
    document.getElementById('drname').value       = sett.drname ?? _user.name ?? '';
    document.getElementById('msg').value          = sett.msg    ?? '';

    if (plan !== 'sec') {
      document.getElementById('code').value = sett.ac?.code ?? '';
    } else {
      document.getElementById('code').value = 'This feature is not available on your plan.';
    }

    document.getElementById('codePreview').textContent = sett.ac?.code ?? '/* no code yet */';

    // --- Event listeners ---

    // Copy code to clipboard
    document.getElementById('copy-code').addEventListener('click', async (e) => {
      e.preventDefault();
      const code = document.getElementById('codePreview').textContent
                || document.getElementById('code').value;
      if (!code) { showToast('Nothing to copy'); return; }
      try {
        await navigator.clipboard.writeText(code);
        showToast('Code copied');
      } catch (err) {
        console.error(err);
        showToast('Copy failed');
      }
    });

    // Toggle code visibility
    let isVisible = false;
    document.getElementById('toggle-visibility').addEventListener('click', (e) => {
      e.preventDefault();
      isVisible = !isVisible;
      const codeInput = document.getElementById('code');
      codeInput.type = isVisible ? 'text' : 'password';
      const btn = e.currentTarget;
      btn.setAttribute('aria-pressed', String(isVisible));
      const span = btn.querySelector('span');
      if (span) span.textContent = isVisible ? 'Hide' : 'Show';
    });

    // Refresh code — FIX: was raw fetch with no timeout; now uses safePost
    document.getElementById('refresh-code').addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        const d = await safePost('/api/binder/code', {
          user_id: _user_id,
          domain:  _domain,
          code:    document.getElementById('code').value,
        });
        if (d?.data) {
          document.getElementById('code').value = d.data;
          document.getElementById('codePreview').textContent = d.data;
          showToast('Code refreshed');
        } else {
          showToast('No code returned');
        }
      } catch (err) {
        console.error(err);
        showToast('Refresh failed');
      }
    });

    // Dark mode toggle (syncs with sidebar)
    const settingsThemeToggle = document.getElementById('theme-toggle-settings');
    if (settingsThemeToggle) {
      const syncSettingsThemeToggle = () => {
        const isDark = document.body.classList.contains('theme-dark');
        settingsThemeToggle.checked = isDark;
        settingsThemeToggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
      };

      syncSettingsThemeToggle();

      settingsThemeToggle.addEventListener('change', (e) => {
        const wantsDark = !!e.currentTarget.checked;

        if (window.EntityManager && typeof window.EntityManager.setTheme === 'function') {
          window.EntityManager.setTheme(wantsDark ? 'dark' : 'light');
          syncSettingsThemeToggle();
          return;
        }

        if (window.EntityManager && typeof window.EntityManager.toggleTheme === 'function') {
          const isDark = document.body.classList.contains('theme-dark');
          if (isDark !== wantsDark) window.EntityManager.toggleTheme();
          syncSettingsThemeToggle();
          return;
        }

        // Fallback if shared manager is unavailable
        document.body.classList.toggle('theme-dark', wantsDark);
        localStorage.setItem('gradicent_theme', wantsDark ? 'dark' : 'light');
        syncSettingsThemeToggle();
      });
    }

    // "lab" domain variant — FIX: was wrapped in try/catch hiding null returns;
    // replaced with individual null checks on each element
    if (_domain === 'lab') {
      const appa   = document.getElementById('appa');
      const appimg = document.getElementById('appimg');
      const apph6  = document.getElementById('apph6');
      const link   = document.querySelector("link[rel~='icon']");
      const namee  = document.getElementById('namee');

      if (appa)   { appa.title = 'Binder Lab'; appa.href = '/srchlab'; }
      if (appimg)   appimg.src = '/static/images/srchlab.png';
      if (apph6)    apph6.textContent = 'Binder Lab';
      if (link)     link.href = '/static/images/binderlab.jpg';
      if (namee)    namee.textContent = 'Lab name:';
      document.title = 'Binder Laboratory';
    }

  } catch (err) {
    console.error('settings.js init failed:', err);
    showToast('Failed to load settings. Please refresh.', 4000);
  }
});