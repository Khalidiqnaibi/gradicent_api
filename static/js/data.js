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
    navigator.sendBeacon(endpoint, payload);
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

function show_toast(message, type = 'info') {
  const container = el('toast');
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
let visits = [];
let currentVisitIndex = 0;
let patientNumber = window.__client__ || 0;

/* ============================================================
   Fetch helpers
============================================================ */
async function safe_fetch(url, opts = {}) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    show_toast(r.status , "error");
  }
  return r.json();
}

/* ============================================================
   Init
============================================================ */
document.addEventListener('DOMContentLoaded', async () => {
  const usage = startUsageTracker("/api/binder/track_time");
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
      show_toast("Fetched client interaction" , "success");
    }).catch( err =>{
      show_toast(`Error Fetching interaction`,"error");
      console.error(`Error Fetching interaction`,err);
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
  }).then(data =>{
    fetchClientData();
    show_toast("Interaction saved ", "success");
  }).catch(err => {
    show_toast("Error saving interaction" , "error");
    console.error("Error saving interaction",err);
  });
}

/* ============================================================
   Print
============================================================ */
function printInteraction() {
  let lock  = ["medical"].includes(domain);
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

// FILES:
const FILE_API_BASE = '/api/binder/files';


/* ---------- Open / Close ---------- */
function openFile() {
  if (["pro","ultra"].includes(plan)){
    $('#fileModal').style.display = 'flex';
    selectFolder('drs');
  }else{
    showToast("This feature is for the Pro and Ultra plans only");
  }
}
function closeFileModal() {
  $('#fileModal').style.display = 'none';
  $('#filePreviews').innerHTML = '';
}

/* ---------- Folder Handling ---------- */
function selectFolder(folder) {
  selectedFolder = folder || 'drs';
  $('#uploadControls').style.display = selectedFolder === 'drs' ? 'flex' : 'none';
  fetchFiles();
}

/* ---------- Fetch Files ---------- */
async function fetchFiles() {
  
  if (["pro","ultra"].includes(plan)){
    try {
      const res = await safe_fetch(`${FILE_API_BASE}/get_files?folder=${encodeURIComponent(selectedFolder)}&client_no=${patientNumber}`, {
        method: 'GET'
      });
      renderFiles(res.data || []);
    } catch (err) {
      console.error(err);
      showToast('Failed to fetch files', 'error');
    }
  }else{
    alert("Hmm thats weird right?");
  }
}

/* ---------- Upload Files ---------- */
function onFilesSelected(e){
    if($('#fileInput').files.length) showToast(`${$('#fileInput').files.length} files selected`,'info');
  }

function uploadFile() {
  if (["pro","ultra"].includes(plan)){
    const files = $('#fileInput').files;
    if (!files.length) return showToast('No files selected', 'error');
    if (selectedFolder !== 'drs') return showToast('Uploads only allowed in Doctor folder', 'error');

    const total = files.length;
    let index = 0;
    $('#uploadProgressContainer').style.display = 'block';

    const uploadNext = () => {
      if (index >= total) {
        $('#uploadProgressContainer').style.display = 'none';
        $('#fileInput').value = '';
        showToast('All files uploaded', 'success');
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
            uploadNext();
          } else {
            showToast('Upload failed', 'error');
            $('#uploadProgressContainer').style.display = 'none';
          }
        })
        .catch(err => {
          console.error(err);
          showToast('Upload error', 'error');
          $('#uploadProgressContainer').style.display = 'none';
        });
    };

    uploadNext();
  }else{
    alert("Hmm thats weird right?");
  }
}

/* ---------- Render Files ---------- */
function renderFiles(files) {
  if (["pro","ultra"].includes(plan)){
    const container = $('#filePreviews');
    container.innerHTML = '';
    if (!files.length) return container.innerHTML = '<div class="text-gray-500">No files</div>';

    files.forEach(file => {
      const wrapper = document.createElement('div');
      wrapper.className = 'file-preview';

      const link = document.createElement('a');
      link.href = file.data;
      link.target = '_blank';

      if (file.file_type.includes('image')) {
        const img = document.createElement('img'); img.src = file.data; link.appendChild(img);
      } else if (file.file_type.includes('video')) {
        const video = document.createElement('video'); video.src = file.data; video.controls = true; video.className = 'rounded'; link.appendChild(video);
      } else {
        const txt = document.createElement('div'); txt.className = 'p-3 border rounded txtPrev'; txt.textContent = file.name || 'file'; link.appendChild(txt);
      }

      if (selectedFolder === 'drs') {
        const remove = document.createElement('div');
        remove.className = 'file-remove'; remove.innerHTML = '&times;';
        remove.onclick = (e) => { e.preventDefault(); if(confirm('Delete this file?')) deleteFile(file.data); };
        wrapper.appendChild(remove);
      }

      wrapper.appendChild(link);
      container.appendChild(wrapper);
    });
  }
}

/* ---------- Delete File ---------- */
async function deleteFile(url) {
  if (["pro","ultra"].includes(plan)){
    try {
      const res = await safe_fetch(`${FILE_API_BASE}/delete_file?url=${encodeURIComponent(url)}`, { method: 'DELETE' });
      if (res.status === 'success') showToast('File deleted', 'success');
      fetchFiles();
    } catch (err) {
      console.error(err);
      showToast('Delete failed', 'error');
    }
  }
}

