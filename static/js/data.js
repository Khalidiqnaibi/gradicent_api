/**
 * data.js — Client/Patient Interaction Page
 * ------------------------------------------
 * Handles viewing, creating, editing, and printing interactions
 * ("visits" in medical, "transactions" in business).
 *
 * Architecture:
 *   DOMAIN_CONFIG maps each domain → { dom selectors, backend field names }
 *   normalize()    converts raw API data  → generic internal shape
 *   populate()     writes internal shape   → DOM form inputs
 *   buildPayload() reads DOM form inputs   → API payload
 *
 * Key conventions:
 *   - "vno" = visit/interaction number (1-based)
 *   - "detail1/2/3" = domain-specific extra fields
 *       medical:  detail1=weight, detail2=height, detail3=lab
 *       business: detail1=outcome, detail2=next follow-up (no detail3)
 *   - Backend field names like "coast", "payed", "debit" are intentional —
 *     they match the database schema and must NOT be renamed here.
 *   - Plan gating: file features (upload/view/delete) require "pro" or "ultra".
 *   - patientNumber comes from the URL via window.__client__.
 *     Value -1 means "newly created client" (redirected after adding).
 */

/* ============================================================
   Helpers
============================================================ */
const $  = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const LAST_PAGE_KEY = 'gradicent_last_page';

function getCurrentPagePath() {
  return `${window.location.pathname}${window.location.search}`;
}

function isSafeInternalPath(path) {
  return typeof path === 'string' && path.startsWith('/') && !path.startsWith('//');
}

function resolveLastPagePath() {
  const currentPath = getCurrentPagePath();

  try {
    const stored = sessionStorage.getItem(LAST_PAGE_KEY);
    if (isSafeInternalPath(stored) && stored !== currentPath) return stored;
  } catch (_) {
    // Storage can fail in restricted browser contexts.
  }

  try {
    if (document.referrer) {
      const ref = new URL(document.referrer);
      if (ref.origin === window.location.origin) {
        const refPath = `${ref.pathname}${ref.search}`;
        if (isSafeInternalPath(refPath) && refPath !== currentPath) return refPath;
      }
    }
  } catch (_) {
    // Ignore malformed referrer.
  }

  return null;
}

/* ============================================================
   Domain Configuration
   --------------------
   Each domain defines:
     label       – UI display name ("Visit" / "Transaction")
     formId      – CSS selector of the HTML <form>
     dom         – CSS selectors for each form input (keyed generically)
     fields      – backend/database field names (keyed generically)
     lockOnPrint – if true, disable form inputs after printing

   The generic keys (date, owner, cost, detail1 …) let normalize(),
   populate(), and buildPayload() work domain-agnostically.
============================================================ */
const DOMAIN_CONFIG = {
  medical: {
    label: 'Visit',
    formId: '#visitForm',
    dom: {
      date:    '#visitDate',
      owner:   '#drname',        // doctor name
      title:   '#diagnosis',
      service: '#treatment',
      notes:   '#details',
      cost:    '#coast',         // HTML id (matches backend "coast")
      paid:    '#payed',         // HTML id (matches backend "payed")
      debt:    '#debt',
      detail1: '#weight',        // medical → patient weight
      detail2: '#height',        // medical → patient height
      detail3: '#lab'            // medical → lab results
    },
    fields: {
      date:    'visit_date',
      owner:   'drname',
      title:   'diagnosis',
      service: 'treatment',
      notes:   'details',
      cost:    'coast',          // backend field name (not a typo)
      paid:    'payed',          // backend field name (not a typo)
      debt:    'debit',          // backend field name (not a typo)
      detail1: 'weight',
      detail2: 'height',
      detail3: 'lab'
    },
    lockOnPrint: true
  },

  business: {
    label: 'Transaction',
    formId: '#interactionForm',
    dom: {
      date:    '#interactionDate',
      owner:   '#employeeName',  // employee who handled it
      title:   '#purpose',
      service: '#service',
      notes:   '#notes',
      cost:    '#cost',
      paid:    '#paid',
      debt:    '#debt',
      detail1: '#outcome',       // business → transaction outcome
      detail2: '#nextFollowUp'   // business → next follow-up date
      // no detail3 for business
    },
    fields: {
      date:    'date',
      owner:   'handled_by',
      title:   'service_name',
      service: 'service',
      notes:   'notes',
      cost:    'amount',
      paid:    'paid',
      debt:    'balance',
      detail1: 'description',
      detail2: 'next'
      // no detail3 for business
    },
    lockOnPrint: true
  }
};

