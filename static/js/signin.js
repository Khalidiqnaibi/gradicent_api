// set the domain type dynamically, e.g. from server or config
// 'medical' = clinic onboarding, 'business' = business onboarding
const domainType = '';

const API_TIMEOUT_MS = 10_000;

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

async function get_domain() {
  try {
    const r = await safe_fetch('/api/binder/get_domain');
    return r.data || r.domain || 'medical';
  } catch { return 'medical'; }
}

// define options for each domain
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



const specListEl = document.getElementById('specList');
const specDropdown = document.getElementById('specDropdown');
const specBtn = document.getElementById('specBtn');
const specValue = document.getElementById('specValue');
const specSearch = document.getElementById('specSearch');


document.addEventListener('DOMContentLoaded', async () => {
  domainType = await get_domain();
  const options = optionsByDomain[domainType];
  
  buildOptionList(options);
});

// populate options
function buildOptionList(options) {
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

function toggleDropdown(open){
  const isOpen = specDropdown.style.display !== 'none';
  const show = (open===undefined) ? !isOpen : !!open;
  specDropdown.style.display = show ? 'flex' : 'none';
  specBtn.setAttribute('aria-expanded', show ? 'true' : 'false');
  if(show){ specSearch.focus(); specSearch.select(); } else { specSearch.value=''; filterFunction(); }
}

function selectOption(opt){
  specValue.textContent = opt;
  toggleDropdown(false);
}

function filterFunction(){
  const q = specSearch.value.trim().toUpperCase();
  Array.from(specListEl.children).forEach(a=>{
    const txt = (a.textContent||'').toUpperCase();
    a.style.display = txt.indexOf(q) > -1 ? '' : 'none';
  });
}

// close dropdown when clicking outside or pressing Esc
document.addEventListener('click', (e) => {
  if (!document.getElementById('specialtyRoot').contains(e.target)) toggleDropdown(false);
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') toggleDropdown(false); });

// simple toast
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

// submit form
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
