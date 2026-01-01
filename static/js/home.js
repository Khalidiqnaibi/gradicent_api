
const API_TIMEOUT_MS = 10_000;
const POLL_TRACK_INTERVAL_MS = 60_000;

let GLOBAL_USER_ID = null;
let GLOBAL_DOMAIN = null;

function el(id) { return document.getElementById(id); }

function show_toast(message, type = 'info') {
  const container = el('toasts');
  const t = document.createElement('div');
  t.className = 'toast-item';
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

document.addEventListener("DOMContentLoaded", async () => {
  startUsageTracker("/api/binder/track_time");

  try {
    menu_init()
    GLOBAL_USER_ID = await get_user_id();       // ex: 1015974463...
    GLOBAL_DOMAIN  = await get_domain();        // ex: "medical"
    let res = await get_plan_status();
    GLOBAL_PLAN = res.plan;

  } catch (err) {
    console.error(`Failed to load domain/user: ${err}`, "error");
    show_toast(`Failed to load domain/user`, "error");
  }
});

function menu_init() {
  const menuBtn = document.querySelector('.hamburger-menu');
  const menuBar = document.getElementById('menuBar');
  
  // Toggle menu (keeps same interaction as previous)
  menuBtn.addEventListener('click', () => {
    menuBar.classList.toggle('menu-active');
  });
  
  const menu_box = document.querySelector(".menu__box")
  // close when clicking outside (improves UX)
  document.addEventListener('click', (ev) => {
    if (!menuBar.contains(ev.target) && menuBar.classList.contains('menu-active')) {
      menuBar.classList.remove('menu-active');
      toggle.setAttribute('aria-expanded', 'false');
      menu_box.setAttribute('aria-hidden', 'true');
    }
  });
}

// ---------------------------------------------
//  SAFE FETCH WRAPPER (same across Binder)
// ---------------------------------------------
async function safePost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    const t = await res.text();
    throw new Error(`Request failed: ${res.status} → ${t}`);
  }

  return await res.json();
}

/**
 * get_plan_status
 * Returns { days: number, plan: string } or null.
 */
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

async function get_domain() {
  try {
    const data = await safe_fetch('/api/binder/get_domain', { method: 'GET' });
    if (data && (typeof data.data === 'string' || typeof data.domain === 'string')) {
      return data.data || data.domain;
    }
  } catch (err) {
    show_toast(`Failed to load domain`, "error");
    console.error(err,"error");
  }
  return null;
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

// ---------------------------------------------
//  USAGE TRACKER
// ---------------------------------------------
function startUsageTracker(endpoint) {
  let active = true;
  let seconds = 0;

  document.addEventListener("visibilitychange", () => {
    active = !document.hidden;
  });
  window.addEventListener("focus",  () => active = true);
  window.addEventListener("blur",   () => active = false);

  setInterval(() => { if (active) seconds++; }, 1000);

  window.addEventListener("beforeunload", () => {
    if (seconds > 0) {
      navigator.sendBeacon(endpoint, JSON.stringify({seconds}));
    }
  });
}



// ---------------------------------------------
//  BUILD client OBJECT
// ---------------------------------------------

// Map domain → { htmlId: backendKey }
const FIELD_MAP = {
  medical: {
    PName:      "name",
    idnum:      "gov_id",
    PNum:       "phone",
    loc:        "location",
    medh:       "pmh",
    allergies:  "allergies",
    btype:      "btype",
    sex:        "sex",
    age:        "age"
  },
  business: {
    PName:      "name",
    idnum:      "gov_id",
    PNum:       "phone",
    loc:        "location",
    medh:       "company",       
    allergies:  "industry",
    btype:      "email",   
    sex:        "account_manager",  
    age:        "company_size"    
  }
};


function buildClientObject() {
  const domain = GLOBAL_DOMAIN || "business";
  const map = FIELD_MAP[domain];

  const client = { debit: 0, payed: 0, interactions: [] };

  for (const [htmlId, key] of Object.entries(map)) {
    const el = document.getElementById(htmlId);
    if (el) client[key] = el.value.trim();
  }

  return client;
}


// ---------------------------------------------
//  SUBMIT
// ---------------------------------------------


async function submitClient() {
  const client = buildClientObject();

  if (!GLOBAL_USER_ID || !GLOBAL_DOMAIN) {
    show_toast("Unable to get user or domain. Please refresh the page." , "error");
    return;
  }

  if (!client.name) {
    show_toast("Please enter the Client name." , "info");
    return;
  }

  if (GLOBAL_DOMAIN == "medical" && client.age == 0){
    show_toast("Please enter the patient age." , "info");
    return;
  }

  try {

    const payload = {
      domain:GLOBAL_DOMAIN,
      user_id: GLOBAL_USER_ID,
      client
    };

    const result = await safePost("/api/binder/clients", payload);

    show_toast("Client added successfully!" , "success");
    document.getElementById("PName").value= '';
    document.getElementById("idnum").value= '';
    document.getElementById("PNum").value= '';
    document.getElementById("loc").value= '';
    document.getElementById("medh").value= '';
    document.getElementById("allergies").value= '';
    document.getElementById("btype").value= '';
    document.getElementById("sex").value= '';
    document.getElementById("age").value= '';
    if (["medical","business"].includes(GLOBAL_DOMAIN) && GLOBAL_PLAN !== "sec"){
      window.location.href = `/data/-1`;
    }else{
      show_toast("not impleminted yet!","info")
    }

  } catch (err) {
    show_toast("Error adding client." ,"error");
    console.error(`Error adding client: ${err}`, "error" );
  }
}