let domain = 'medical';                    // set from API on page load
const cfg = () => DOMAIN_CONFIG[domain];   // shorthand to get active config
let plan = "free";                          // user subscription plan
const pageSection = new URLSearchParams(window.location.search).get('section');
const transactionMode = Boolean(window.__transactionMode__) || pageSection === 'transactions';

/**
 * Tracks real active time on the page and sends ONLY one final value:
 * { seconds: totalActiveSeconds }
 *
 * Usage:
 * startUsageTracker("/track_time");
 */
function startUsageTracker(endpoint) {

  let totalActiveSeconds = 0;
  let active = true;

  // Count only when the page is visible & focused
  document.addEventListener("visibilitychange", () => {
    active = !document.hidden;
  });

  window.addEventListener("blur", () => { active = false; });
  window.addEventListener("focus", () => { active = true; });

  // Tick every second → adds to active use
  setInterval(() => {
    if (active) totalActiveSeconds += 1;
  }, 1000);

  // Send the final total when the session ends
  function sendFinal() {
    if (totalActiveSeconds <= 0) return;

    const payload = JSON.stringify({ seconds: totalActiveSeconds });

    // Use sendBeacon so it always sends before page unload
    const blob = new Blob([payload], { type: 'application/json' });
    navigator.sendBeacon(endpoint, blob);
  }

  // On close / refresh / navigation
  window.addEventListener("beforeunload", sendFinal);

  // Return API for manual flush if needed
  return {
    getSeconds: () => totalActiveSeconds,
    flush: sendFinal
  };
}



function el(id) { return document.getElementById(id); }

function applySectionContext() {
  const topBarTitle = document.querySelector('.top-bar-title');
  const pageTitle = document.querySelector('.page-title');
  const pageSubtitle = document.querySelector('.page-subtitle');
  const saveButton = $('#saveBtn');

  if (saveButton) {
    saveButton.textContent = 'Save Changes';
  }

  if (transactionMode) {
    if (topBarTitle) topBarTitle.textContent = 'Client Payment Log';
    if (pageTitle) pageTitle.textContent = 'Client Payment Log';
    if (pageSubtitle) pageSubtitle.textContent = 'Record payments and payment history for this client';
  } else {
    if (topBarTitle) topBarTitle.textContent = 'Client Appointment Log';
    if (pageTitle) pageTitle.textContent = 'Client Appointment Log';
    if (pageSubtitle) pageSubtitle.textContent = 'Record appointments and interaction notes for this client';
  }
}

function show_toast(message, type = 'info') {
  const container = el('toast_container') || el('toast');
  if (!container) return;
  const t = document.createElement('div');
  t.className = 'toast';
  t.style.padding = '10px 12px';
  t.style.borderRadius = '10px';
  t.style.fontWeight = 700;
  t.textContent = message;
  if (type === 'error') { t.style.background = '#fee2e2'; t.style.color = '#991b1b'; t.style.borderLeft = '6px solid #ef4444'; }
  else if (type === 'success') { t.style.background = '#dcfce7'; t.style.color = '#065f46'; t.style.borderLeft = '6px solid #10b981'; }
  else { t.style.background = '#dbeafe'; t.style.color = '#1e3a8a'; t.style.borderLeft = '6px solid #3b82f6'; }
  container.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

/* ============================================================
   Global State
============================================================ */
let user_id = '';
let visibleCount = 20;
const PAGE_SIZE = 20;              // array of interaction objects for this client
let currentVisitIndex = 0;     // index into visits[] currently shown in form
let patientNumber = window.__client__ ?? 0;  // client number from URL (-1 = new)
let forceNewEntry = new URLSearchParams(window.location.search).get('action') === 'new';
let pendingDroppedFiles = [];

/* ============================================================
   Fetch helpers
============================================================ */
async function safe_fetch(url, opts = {}) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    show_toast(`Error: ${r.status}`, "error");
    throw new Error(`HTTP ${r.status}: ${text}`);
  }
  return r.json();
}

