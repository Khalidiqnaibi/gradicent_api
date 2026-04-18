/**
 * home.js — Client Registration Page
 * -----------------------------------
 * Lets the user add a new client (patient or business contact).
 *
 * Key conventions:
 *   - FIELD_MAP maps HTML element IDs → backend field names per domain.
 *     The same HTML IDs are reused across domains but map to different keys
 *     (e.g. "medh" → "pmh" in medical, "company" in business).
 *   - After adding a client, redirects to /data/-1 where -1 means
 *     "the most recently created client" (resolved server-side).
 *   - "sec" plan = security/restricted plan that limits navigation.
 */

const API_TIMEOUT_MS = 10_000;

let GLOBAL_USER_ID = null;
let GLOBAL_DOMAIN  = null;
let GLOBAL_PLAN    = null;

function el(id) { return document.getElementById(id); }

function show_toast(message, type = 'info') {
  const container = el('toasts');
  const t = document.createElement('div');
  t.className = 'toast-item';
  t.style.padding = '10px 12px';
  t.style.borderRadius = '10px';
  t.style.fontWeight = 700;
  t.textContent = message;
  if (type === 'error')        { t.style.background = '#fee2e2'; t.style.color = '#991b1b'; t.style.borderLeft = '6px solid #ef4444'; }
  else if (type === 'success') { t.style.background = '#dcfce7'; t.style.color = '#065f46'; t.style.borderLeft = '6px solid #10b981'; }
  else                         { t.style.background = '#dbeafe'; t.style.color = '#1e3a8a'; t.style.borderLeft = '6px solid #3b82f6'; }
  container.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

document.addEventListener("DOMContentLoaded", async () => {
  startUsageTracker("/api/binder/track_time");

  try {
    menu_init();
    GLOBAL_USER_ID = await get_user_id();
    GLOBAL_DOMAIN  = await get_domain();
    const res = await get_plan_status();
    GLOBAL_PLAN = res?.plan ?? null;
  } catch (err) {
    console.error(`Failed to load domain/user: ${err}`);
    show_toast("Failed to load domain/user", "error");
  }
});

// ---------------------------------------------
//  MENU
// ---------------------------------------------
function menu_init() {
  const menuBtn = document.querySelector('.hamburger-menu');
  const menuBar = document.getElementById('menuBar');
  if (!menuBtn || !menuBar) return;

  menuBtn.addEventListener('click', () => {
    menuBar.classList.toggle('menu-active');
  });

  const menu_box = document.querySelector(".menu__box");
  document.addEventListener('click', (ev) => {
    if (
      !menuBar.contains(ev.target) &&
      !menuBtn.contains(ev.target) &&
      menuBar.classList.contains('menu-active')
    ) {
      menuBar.classList.remove('menu-active');
      menuBtn.setAttribute('aria-expanded', 'false');
      if (menu_box) menu_box.setAttribute('aria-hidden', 'true');
    }
  });
}

// ---------------------------------------------
//  SAFE FETCH (single unified wrapper)
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
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------
//  AUTH / DOMAIN / PLAN
// ---------------------------------------------
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

async function get_domain() {
  try {
    const data = await safe_fetch('/api/binder/get_domain', { method: 'GET' });
    if (data && (typeof data.data === 'string' || typeof data.domain === 'string')) {
      return data.data || data.domain;
    }
  } catch (err) {
    show_toast("Failed to load domain", "error");
    console.error(err);
  }
  return null;
}

async function get_user() {
  const data = await safe_fetch('/api/auth/me', { method: 'GET' });
  return data.data;
}

async function get_user_id() {
  const user = await get_user();
  return user.id;
}

// ---------------------------------------------
//  USAGE TRACKER
// ---------------------------------------------
function startUsageTracker(endpoint) {
  let active = true;
  let seconds = 0;

  document.addEventListener("visibilitychange", () => { active = !document.hidden; });
  window.addEventListener("focus", () => active = true);
  window.addEventListener("blur",  () => active = false);

  setInterval(() => { if (active) seconds++; }, 1000);

  window.addEventListener("beforeunload", () => {
    if (seconds > 0) {
      const blob = new Blob([JSON.stringify({ seconds })], { type: 'application/json' });
      navigator.sendBeacon(endpoint, blob);
    }
  });
}

// ---------------------------------------------
//  FIELD_MAP
//  Maps HTML element IDs → backend field names.
//  Both domains share the same HTML form; only
//  the backend key names differ per domain.
// ---------------------------------------------
const FIELD_MAP = {
  medical: {
    PName:     "name",
    idnum:     "gov_id",
    PNum:      "phone",
    loc:       "location",
    medh:      "pmh",
    allergies: "allergies",
    btype:     "btype",
    sex:       "sex",
    age:       "age",
  },
  business: {
    PName:     "name",
    idnum:     "gov_id",
    PNum:      "phone",
    loc:       "location",
    medh:      "company",
    allergies: "industry",
    btype:     "email",
    sex:       "account_manager",
    age:       "company_size",
  },
};

// ---------------------------------------------
//  BUILD CLIENT OBJECT
// ---------------------------------------------
function buildClientObject() {
  // No fallback here — if domain is null, submitClient will catch it
  const map = FIELD_MAP[GLOBAL_DOMAIN];
  if (!map) return null;

  const client = { debit: 0, payed: 0, interactions: [] };

  for (const [htmlId, key] of Object.entries(map)) {
    const field = document.getElementById(htmlId);
    if (field) client[key] = field.value.trim();
  }

  return client;
}

// ---------------------------------------------
//  RESET FORM
//  Derived from FIELD_MAP — stays in sync automatically
// ---------------------------------------------
function resetForm() {
  const map = FIELD_MAP[GLOBAL_DOMAIN];
  if (!map) return;
  for (const htmlId of Object.keys(map)) {
    const field = document.getElementById(htmlId);
    if (field) field.value = '';
  }
}

// ---------------------------------------------
//  SUBMIT
// ---------------------------------------------
async function submitClient() {
  if (!GLOBAL_USER_ID || !GLOBAL_DOMAIN) {
    show_toast("Unable to get user or domain. Please refresh the page.", "error");
    return;
  }

  const client = buildClientObject();

  if (!client) {
    show_toast("Unknown domain. Please refresh the page.", "error");
    return;
  }

  if (!client.name) {
    show_toast("Please enter the client name.", "info");
    return;
  }

  // FIX: was `client.age === 0` which never matched a blank string.
  // `!client.age` correctly catches empty strings, null, and "0".
  if (GLOBAL_DOMAIN === "medical" && !client.age) {
    show_toast("Please enter the patient age.", "info");
    return;
  }

  try {
    const payload = { domain: GLOBAL_DOMAIN, user_id: GLOBAL_USER_ID, client };
    await safePost("/api/binder/clients", payload);

    show_toast("Client added successfully!", "success");
    resetForm(); // FIX: was 9 hardcoded lines; now uses FIELD_MAP as single source of truth

    if (GLOBAL_PLAN !== "sec") {
      window.location.href = `/data/-1`;
    } else {
      show_toast("Not implemented yet!", "info");
    }
  } catch (err) {
    show_toast("Error adding client.", "error");
    console.error(`Error adding client: ${err}`);
  }
}