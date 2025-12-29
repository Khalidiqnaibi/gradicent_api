
  // Helpers
  const $  = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  
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

  // Toast system
  function showToast(text, type = 'info') {
    const c = document.getElementById('toastContainer');
    if (!c) return;

    const el = document.createElement('div');
    el.className = `item ${type}`;
    el.textContent = text;
    c.appendChild(el);

    // animate out after 3s
    setTimeout(() => {
      el.classList.add('hide');
      setTimeout(() => el.remove(), 400);
    }, 3000);
  }

  // State
  const API_TIMEOUT_MS = 10_000;
  const POLL_TRACK_INTERVAL_MS = 60_000;
  let user_id = "";
  let visits = [];
  let currentVisitIndex = 0;
  let patientNumber = '{{client}}';
  let selectedFolder = 'drs';
  let domain = "";
  let plan ='free';
  
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
      // assume JSON by default
      const ct = (res.headers.get('content-type') || '');
      if (ct.includes('application/json')) return res.json();
      return res.text();
    } catch (err) {
      clearTimeout(timeout);
      throw err;
    }
  }

  async function get_user(){
    const url = `/api/auth/me`;
    const data = await safe_fetch(url, { method: 'GET' });
    return data.data;    
  }

  async function get_user_id(){
    user = await get_user();
    return user.id;    
  }

  async function get_domain() {
    try {
      const data = await safe_fetch('/api/binder/get_domain', { method: 'GET' });
      if (data && (typeof data.data === 'string' || typeof data.domain === 'string')) {
        return data.data || data.domain;
      }
    } catch (err) {
      console.log(err)
    }
    return "medical";
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

  document.addEventListener('DOMContentLoaded', async function() {
    domain = await get_domain();
    user_id = await get_user_id();
    let res = await get_plan_status();
    plan = res.plan;

    // Hamburger menu
    const menuBtn = document.querySelector('.hamburger-menu');
    const menuBar = document.getElementById('menuBar');
    menuBtn.addEventListener('click', () => {
      menuBar.classList.toggle('menu-active');
    });
    const usage = startUsageTracker("/api/binder/track_time");
    // Button bindings
    $('#searchButton').addEventListener('click', search);
    $('#prevButton').addEventListener('click', prev);
    $('#nextButton').addEventListener('click', next);
    $('#firstButton').addEventListener('click', first);
    $('#lastButton').addEventListener('click', last);
    $('#saveBtn').addEventListener('click', save);
    $('#openFolderBtn').addEventListener('click', openFile);
    $('#printBtn').addEventListener('click', () => { save(); printVisit(); });

    // File modal
    $('#closeModal').addEventListener('click', closeFileModal);
    $('#chooseFile').addEventListener('click', () => $('#fileInput').click());
    $('#fileInput').addEventListener('change', onFilesSelected);
    $('#uploadFiles').addEventListener('click', uploadFile);

    $$('.folder-btn').forEach(b => b.addEventListener('click', (e) => {
      $$('.folder-btn').forEach(x => x.classList.remove('bg-[var(--accent)]/20'));
      e.currentTarget.classList.add('bg-[var(--accent)]/20');
      selectFolder(e.currentTarget.dataset.folder || 'drs');
    }));

    // Keyboard flow
    const entryWidgets = {
      visit_date: $('#visitDate'), drname: $('#drname'),
      diagnosis: $('#diagnosis'), treatment: $('#treatment'),
      lab: $('#lab'), wight: $('#wight'),
      height: $('#height'), coast: $('#coast'),
      payed: $('#payed'), debit: $('#debt'),
      details: $('#details'), search: $('#search')
    };
    Object.values(entryWidgets).forEach(widget => {
      if (!widget) return;
      widget.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey && widget.tagName !== 'TEXTAREA') {
          e.preventDefault();
          const fields = Object.values(entryWidgets).filter(Boolean);
          const idx = fields.indexOf(widget);
          if (idx >= 0 && idx < fields.length - 1) fields[idx + 1].focus();
        }
      });
    });

    fetchPatientData();
  });

  // Patient data
  function fetchPatientData() {
    fetch(`/api/binder/clients/${patientNumber}?domain=${domain}&user_id=${user_id}`)
      .then(r => r.json())
      .then(data => {
        data = data.data;
        
        var len = data.interactions.length;
        if (len){
          visits = data.interactions;
        }else{
          visits = [data.interactions];
          len = 1;
        }

        if (len) {
          currentVisitIndex = len-1;
          populatePatientData(visits[currentVisitIndex]);
          showToast('Patient data loaded', 'success');
        } else {
          const t = { visit_date: '', drname:'', diagnosis:'', treatment:'', lab:'', wight:'0', height:'0', coast:0, payed:0, debit:0, details:'', vno:1 };
          visits=[t]; currentVisitIndex=0; populatePatientData(t);
        }
      })
      .catch(err => { console.error(err); showToast('Failed to load client data', 'error'); });
  }

  function populatePatientData(visit) {
    $('#visitDate').value = visit.visit_date || '';
    $('#drname').value = visit.drname || '';
    $('#diagnosis').value = visit.diagnosis || '';
    $('#treatment').value = visit.treatment || '';
    $('#lab').value = visit.lab || '';
    $('#wight').value = visit.wight ?? '0';
    $('#height').value = visit.height ?? '0';
    $('#coast').value = visit.coast ?? '0';
    $('#payed').value = visit.payed ?? '0';
    $('#debt').value = visit.debit ?? '0';
    $('#details').value = visit.details || '';

    const printed = !!visit.printed;
    if (printed) {
      $$('#visitForm input, #visitForm textarea').forEach(el => el.disabled = true);
      $('#search').disabled = false;
      showToast('This visit is locked (printed).', 'info');
    } else {
      $$('#visitForm input, #visitForm textarea').forEach(el => el.disabled = false);
    }
    if (!visit.drname || visit.drname.trim() === '') $('#drname').disabled = false;
    else $('#drname').disabled = true;
  }

  // Navigation
  function first() { if(visits.length){ currentVisitIndex=0; populatePatientData(visits[0]); } }
  function prev() { if(currentVisitIndex>0){ currentVisitIndex--; populatePatientData(visits[currentVisitIndex]); } }
  function next() {
    const newIdx=currentVisitIndex+1;
    if(visits[newIdx]){ currentVisitIndex=newIdx; populatePatientData(visits[newIdx]); }
    else {
      const t={visit_date:'', drname:'', treatment:'', diagnosis:'', lab:'', wight:'0', height:'0', coast:0, payed:0, debit:0, details:'', vno:visits.length+1};
      visits.push(t); currentVisitIndex=visits.length-1; populatePatientData(t);
    }
  }
  function last() { if(visits.length){ currentVisitIndex=visits.length-1; populatePatientData(visits[currentVisitIndex]); } }

  function search() {
    const dateToSearch=$('#search').value;
    const found=visits.find(v=>v.visit_date===dateToSearch);
    if(found){ currentVisitIndex=visits.indexOf(found); populatePatientData(found); showToast('Visit found','success'); }
    else showToast('No visit for that date','info');
  }

  // Save
  function save() {
    const visitData = {
      visit_date: $('#visitDate').value.trim(),
      drname: $('#drname').value.trim(),
      treatment: $('#treatment').value.trim(),
      diagnosis: $('#diagnosis').value.trim(),
      lab: $('#lab').value.trim(),
      wight: $('#wight').value || '0',
      height: $('#height').value || '0',
      debit: parseFloat($('#debt').value) || 0,
      payed: parseFloat($('#payed').value) || 0,
      coast: parseFloat($('#coast').value) || 0,
      details: $('#details').value.trim(),
      vno: (visits[currentVisitIndex] && visits[currentVisitIndex].vno) || (currentVisitIndex+1)
    };
    if (!visitData.visit_date) { showToast('Visit date is required','error'); return; }
    totald(visitData);
    if (visits.length == currentVisitIndex+1){
      fetch(`/api/binder/clients/${patientNumber}/interactions`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({"user_id":user_id,"domain":domain,"interaction":visitData})})
        .then(()=> { showToast('Visit saved','success'); fetchPatientData(); })
        .catch(err=>{console.error(err); showToast('Error saving visit','error');});
    }else{
      fetch(`/api/binder/clients/${patientNumber}/interactions`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({"user_id":user_id,"interaction_no" : currentVisitIndex +1,"domain":domain,"patch":visitData})})
        .then(()=> { showToast('Visit saved','success'); fetchPatientData(); })
        .catch(err=>{console.error(err); showToast('Error saving visit','error');});
    }
  }

  function totald(visitData){
    try{
      if(parseFloat(visitData.payed)>0 && parseFloat(visitData.coast)>0){
        const res=parseFloat(visitData.coast)-parseFloat(visitData.payed);
        $('#debt').value=res; visitData.debit=res;
      } else if(parseFloat(visitData.debit)!==0 && parseFloat(visitData.coast)>0){
        if(parseFloat(visitData.debit)>0){
          const res=parseFloat(visitData.coast)-parseFloat(visitData.debit);
          $('#payed').value=res; visitData.payed=res;
        } else {
          const res=parseFloat(visitData.coast)+parseFloat(visitData.debit);
          $('#payed').value=res; visitData.payed=res;
        }
      } else if(parseFloat(visitData.debit)!==0 && parseFloat(visitData.payed)>0){
        const res=parseFloat(visitData.payed)+parseFloat(visitData.debit);
        $('#coast').value=res; visitData.coast=res;
      } else if(parseFloat(visitData.coast)>0){
        const res=parseFloat(visitData.coast);
        $('#debt').value=res; visitData.debit=res;
      }
    } catch(e){ console.error('totald error',e);}
    return visitData;
  }

  function printVisit(){
    if(!confirm("After printing you can't change this visit's info. Continue?")) return;
    fetch('/kkprint',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ vno: currentVisitIndex })})
      .then(resp=>{ if(!resp.ok) throw new Error('Print failed'); return resp.blob(); })
      .then(blob=>{
        const url=URL.createObjectURL(blob);
        const a=document.createElement('a'); a.href=url; a.download='visit.docx';
        document.body.appendChild(a); a.click();
        url && URL.revokeObjectURL(url);
        showToast('Visit printed and locked','success');
        fetchPatientData();
      })
      .catch(err=>{console.error(err); showToast('Print failed','error');});
  }

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

/* ---------- Bind globals ---------- */
window.openFile = openFile;
window.printVisit = printVisit;