async function get_plan_status() {
  try {
    const data = await safe_fetch('/api/binder/get_plan_status', { method: 'GET' });
    // expected shape: { data: { days: N, plan: 'x' } } or { days: N, plan: 'x' }
    if (!data) return null;
    const payload = data.data || data;
    return { days: Number(payload.days || 0), plan: payload.plan || null };
  } catch (err) {
    return null;
  }
}

/* ============================================================
   Menu Initialization
============================================================ */
function menu_init() {
  const menuBtn = document.querySelector('.hamburger-menu');
  const menuBar = document.getElementById('menuBar');
  if (!menuBtn || !menuBar) return;
  menuBtn.addEventListener('click', () => {
    menuBar.classList.toggle('menu-active');
  });
  document.addEventListener('click', (ev) => {
    if (!menuBar.contains(ev.target) && !menuBtn.contains(ev.target) && menuBar.classList.contains('menu-active')) {
      menuBar.classList.remove('menu-active');
    }
  });
}

/* ============================================================
   Init
============================================================ */
document.addEventListener('DOMContentLoaded', async () => {
  menu_init();
  applySectionContext();

  const usage = startUsageTracker("/api/binder/track_time");
  domain = (await safe_fetch('/api/binder/get_domain')).data || 'medical';
  user_id = (await safe_fetch('/api/auth/me')).data.id;
  plan = (await get_plan_status()).plan;

  bindControls();
  fetchClientData();

  // If opened from client transactions action, guide attention to transaction fields.
  if (transactionMode) {
    setTimeout(() => {
      const target = $('#cost') || $('#paid') || $('#debt');
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.focus();
      }
      ['#cost', '#paid', '#debt', '#service', '#outcome'].forEach((sel) => {
        const node = $(sel);
        if (!node) return;
        node.style.boxShadow = '0 0 0 3px rgba(245, 158, 11, 0.28)';
        setTimeout(() => { node.style.boxShadow = ''; }, 1400);
      });
      show_toast('Payment log opened on the same page. Use cost, paid, and outstanding fields.', 'info');
    }, 300);
  }
});

/* ============================================================
   Bind UI
============================================================ */
function bindControls() {
  $('#searchButton')?.addEventListener('click', search);
  $('#prevButton')?.addEventListener('click', prev);
  $('#nextButton')?.addEventListener('click', next);
  $('#firstButton')?.addEventListener('click', first);
  $('#lastButton')?.addEventListener('click', last);
  $('#saveBtn')?.addEventListener('click', save);
  $('#printBtn')?.addEventListener('click', printInteraction);
  $('#openFolderBtn')?.addEventListener('click', openFolder);
  $('#closeModal')?.addEventListener('click',closeFileModal)
  $$('.folder-btn').forEach((btn) => {
    btn.addEventListener('click', () => selectFolder(btn.dataset.folder));
  });
  $('#chooseFile')?.addEventListener('click', () => $('#fileInput')?.click());
  $('#fileInput')?.addEventListener('change', onFilesSelected);
  $('#uploadFiles')?.addEventListener('click', uploadFile);
  const dropZone = $('#dropZone');
  if (dropZone) {
    dropZone.addEventListener('click', () => $('#fileInput')?.click());
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      const fileInput = $('#fileInput');
      if (!fileInput || !e.dataTransfer?.files?.length) return;
      pendingDroppedFiles = Array.from(e.dataTransfer.files || []);
      try {
        fileInput.files = e.dataTransfer.files;
      } catch (_) {
        // Some browsers block programmatic assignment to FileList.
      }
      onFilesSelected();
    });
  }
  $('#addNewEntryBtn')?.addEventListener('click', openNewEntry);
  $('#backBtn')?.addEventListener('click', () => {
    const lastPagePath = resolveLastPagePath();
    if (lastPagePath) {
      window.location.href = lastPagePath;
      return;
    }

    if (window.history.length > 1) {
      window.history.back();
      return;
    }

    window.location.href = '/client';
  });
}

