/* ============================================================
   Helpers
============================================================ */
const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/* ============================================================
   Usage Tracker (unchanged – already business-safe)
============================================================ */
function startUsageTracker(endpoint) {
  let totalActiveSeconds = 0;
  let active = true;

  document.addEventListener("visibilitychange", () => {
    active = !document.hidden;
  });
  window.addEventListener("blur", () => active = false);
  window.addEventListener("focus", () => active = true);

  setInterval(() => { if (active) totalActiveSeconds++; }, 1000);

  function sendFinal() {
    if (totalActiveSeconds <= 0) return;
    navigator.sendBeacon(endpoint, JSON.stringify({ seconds: totalActiveSeconds }));
  }

  window.addEventListener("beforeunload", sendFinal);

  return {
    getSeconds: () => totalActiveSeconds,
    flush: sendFinal
  };
}

/* ============================================================
   Toasts
============================================================ */
function showToast(text, type = 'info') {
  const c = document.getElementById('toastContainer');
  if (!c) return;

  const el = document.createElement('div');
  el.className = `item ${type}`;
  el.textContent = text;
  c.appendChild(el);

  setTimeout(() => {
    el.classList.add('hide');
    setTimeout(() => el.remove(), 400);
  }, 3000);
}

/* ============================================================
   Domain Adapter (MOST IMPORTANT PART)
============================================================ */
const DOMAIN_CONFIG = {
  medical: {
    label: 'Visit',
    fields: {
      date: 'visit_date',
      owner: 'drname',
      title: 'diagnosis',
      service: 'treatment',
      notes: 'details',
      cost: 'coast',
      paid: 'payed',
      debt: 'debit'
    },
    defaultFolder: 'drs',
    lockOnPrint: true
  },

  business: {
    label: 'Transaction',
    fields: {
      date: 'date',
      owner: 'handled_by',
      title: 'service_name',
      service: 'description',
      notes: 'notes',
      cost: 'amount',
      paid: 'paid',
      debt: 'balance'
    },
    defaultFolder: 'invoices',
    lockOnPrint: true
  }
};

let domain = 'medical';
const cfg = () => DOMAIN_CONFIG[domain] || DOMAIN_CONFIG.medical;

/* ============================================================
   Global State
============================================================ */
const API_TIMEOUT_MS = 10_000;

let user_id = "";
let plan = "free";
let visits = [];
let currentVisitIndex = 0;
let patientNumber = '{{client}}';
let selectedFolder = 'drs';

/* ============================================================
   Fetch helpers
============================================================ */
async function safe_fetch(url, opts = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  opts.signal = controller.signal;

  try {
    const res = await fetch(url, opts);
    clearTimeout(timeout);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ct = res.headers.get('content-type') || '';
    return ct.includes('json') ? res.json() : res.text();
  } catch (e) {
    clearTimeout(timeout);
    throw e;
  }
}

/* ============================================================
   User / Domain
============================================================ */
async function get_user() {
  const r = await safe_fetch('/api/auth/me');
  return r.data;
}
async function get_domain() {
  try {
    const r = await safe_fetch('/api/binder/get_domain');
    return r.data || r.domain || 'medical';
  } catch { return 'medical'; }
}
async function get_plan_status() {
  try {
    const r = await safe_fetch('/api/binder/get_plan_status');
    return r.data || r;
  } catch { return { plan:'free' }; }
}

/* ============================================================
   Normalize Interaction
============================================================ */
function normalizeInteraction(raw = {}) {
  const f = cfg().fields;
  return {
    date: raw[f.date] || '',
    owner: raw[f.owner] || '',
    title: raw[f.title] || '',
    service: raw[f.service] || '',
    notes: raw[f.notes] || '',
    cost: Number(raw[f.cost] || 0),
    paid: Number(raw[f.paid] || 0),
    debt: Number(raw[f.debt] || 0),
    printed: !!raw.printed,
    vno: raw.vno || 1
  };
}

/* ============================================================
   DOM Ready
============================================================ */
document.addEventListener('DOMContentLoaded', async () => {
  domain = await get_domain();
  const user = await get_user();
  user_id = user.id;

  const p = await get_plan_status();
  plan = p.plan || 'free';

  startUsageTracker('/api/binder/track_time');

  $('#searchButton')?.addEventListener('click', search);
  $('#prevButton')?.addEventListener('click', prev);
  $('#nextButton')?.addEventListener('click', next);
  $('#firstButton')?.addEventListener('click', first);
  $('#lastButton')?.addEventListener('click', last);
  $('#saveBtn')?.addEventListener('click', save);
  $('#printBtn')?.addEventListener('click', () => { save(); printInteraction(); });

  fetchClientData();
});

