/* ============================================================
   Helpers
============================================================ */
const $  = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

/* ============================================================
   Domain Configuration
============================================================ */
const DOMAIN_CONFIG = {
  medical: {
    label: 'Visit',
    formId: '#visitForm',
    dom: {
      date: '#visitDate',
      owner: '#drname',
      title: '#diagnosis',
      service: '#treatment',
      notes: '#details',
      cost: '#coast',
      paid: '#payed',
      debt: '#debt'
    },
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
    lockOnPrint: true
  },

  business: {
    label: 'Transaction',
    formId: '#interactionForm',
    dom: {
      date: '#interactionDate',
      owner: '#employeeName',
      title: '#purpose',
      service: '#outcome',
      notes: '#notes',
      cost: '#cost',
      paid: '#paid',
      debt: '#debt'
    },
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
    lockOnPrint: true
  }
};

let domain = 'medical';
const cfg = () => DOMAIN_CONFIG[domain];

/* ============================================================
   Global State
============================================================ */
let user_id = '';
let visits = [];
let currentVisitIndex = 0;
let patientNumber = window.__client__ || 0;

/* ============================================================
   Fetch helpers
============================================================ */
async function safe_fetch(url, opts = {}) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(r.status);
  return r.json();
}

/* ============================================================
   Init
============================================================ */
document.addEventListener('DOMContentLoaded', async () => {
  domain = (await safe_fetch('/api/binder/get_domain')).data || 'medical';
  user_id = (await safe_fetch('/api/auth/me')).data.id;

  bindControls();
  fetchClientData();
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
}

/* ============================================================
   Normalize
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
    printed: !!raw.printed,
    vno: raw.vno || 1
  };
}

/* ============================================================
   Populate
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

  const locked = v.printed && cfg().lockOnPrint;
  $(`${cfg().formId}`)?.querySelectorAll('input, textarea')
    .forEach(e => e.disabled = locked);
}

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
    });
}

/* ============================================================
   Navigation
============================================================ */
function first(){ if(visits.length){ currentVisitIndex=0; populate(visits[0]); } }
function last(){ if(visits.length){ currentVisitIndex=visits.length-1; populate(visits[currentVisitIndex]); } }
function prev(){ if(currentVisitIndex>0){ currentVisitIndex--; populate(visits[currentVisitIndex]); } }
function next(){
  if(visits[currentVisitIndex+1]){
    currentVisitIndex++;
    populate(visits[currentVisitIndex]);
  } else {
    visits.push({});
    currentVisitIndex = visits.length - 1;
    populate({});
  }
}

/* ============================================================
   Search
============================================================ */
function search() {
  const d = $('#search').value;
  const f = cfg().fields.date;
  const found = visits.find(v => v[f] === d);
  if (!found) return alert('Not found');
  currentVisitIndex = visits.indexOf(found);
  populate(found);
}

/* ============================================================
   Save
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
    vno: visits[currentVisitIndex]?.vno || currentVisitIndex + 1
  };

  data[f.debt] = data[f.cost] - data[f.paid];
  $(d.debt).value = data[f.debt];

  return data;
}

function save() {
  const payload = buildPayload();
  fetch(`/api/binder/clients/${patientNumber}/interactions`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      domain,
      user_id,
      interaction: payload,
      interaction_no: currentVisitIndex + 1
    })
  }).then(fetchClientData);
}

/* ============================================================
   Print
============================================================ */
function printInteraction() {
  if (!confirm(`Lock this ${cfg().label}?`)) return;
  fetch('/kkprint',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ vno: currentVisitIndex })
  }).then(fetchClientData);
}