/* ============================================================
   Normalize
   Converts a raw API interaction object into a generic shape
   using the active domain's field mapping. This lets populate()
   and the rest of the code work without knowing which domain.
============================================================ */
function normalize(raw = {}) {
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
    detail1: raw[f.detail1] || '',
    detail2: raw[f.detail2] || '',
    detail3: raw[f.detail3] || '',
    printed: !!raw.printed,
    vno: raw.vno || 1
  };
}

/* ============================================================
   Populate
   Writes a normalized interaction into the DOM form inputs.
   If the interaction was printed and lockOnPrint is set,
   all inputs are disabled so the record can't be changed.
============================================================ */
function populate(raw) {
  const v = normalize(raw);
  const d = cfg().dom;

  $(d.date).value = v.date;
  $(d.owner).value = v.owner;
  $(d.title).value = v.title;
  $(d.service).value = v.service;
  $(d.notes).value = v.notes;
  $(d.cost).value = v.cost;
  $(d.paid).value = v.paid;
  $(d.debt).value = v.debt;
  $(d.detail1).value = v.detail1;
  $(d.detail2).value = v.detail2;
  if (Boolean(d.detail3)){
    $(d.detail3).value = v.detail3;
  }

  const locked = v.printed && cfg().lockOnPrint;
  $(`${cfg().formId}`)?.querySelectorAll('input, textarea')
    .forEach(e => e.disabled = locked);
}

/* ============================================================
   Fetch Client
   Loads all interactions for the current client (patientNumber)
   and displays the most recent one.
============================================================ */
function fetchClientData() {
  fetch(`/api/binder/clients/${patientNumber}?domain=${domain}&user_id=${user_id}`)
    .then(r => r.json())
    .then(r => {
      visits = r.data.interactions || [];
      visibleCount = PAGE_SIZE;
      if (!Array.isArray(visits)) visits = [visits];
      const hasEntries = visits.some((v) => Object.keys(v || {}).length > 0);
      const openInNewMode = forceNewEntry;

      if (openInNewMode) {
        visits.push({});
        currentVisitIndex = visits.length - 1;
        forceNewEntry = false;
      } else {
        currentVisitIndex = visits.length ? visits.length - 1 : 0;
      }

      renderLogPanel();

      if (openInNewMode || !hasEntries) {
        showInteractionForm();
        populate(visits[currentVisitIndex] || {});
      }
      show_toast("Fetched client interaction" , "success");
    }).catch( err =>{
      show_toast(`Error Fetching interaction`,"error");
      console.error(`Error Fetching interaction`,err);
    });
}

/* ============================================================
   Navigation
   Walk through the visits[] array. "next" past the last visit
   creates a blank entry so the user can add a new interaction.
============================================================ */
function first(){ if(visits.length){ currentVisitIndex=0; showInteractionForm(); populate(visits[0]); selectLogItem(currentVisitIndex); } }
function last(){ if(visits.length){ currentVisitIndex=visits.length-1; showInteractionForm(); populate(visits[currentVisitIndex]); selectLogItem(currentVisitIndex); } }
function prev(){ if(currentVisitIndex>0){ currentVisitIndex--; showInteractionForm(); populate(visits[currentVisitIndex]); selectLogItem(currentVisitIndex); } }
function next(){
  if(visits[currentVisitIndex+1]){
    currentVisitIndex++;
    showInteractionForm();
    populate(visits[currentVisitIndex]);
    selectLogItem(currentVisitIndex);
  } else {
    visits.push({});
    currentVisitIndex = visits.length - 1;
    renderLogPanel();
    showInteractionForm();
    populate({});
    selectLogItem(currentVisitIndex);
  }
}

