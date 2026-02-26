// ===== Config =====
// Domain type is resolved at runtime: 'medical' = clinic, 'business' = company.
let domainType = '';

// Abort slow API calls to keep the UI responsive.
const API_TIMEOUT_MS = 10_000;

// Fetch helper with timeout + JSON handling.
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

// Ask the backend which domain is active.
async function get_domain() {
  try {
    const r = await safe_fetch('/api/binder/get_domain');
    return r.data || r.domain || 'medical';
  } catch { return 'medical'; }
}

// Domain-specific dropdown options.
const optionsByDomain = {
  medical: [
    "Accident and emergency medicine","Allergist","Anaesthetics","Cardiology","Child psychiatry",
    "Clinical biology","Clinical chemistry","Clinical microbiology","Clinical neurophysiology",
    "Craniofacial surgery","Dermatology","Endocrinology","Family and General Medicine",
    "Gastroenterologic surgery","Gastroenterology","General Practice","General surgery",
    "Geriatrics","Hematology","Immunology","Infectious diseases","Internal medicine",
    "Laboratory medicine","Nephrology","Neuropsychiatry","Neurology","Neurosurgery","Nuclear medicine",
    "Obstetrics and gynaecology","Occupational medicine","Oncology","Ophthalmology",
    "Oral and maxillofacial surgery","Orthopaedics","Otorhinolaryngology","Paediatric surgery",
    "Paediatrics","Pathology","Pharmacology","Physical medicine and rehabilitation","Plastic surgery",
    "Podiatric surgery","Preventive medicine","Psychiatry","Public health","Radiation Oncology",
    "Radiology","Respiratory medicine","Rheumatology","Stomatology","Thoracic surgery",
    "Tropical medicine","Urology","Vascular surgery","Venereology"
  ],
  business: [
    "Consulting","Retail","Wholesale","Technology / IT","Manufacturing","Healthcare services",
    "Education / Training","Hospitality / Tourism","Real estate","Transportation / Logistics",
    "Financial services","Marketing / Advertising","Legal services","Entertainment / Media",
    "Construction","Agriculture / Farming","Energy / Utilities","Nonprofit / NGO","Pharmaceuticals",
    "Telecommunications","Automotive","Food & Beverage","Beauty / Personal care","E-commerce",
    "Creative / Design","Fitness / Wellness","Professional services","Security / Surveillance",
    "Research & Development","Other"
  ]
};



// DOM references used by the dropdown.
const specListEl = document.getElementById('specList');
const specDropdown = document.getElementById('specDropdown');
const specBtn = document.getElementById('specBtn');
const specValue = document.getElementById('specValue');
const specSearch = document.getElementById('specSearch');


// Initialize options once the page is ready.
document.addEventListener('DOMContentLoaded', async () => {
  if (!specListEl) return;
  domainType = await get_domain();
  const options = optionsByDomain[domainType] || optionsByDomain.medical;
  buildOptionList(options);
});

// Populate dropdown with the given options.
function buildOptionList(options) {
  if (!specListEl) return;
  specListEl.innerHTML = '';
  options.forEach(opt => {
    const a = document.createElement('a');
    a.setAttribute('role','option');
    a.textContent = opt;
    a.href = 'javascript:void(0)';
    a.addEventListener('click', () => selectOption(opt));
    specListEl.appendChild(a);
  });
}

// Open/close the dropdown and manage focus.
function toggleDropdown(open){
  if (!specDropdown || !specBtn || !specSearch) return;
  const isOpen = specDropdown.style.display !== 'none';
  const show = (open===undefined) ? !isOpen : !!open;
  specDropdown.style.display = show ? 'flex' : 'none';
  specBtn.setAttribute('aria-expanded', show ? 'true' : 'false');
  if(show){ specSearch.focus(); specSearch.select(); } else { specSearch.value=''; filterFunction(); }
}

// Set the selected option and close the dropdown.
function selectOption(opt){
  if (!specValue) return;
  specValue.textContent = opt;
  toggleDropdown(false);
}

// Filter visible options based on search input.
function filterFunction(){
  if (!specSearch || !specListEl) return;
  const q = specSearch.value.trim().toUpperCase();
  Array.from(specListEl.children).forEach(a=>{
    const txt = (a.textContent||'').toUpperCase();
    a.style.display = txt.indexOf(q) > -1 ? '' : 'none';
  });
}

// Close dropdown when clicking outside or pressing Esc.
document.addEventListener('click', (e) => {
  const root = document.getElementById('specialtyRoot');
  if (!root) return;
  if (!root.contains(e.target)) toggleDropdown(false);
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') toggleDropdown(false); });

// Simple toast helper for status feedback.
function toast(msg, type='info'){
  const wrap = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  if(type==='error') el.style.background = '#B91C1C';
  if(type==='success') el.style.background = '#059669';
  wrap.appendChild(el);
  setTimeout(()=>{
    el.style.opacity = '0';
    el.style.transform='translateY(6px)';
    setTimeout(()=>el.remove(),400);
  }, 3500);
}

// Submit form to create/update the business/clinic profile.
async function sign(){
  const name = document.getElementById('drname').value.trim();
  const specialty = specValue.textContent.trim();
  const location = document.getElementById('location').value.trim();
  const phone = document.getElementById('phone').value.trim();

  if(!name){ toast(`Please enter your ${domainType==='medical'?'clinic/doctor name':'business name'}`,'error'); document.getElementById('drname').focus(); return; }
  if(!specialty){ toast(`Please choose a ${domainType==='medical'?'specialty':'business type'}`,'error'); toggleDropdown(true); return; }
  if(!location){ toast(`Please enter ${domainType==='medical'?'clinic location':'business location'}`,'error'); document.getElementById('location').focus(); return; }
  if(!phone){ toast('Please enter phone number','error'); document.getElementById('phone').focus(); return; }

  const payload = { name, specialty, location, phone, domain: domainType };

  try{
    toast('Saving…');
    const res = await fetch('/savesign', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    if(!res.ok) throw new Error('Network error');
    toast('Profile saved — redirecting...', 'success');
    setTimeout(()=> window.location.href = '/acc', 700);
  } catch(err){
    console.error(err);
    toast('Failed to save. Try again.', 'error');
  }
}