/* ============================================================
   Fetch Client
============================================================ */
function fetchClientData() {
  fetch(`/api/binder/clients/${patientNumber}?domain=${domain}&user_id=${user_id}`)
    .then(r => r.json())
    .then(r => {
      visits = r.data.interactions || [];
      if (!Array.isArray(visits)) visits = [visits];
      currentVisitIndex = visits.length ? visits.length - 1 : 0;
      populate(visits[currentVisitIndex] || {});
      showToast(`${cfg().label} loaded`, 'success');
    })
    .catch(() => showToast('Failed to load data','error'));
}

/* ============================================================
   Populate
============================================================ */
function populate(raw) {
  const v = normalizeInteraction(raw);

  $('#visitDate').value = v.date;
  $('#drname').value = v.owner;
  $('#diagnosis').value = v.title;
  $('#treatment').value = v.service;
  $('#details').value = v.notes;
  $('#coast').value = v.cost;
  $('#payed').value = v.paid;
  $('#debt').value = v.debt;

  const locked = v.printed && cfg().lockOnPrint;
  $$('#visitForm input, #visitForm textarea').forEach(e => e.disabled = locked);
}

/* ============================================================
   Navigation
============================================================ */
function first(){ if(visits.length){ currentVisitIndex=0; populate(visits[0]); } }
function last(){ if(visits.length){ currentVisitIndex=visits.length-1; populate(visits[currentVisitIndex]); } }
function prev(){ if(currentVisitIndex>0){ currentVisitIndex--; populate(visits[currentVisitIndex]); } }
function next(){
  const n = visits[currentVisitIndex+1];
  if (n) { currentVisitIndex++; populate(n); }
  else {
    const empty = {};
    visits.push(empty);
    currentVisitIndex = visits.length - 1;
    populate(empty);
  }
}

/* ============================================================
   Search
============================================================ */
function search() {
  const d = $('#search').value;
  const f = cfg().fields.date;
  const found = visits.find(v => v[f] === d);
  if (!found) return showToast('Not found','info');
  currentVisitIndex = visits.indexOf(found);
  populate(found);
}

/* ============================================================
   Save
============================================================ */
function buildPayload() {
  const f = cfg().fields;
  const data = {
    [f.date]: $('#visitDate').value.trim(),
    [f.owner]: $('#drname').value.trim(),
    [f.title]: $('#diagnosis').value.trim(),
    [f.service]: $('#treatment').value.trim(),
    [f.notes]: $('#details').value.trim(),
    [f.cost]: Number($('#coast').value || 0),
    [f.paid]: Number($('#payed').value || 0),
    vno: visits[currentVisitIndex]?.vno || currentVisitIndex + 1
  };
  data[f.debt] = data[f.cost] - data[f.paid];
  $('#debt').value = data[f.debt];
  return data;
}

function save() {
  const payload = buildPayload();
  if (!payload[cfg().fields.date]) {
    showToast('Date required','error');
    return;
  }

  const isNew = !visits[currentVisitIndex]?.vno;
  const method = isNew ? 'POST' : 'PATCH';

  fetch(`/api/binder/clients/${patientNumber}/interactions`,{
    method,
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      user_id,
      domain,
      interaction: payload,
      interaction_no: currentVisitIndex+1,
      patch: payload
    })
  })
  .then(()=>{ showToast('Saved','success'); fetchClientData(); })
  .catch(()=> showToast('Save failed','error'));
}

/* ============================================================
   Print (Invoice / Visit)
============================================================ */
function printInteraction() {
  if (!confirm(`Lock this ${cfg().label}?`)) return;

  fetch('/kkprint',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ vno: currentVisitIndex })
  })
  .then(r=>r.blob())
  .then(b=>{
    const u=URL.createObjectURL(b);
    const a=document.createElement('a');
    a.href=u; a.download=`${cfg().label}.docx`;
    a.click(); URL.revokeObjectURL(u);
    fetchClientData();
  });
}