/* ============================================================
   Search
============================================================ */
function search() {
  const d = $('#search').value;
  const f = cfg().fields.date;
  const found = visits.find(v => v[f] === d);
  if (!found) return show_toast('Not found', 'info');
  currentVisitIndex = visits.indexOf(found);
  showInteractionForm();
  populate(found);
  selectLogItem(currentVisitIndex);
}

/* ============================================================
   Save
   buildPayload() reads form inputs → API-shaped object.
   save() decides POST (new) vs PATCH (existing) based on
   whether the current visits[] slot is empty.
============================================================ */
function buildPayload() {
  const f = cfg().fields;
  const d = cfg().dom;

  const data = {
    [f.date]: $(d.date).value,
    [f.owner]: $(d.owner).value,
    [f.title]: $(d.title).value,
    [f.service]: $(d.service).value,
    [f.notes]: $(d.notes).value,
    [f.cost]: Number($(d.cost).value || 0),
    [f.paid]: Number($(d.paid).value || 0),
    [f.detail1]: $(d.detail1).value,
    [f.detail2]: $(d.detail2).value,
    vno: visits[currentVisitIndex]?.vno || currentVisitIndex + 1
  };
  if (Boolean(d.detail3)){
    data[f.detail3]= $(d.detail3).value;
  }
  data[f.debt] = data[f.cost] - data[f.paid];
  $(d.debt).value = data[f.debt];

  return data;
}

function save() {
  const payload = buildPayload();
  // vno is 1-based; treat empty objects (from next()) as new
  const isNew = visits.length === 0 || Object.keys(visits[currentVisitIndex] || {}).length === 0;

  const method = isNew ? 'POST' : 'PATCH';
  const body = isNew
    ? { domain, user_id, interaction: payload, interaction_no: payload.vno }
    : { domain, user_id, patch: payload, interaction_no: payload.vno };

  fetch(`/api/binder/clients/${patientNumber}/interactions`, {
    method,
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body)
  })
  .then(() => {
    fetchClientData();
    if (isNew) {
      show_toast(transactionMode ? 'Payment log added' : 'Interaction added', 'success');
    } else {
      show_toast(transactionMode ? 'Changes saved in payment log' : 'Changes saved in interaction', 'success');
    }
  })
  .catch(err => {
    show_toast("Error saving interaction", "error");
    console.error("Error saving interaction", err);
  });
}

function showInteractionForm() {
  const card = $('#interactionCard');
  if (card) card.style.display = 'block';
}

function hideInteractionForm() {
  const card = $('#interactionCard');
  if (card) card.style.display = 'none';
}

function getEntryDate(entry) {
  return entry?.[cfg().fields.date] || 'No date';
}

function getEntryLabel(entry, index) {
  const number = entry?.vno || index + 1;
  const owner = entry?.[cfg().fields.owner] || 'Unassigned';
  const title = entry?.[cfg().fields.title] || (transactionMode ? 'Payment entry' : 'Appointment entry');
  return `#${number} - ${title} (${owner})`;
}

function selectLogItem(index) {
  const list = $('#logList');
  if (!list) return;
  list.querySelectorAll('[data-log-index]').forEach((item) => {
    item.style.borderColor = 'var(--border)';
    item.style.background = 'var(--bg-card)';
  });

  const active = list.querySelector(`[data-log-index="${index}"]`);
  if (active) {
    active.style.borderColor = 'var(--accent)';
    active.style.background = 'rgba(17, 113, 187, 0.08)';
  }
}

