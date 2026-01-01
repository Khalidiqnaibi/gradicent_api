
  /**
   * srch.html — minimal, logical, and stylish.
   * - Single input + single button (Enter works).
   * - Calls unified backend: POST /api/binder/search { query, domain?, user_id? }.
   * - Small modules: utils, api, ui, controller.
   * - Single-session usage tracker that sends final total to /track_time.
   */

  /* ----------------------
     Constants & App State
     ---------------------- */
  const API_SEARCH = '/api/binder/search/client';
  const API_GET_CLIENT = (id) => `/api/binder/clients/${encodeURIComponent(id)}?domain=${encodeURIComponent(APP_STATE.domain || '')}&user_id=${encodeURIComponent(APP_STATE.user_id || '')}`;
  const API_PATCH_CLIENT = (id) => `/api/binder/clients/${encodeURIComponent(id)}`;
  const API_OPEN_CLIENT = (id) => `/data/${encodeURIComponent(id)}`;
  const TRACK_ENDPOINT = '/api/binder/track_time';
  const __GAIA_LIST = window.__GAIA_LIST__ || [];


  const APP_STATE = {
    domain: null,
    user_id: null,
    last_results: [],
    last_query: '',
    usage_tracker: null,
    plan : 'free',
    client_id: window.__client__ || null,
  };

  /* ----------------------
     Utils
     ---------------------- */
  const utils = (function () {
    async function safe_fetch(url, opts = {}, timeout = 10000) {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), timeout);
      opts.signal = controller.signal;
      try {
        const res = await fetch(url, opts);
        clearTimeout(id);
        const text = await res.text().catch(() => '');
        const ct = res.headers.get('content-type') || '';
        if (!res.ok) {
          const err = new Error(`HTTP ${res.status}`);
          err.status = res.status;
          err.body = text;
          throw err;
        }
        if (ct.includes('application/json')) return JSON.parse(text || '{}');
        return text;
      } catch (err) {
        clearTimeout(id);
        throw err;
      }
    }

    function normalize_id_list(value) {
      if (!value) return [];

      if (Array.isArray(value)) return value;

      if (typeof value === "string") {
        return value
          .split(",")
          .map(v => v.trim())
          .filter(Boolean);
      }

      return [];
    }

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

    function escape_html(s) {
      return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    return { normalize_id_list, safe_fetch, el, show_toast, escape_html };
  })();

  /* ----------------------
     API module
     ---------------------- */
  const api = (function (u) {
    async function get_domain() {
      try {
        const data = await u.safe_fetch('/api/binder/get_domain', { method: 'GET' });
        if (data && (typeof data.data === 'string' || typeof data.domain === 'string')) {
          return data.data || data.domain;
        }
      } catch (err) {
        // propagate to caller
      }
      return null;
    }

    async function get_user(){
      const url = `/api/auth/me`;
      const data = await u.safe_fetch(url, { method: 'GET' });
      return data.data;    
    }

    async function get_user_id(){
      user = await get_user();
      return user.id;    
    }

    async function search(query, opts = {}) {
      const body = { query, user_id:APP_STATE.user_id, ...opts };
      res= await u.safe_fetch(API_SEARCH, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      return res;
    }

    async function get_client(id) {
      out = u.safe_fetch(API_GET_CLIENT(id), { method: 'GET' });
      return out
    }

    async function patch_client(id, updates) {
      return u.safe_fetch(API_PATCH_CLIENT(id), {
        method: 'PATCH',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ patch: updates , user_id:APP_STATE.user_id , domain:APP_STATE.domain })
      });
    }

    async function load_clients_by_ids(ids) {
      if (!Array.isArray(ids) || ids.length === 0) return [];

      const requests = ids.map(id =>
        api.get_client(id)
          .then(res => res?.status === 'success' ? res.data : null)
          .catch(() => null)
      );

      const results = await Promise.all(requests);
      return results.filter(Boolean);
    }

    async function track_time(payload) {
      // best-effort
      try {
        await u.safe_fetch(TRACK_ENDPOINT, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(payload)
        });
      } catch (e) { /* ignore */ }
    }

    /**
     * get_plan_status
     * Returns { days: number, plan: string } or null.
     */
    async function get_plan_status() {
      try {
        const data = await u.safe_fetch('/api/binder/get_plan_status', { method: 'GET' });
        // expected shape: { data: { days: N, plan: 'x' } } or { days: N, plan: 'x' }
        if (!data) return null;
        const payload = data.data || data;
        return { days: Number(payload.days || 0), plan: payload.plan || null };
      } catch (err) {
        return null;
      }
    }

    return { load_clients_by_ids,get_plan_status , search, get_client, patch_client, track_time , get_user_id , get_user , get_domain  };
  })(utils);

  /* ----------------------
     UI module
     ---------------------- */
  const ui = (function (u) {
    const results_el = u.el('results');

    function clear() { results_el.innerHTML = ''; }

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

    function render_client_detail(patient) {
      clear();
      const el = results_el;

      if (!patient) {
        utils.show_toast("Client not found", "error");
        return;
      }

      const labels = [
        { key: 'name', text: 'Patient Name' },
        { key: 'gov_id', text: 'ID Number' },
        { key: 'phone', text: 'Phone Number' },
        { key: 'location', text: 'Location' },
        { key: 'pmh', text: 'Medical History' },
        { key: 'allergies', text: 'Allergies' },
        { key: 'age', text: 'Age' },
        { key: 'next', text: 'Next visit' },
        { key: 'btype', text: 'Blood Type' },
        { key: 'sex', text: 'Sex' },
        { key: 'payed', text: 'Paid' },
        { key: 'debit', text: 'Debit' },
        { key: 'notes', text: 'Notes' }
      ];

      const panel = document.createElement('div');
      panel.className = 'patient-card decorative-card';
      panel.style.padding = "20px";

      const grid = document.createElement('div');
      grid.className = 'patient-info-grid';

      labels.forEach(lbl => {
        const wrap = document.createElement('div');

        const l = document.createElement('div');
        l.className = 'patient-label';
        l.textContent = lbl.text + ':';

        const input = document.createElement('input');
        input.className = 'patient-value';
        input.setAttribute('data-key', lbl.key);

        if (lbl.key === 'next') {
          input.type = 'datetime-local';
          input.value = patient.next || new Date().toISOString().slice(0, 16);
        }else {
          input.type = 'text';
          input.value = patient[lbl.key] || '';
        }

        if (APP_STATE.plan !== "sec" || ! ["payed" , "debit"].includes(lbl.key)){
          wrap.appendChild(l);
          wrap.appendChild(input);
          grid.appendChild(wrap);
        }
      });

      const btnRow = document.createElement('div');
      btnRow.style.display = 'flex';
      btnRow.style.gap = '10px';
      btnRow.style.marginTop = '16px';

      if (APP_STATE.plan === "sec"){
        btnRow.innerHTML = `
          <button class="big-btn btn-primary" id="save_btn">Save</button>
          <button class="big-btn btn-ghost" id="back_btn">Back</button>
        `;
      }else{
        btnRow.innerHTML = `
        <button class="big-btn btn-primary" id="save_btn">Save</button>
        <button class="big-btn btn-primary" id="open_btn">Open</button>
        <button class="big-btn btn-ghost" id="back_btn">Back</button>
      `;
      }
      
      panel.appendChild(grid);
      panel.appendChild(btnRow);
      el.appendChild(panel);

      document.getElementById('back_btn').addEventListener('click', () => controller.render_last());
      document.getElementById('save_btn').addEventListener('click', () => controller.save_client(patient.id, collectPatientValues()));
      document.getElementById('open_btn').addEventListener('click', () => controller.open_client(parseInt(patient.id)+1));
    }

    function collectPatientValues() {
      const inputs = results_el.querySelectorAll('[data-key]');
      const data = {};
      inputs.forEach(i => {
        const key = i.dataset.key;
        data[key] = i.value;
      });
      return data;
    }


   function render_list(list) {
    clear();
    const el = results_el;

    if (!list || list.length === 0) {
      const no = document.createElement('div');
      no.className = 'patient-card decorative-card';
      no.textContent = 'No patients found.';
      el.appendChild(no);
      return;
    }

    list.forEach(patient => {
      const card = document.createElement('div');
      card.className = 'patient-card decorative-card';
      card.innerHTML = `
        <div class="patient-row" style="justify-content:space-between;">
          <div>
            <div style="font-weight:800; font-size:1.05rem;">${patient.name || '—'}</div>
            <div style="color:rgba(0,0,0,0.6); margin-top:6px;">
              ID: ${parseInt(patient.id) || '—'} • Age: ${patient.age || '—'}
            </div>
          </div>
          <div style="text-align:right;">
            <button 
              class="big-btn btn-secondary" 
              style="min-width:110px;" 
              data-id="${patient.id}"
            >
              Open
            </button>
          </div>
        </div>
      `;
      el.appendChild(card);
    });

    el.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', ev => controller.view_client(ev.target.dataset.id));
    });
  }
  return { clear, menu_init, render_list , render_client_detail };

  })(utils)

  /* ----------------------
     Usage tracker (single final send)
     ---------------------- */
  function start_usage_tracker(endpoint) {
    let seconds = 0;
    let active = true;
    document.addEventListener('visibilitychange', () => { active = !document.hidden; });
    window.addEventListener('focus', () => active = true);
    window.addEventListener('blur', () => active = false);

    const id = setInterval(() => { if (active) seconds += 1; }, 1000);

    function send_final() {
      if (seconds < 1) return;
      try {
        navigator.sendBeacon(endpoint, JSON.stringify({ seconds }));
      } catch (e) {
        // best-effort fallback
        fetch(endpoint, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ seconds }) }).catch(()=>{});
      } finally {
        clearInterval(id);
      }
    }
    window.addEventListener('beforeunload', send_final);
    return { get_seconds: () => seconds, flush: send_final };
  }

  /* ----------------------
     Controller
     ---------------------- */
  const controller = (function (api_mod, ui_mod, u_mod) {
    let last_results = [];
    async function init() {
      APP_STATE.user_id =  await api_mod.get_user_id();
      APP_STATE.domain = await api_mod.get_domain();
      let res = await api_mod.get_plan_status();
      APP_STATE.plan = res.plan;
      ui_mod.menu_init();
      // wire UI
      u_mod.el('search_btn').addEventListener('click', () => do_search());
      u_mod.el('query_input').addEventListener('keydown', (e) => { if (e.key === 'Enter') do_search(); });

      // start usage tracker
      APP_STATE.usage_tracker = start_usage_tracker(TRACK_ENDPOINT);

      // auto-render if server injected data
      try {
        if (APP_STATE.client_id) {
          const resp = await api_mod.get_client(APP_STATE.client_id);
          u_mod.el('query_input').value = APP_STATE.client_id;
          if (resp && resp.status === 'success') ui_mod.render_client_detail(resp.data);
        }
        if (__GAIA_LIST.length >0) {
          const ids = utils.normalize_id_list(__GAIA_LIST);

          if (ids.length > 0) {
            const clients = await api.load_clients_by_ids(ids);
            APP_STATE.last_results = clients;
            ui_mod.render_list(clients);
          }

        }
      } catch (err) { console.debug('auto render error', err); }
    }

    async function do_search() {
      const q = (u_mod.el('query_input').value || '').trim();
      if (!q) { u_mod.show_toast('Please enter a query', 'info'); return; }
      APP_STATE.last_query = q;
      try {
        const payload = {};
        if (APP_STATE.domain) payload.domain = APP_STATE.domain;
        if (APP_STATE.user_id) payload.user_id = APP_STATE.user_id;

        const res = await api_mod.search(q, payload);
        if (!res || res.status !== 'success') {
          u_mod.show_toast(res?.message || 'Search failed', 'error');
          return;
        }

        last_results = Object.entries(res.data).map(([id, p]) => ({
          id: p.id,
          gov_id: p.gov_id,
          name: p.name,
          age: p.age,
          phone: p.phone,
          pmh: p.pmh,
          allergies: p.allergies,
          location: p.location,
          sex: p.sex,
          debit: p.debit,
          payed: p.payed,
          next: p.next,
          btype: p.btype,
          notes: p.notes
        }));

        APP_STATE.last_results = last_results;
        ui_mod.render_list(last_results);
      } catch (err) {
        console.error('search error', err);
        u_mod.show_toast('Search request failed', 'error');
      }
    }

    async function view_client(id) {
      // for quick-view we can open client detail using get_client
      try {
        const res = await api_mod.get_client(id);
        if (!res || res.status !== 'success') { u_mod.show_toast(res?.message || 'Failed to load', 'error'); return; }
        ui_mod.render_client_detail(res.data);
      } catch (err) {
        console.error('view error', err);
        u_mod.show_toast('Failed to load client', 'error');
      }
    }

    async function open_client(id) { 
      window.location.href = API_OPEN_CLIENT(id);
    }

    async function save_client(id, updates) {
      try {
        const res = await api_mod.patch_client(id, updates);
        if (!res || res.status !== 'success') throw new Error(res?.message || 'save failed');
        return res.data;
      } catch (err) {
        console.error('save client error', err);
        throw err;
      }
    }

    function render_last() {
      ui_mod.render_list(APP_STATE.last_results || []);
    }

    return { init, do_search, view_client, open_client, save_client, render_last };
  })(api, ui, utils);

  // bootstrap
  document.addEventListener('DOMContentLoaded', () => controller.init());
  