function openExistingEntry(index) {
  currentVisitIndex = index;
  showInteractionForm();
  populate(visits[currentVisitIndex] || {});
  selectLogItem(currentVisitIndex);
}

function openNewEntry() {
  const currentEntry = visits[currentVisitIndex] || {};
  const currentIsBlank = Object.keys(currentEntry).length === 0;

  if (!currentIsBlank) {
    visits.push({});
    currentVisitIndex = visits.length - 1;
  }

  renderLogPanel();
  showInteractionForm();
  populate({});
  selectLogItem(currentVisitIndex);
  show_toast(transactionMode ? 'Adding new transaction' : 'Adding new interaction', 'info');
}

function renderLogPanel() {
  const logSection = $('#logSection');
  const logList = $('#logList');
  const logTitle = $('#logTitle');
  const addNewBtn = $('#addNewEntryBtn');
  if (!logSection || !logList || !logTitle || !addNewBtn) return;

  const hasEntries = visits.some((v) => Object.keys(v || {}).length > 0);
  logTitle.textContent = transactionMode ? 'Transaction Log' : 'Interaction Log';
  addNewBtn.textContent = transactionMode ? 'Add New Transaction' : 'Add New Interaction';

  if (!hasEntries) {
    logSection.style.display = 'none';
    showInteractionForm();
    return;
  }

  logSection.style.display = 'block';
  hideInteractionForm();

  const entries = visits
  .map((entry, index) => ({ entry, index }))
  .filter(({ entry }) => Object.keys(entry || {}).length > 0)
  .reverse()
  .slice(0, visibleCount);

  logList.innerHTML = entries.map(({ entry, index }) => `
    <button
      type="button"
      data-log-index="${index}"
      style="text-align:left; border:1px solid var(--border); background:var(--bg-card); border-radius:10px; padding:10px 12px; cursor:pointer; display:flex; justify-content:space-between; gap:8px; color:var(--text);"
    >
      <span style="font-weight:600;">${getEntryLabel(entry, index)}</span>
      <span style="color:var(--text-muted);">${getEntryDate(entry)}</span>
    </button>
  `).join('');

  logList.querySelectorAll('[data-log-index]').forEach((item) => {
    item.addEventListener('click', () => {
      const idx = Number(item.getAttribute('data-log-index'));
      if (Number.isNaN(idx)) return;
      openExistingEntry(idx);
    });
  });

  const firstIndex = Number(logList.querySelector('[data-log-index]')?.getAttribute('data-log-index'));
  if (!Number.isNaN(firstIndex)) {
    selectLogItem(firstIndex);
  }
  const totalEntries = visits.filter(v => Object.keys(v || {}).length > 0).length;

if (visibleCount < totalEntries) {
  const loadMoreBtn = document.createElement('button');
  loadMoreBtn.textContent = 'Load More';

  loadMoreBtn.style.marginTop = '10px';
  loadMoreBtn.style.padding = '8px 12px';
  loadMoreBtn.style.cursor = 'pointer';
  loadMoreBtn.style.borderRadius = '8px';
  loadMoreBtn.style.border = '1px solid var(--border)';
  loadMoreBtn.style.background = 'var(--bg-card)';
  loadMoreBtn.style.color = 'var(--text)';

  loadMoreBtn.onclick = () => {
    visibleCount += PAGE_SIZE;
    renderLogPanel();
  };

  logList.appendChild(loadMoreBtn);
}
}


/* ============================================================
   Print
   Generates a .docx download. In medical domain, printing
   also "locks" the interaction so it can't be edited afterward
   (printed=true flag, enforced by populate).
============================================================ */
function printInteraction() {
  let lock  = ["medical"].includes(domain);  // only medical locks on print
  if (lock && !confirm(`Lock this ${cfg().label}?`)) return;
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
    show_toast("Interaction printed","success");
    if (lock){
      show_toast("Interaction locked");
    }
    fetchClientData();
  })
  .catch(err => {
    show_toast("Error printing interaction","error");
    console.error("Error printing interaction",err)
  });
}

/* ============================================================
   FILES SECTION
   Client file management (upload, view, delete).
   All file features are gated behind the "pro" or "ultra" plan.
   Default folder: "drs" (medical) or "contracts" (business).
============================================================ */
const FILE_API_BASE = '/api/binder/files';

let selectedFolder = '';

function getDefaultFolderForDomain() {
  if (domain === 'medical') return 'drs';
  if (domain === 'business') return 'contracts';
  return 'docs';
}

// Default folder per domain
function initSelectedFolder() {
  selectedFolder = getDefaultFolderForDomain();
}

/* ---------- Open / Close (plan-gated) ---------- */
function openFolder() {
  if (!selectedFolder) initSelectedFolder();
  if (["pro","ultra"].includes(plan)){
    $('#fileModal').style.display = 'flex';
    selectFolder(selectedFolder);
  }else{
    show_toast("This feature is for the Pro and Ultra plans only");
  }
}
function closeFileModal() {
  $('#fileModal').style.display = 'none';
  $('#filePreviews').innerHTML = '';
}

/* ---------- Folder Handling (falls back to domain default) ---------- */
function selectFolder(folder) {
  selectedFolder = folder || getDefaultFolderForDomain();

  updateActiveFolderButton();
    
  const uploadControls = $('#uploadControls');
  if (uploadControls) {
    const canUpload = domain === 'business' || selectedFolder === 'drs';
    uploadControls.style.display = canUpload ? 'block' : 'none';
  }
  fetchFiles();
}

function updateActiveFolderButton() {
  $$('.folder-btn').forEach((btn) => {
    const isActive = btn.dataset.folder === selectedFolder;
    btn.classList.toggle('btn-primary', isActive);
    btn.classList.toggle('btn-secondary', !isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  });
}

/* ---------- Fetch Files (plan-gated) ---------- */
async function fetchFiles() {
  
  if (["pro","ultra"].includes(plan)){
    try {
      const res = await safe_fetch(`${FILE_API_BASE}/get_files?folder=${encodeURIComponent(selectedFolder)}&client_no=${encodeURIComponent(String(patientNumber))}`, {
        method: 'GET'
      });
      const files = Array.isArray(res?.data)
        ? res.data
        : Array.isArray(res?.data?.files)
          ? res.data.files
          : [];
      renderFiles(files);
    } catch (err) {
      console.error(err);
      show_toast('Failed to fetch files', 'error');
    }
  }else{
    show_toast("This feature is for the Pro and Ultra plans only", "info");
  }
}

/* ---------- Upload Files (sequential, with progress bar) ---------- */
function onFilesSelected(e){
  const inputFiles = Array.from($('#fileInput')?.files || []);
  if (inputFiles.length > 0) {
    pendingDroppedFiles = [];
  }
  const totalFiles = inputFiles.length || pendingDroppedFiles.length;
  if (totalFiles > 0) {
    show_toast(`${totalFiles} files selected`,'info');
  }
}

function uploadFile() {
  if (["pro","ultra"].includes(plan)){
    const inputFiles = Array.from($('#fileInput')?.files || []);
    const files = inputFiles.length ? inputFiles : pendingDroppedFiles;
    if (!files.length) return show_toast('No files selected', 'error');
    if (["medical"].includes(domain) && selectedFolder !== 'drs') return show_toast('Uploads only allowed in Doctor folder', 'error');
    const total = files.length;
    let index = 0;
    const progressEl = $('#fileUploadProgress');
    const progressTextEl = $('#progressText');
    $('#uploadProgressContainer').style.display = 'block';
    if (progressEl) progressEl.value = 0;
    if (progressTextEl) progressTextEl.textContent = `0 / ${total}`;

    const uploadNext = () => {
      if (index >= total) {
        $('#uploadProgressContainer').style.display = 'none';
        $('#fileInput').value = '';
        pendingDroppedFiles = [];
        show_toast('All files uploaded', 'success');
        fetchFiles();
        return;
      }

      const form = new FormData();
      form.append('file', files[index]);
      form.append('folder', selectedFolder);
      form.append('client_no', patientNumber); // adjust if needed
      form.append('user_id', user_id);

      fetch(`${FILE_API_BASE}/upload_file`, { method: 'POST', body: form })
        .then(res => res.json())
        .then(res => {
          if (res.status === 'success') {
            index++;
            if (progressEl) progressEl.value = Math.round((index / total) * 100);
            if (progressTextEl) progressTextEl.textContent = `${index} / ${total}`;
            uploadNext();
          } else {
            show_toast('Upload failed', 'error');
            $('#uploadProgressContainer').style.display = 'none';
            pendingDroppedFiles = [];
          }
        })
        .catch(err => {
          console.error(err);
          show_toast('Upload error', 'error');
          $('#uploadProgressContainer').style.display = 'none';
          pendingDroppedFiles = [];
        });
    };

    uploadNext();
  }else{
    show_toast("This feature is for the Pro and Ultra plans only", "info");
  }
}

/* ---------- Render Files (images, videos, or generic file links) ---------- */
function renderFiles(files) {
  if (["pro","ultra"].includes(plan)){
    const container = $('#filePreviews');
    container.innerHTML = '';
    if (!files.length) return container.innerHTML = '<div class="text-gray-500">No files</div>';

    const formatUploadDate = (value) => {
      if (!value) return 'Unknown date';
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) return String(value);
      return parsed.toLocaleString();
    };

    files.forEach(file => {
      const fileUrl = file?.data || file?.url || file?.file_url || '';
      const fileType = String(file?.file_type || file?.content_type || '').toLowerCase();
      const fileName = file?.name || file?.filename || 'file';
      const fileDate = formatUploadDate(file?.upload_date || file?.created_at || file?.date);
      if (!fileUrl) return;

      const wrapper = document.createElement('div');
      wrapper.className = 'file-preview';

      const link = document.createElement('a');
      link.href = fileUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';

      if (fileType.includes('image')) {
        const img = document.createElement('img');
        img.src = fileUrl;
        img.alt = fileName;
        link.appendChild(img);
      } else if (fileType.includes('video')) {
        const video = document.createElement('video');
        video.src = fileUrl;
        video.controls = true;
        video.className = 'rounded';
        link.appendChild(video);
      } else {
        const txt = document.createElement('div');
        txt.className = 'p-3 border rounded txtPrev';
        txt.textContent = fileName;
        link.appendChild(txt);
      }

      if (["docs","invoices","contracts",'drs'].includes(selectedFolder)) {
        const remove = document.createElement('div');
        remove.className = 'file-remove'; remove.innerHTML = '&times;';
        remove.onclick = (e) => { e.preventDefault(); if(confirm('Delete this file?')) deleteFile(fileUrl); };
        wrapper.appendChild(remove);
      }

      const meta = document.createElement('div');
      meta.className = 'file-meta';
      const typeLabel = fileType || 'unknown';
      meta.innerHTML = `
        <div class="file-name" title="${fileName}">${fileName}</div>
        <div class="file-sub">${typeLabel} • ${fileDate}</div>
      `;

      wrapper.appendChild(link);
      wrapper.appendChild(meta);
      container.appendChild(wrapper);
    });
  }
}

/* ---------- Delete File (plan-gated) ---------- */
async function deleteFile(url) {
  if (["pro","ultra"].includes(plan)){
    try {
      const res = await safe_fetch(`${FILE_API_BASE}/delete_file?url=${encodeURIComponent(url)}`, { method: 'DELETE' });
      if (res.status === 'success') show_toast('File deleted', 'success');
      fetchFiles();
    } catch (err) {
      console.error(err);
      show_toast('Delete failed', 'error');
    }
  }
}
