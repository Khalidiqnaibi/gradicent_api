
  /**
   * appointments_page.js
   * --------------------
   * Single-file modular structure:
   * - utils: helpers (time, dom, safe_fetch)
   * - api: network calls (binder)
   * - ui: toasts + menu wiring
   * - controller: page wiring and rendering
   *
   * Conforms to company standards:
   * - snake_case naming
   * - small functions (<= ~30 lines)
   * - explicit APP_STATE
   * - doc-comments explaining what each exported function does
   */

  /* =========================
     Constants & Explicit State
     ========================= */
  const API_TIMEOUT_MS = 10_000;
  const APP_STATE = {
    current_user_id: null,
    current_domain: 'medical',
    appointments: []
  };

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

  /* =========================
     Utils Module
     ========================= */
  const utils = (function () {
    /**
     * iso_today
     * Return today's date in YYYY-MM-DD according to local timezone.
     */
    function iso_today() {
      const now = new Date();
      const tz_offset_ms = now.getTimezoneOffset() * 60000;
      return new Date(now.getTime() - tz_offset_ms).toISOString().slice(0, 10);
    }

    /**
     * safe_fetch
     * Fetch wrapper with timeout and JSON handling.
     */
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
          err.status = res.status; err.body = text;
          throw err;
        }
        const ct = (res.headers.get('content-type') || '');
        if (ct.includes('application/json')) return res.json();
        return res.text();
      } catch (err) {
        clearTimeout(timeout);
        throw err;
      }
    }

    /**
     * el
     * Shorthand for document.getElementById
     */
    function el(id) { return document.getElementById(id); }

    return { iso_today, safe_fetch, el };
  })();

  /* =========================
     API Module
     ========================= */
  const api = (function (u) {
    /**
     * get_user
     * Fetch current user object from backend.
     * Returns user payload { id, domain, ... } or throws.
     */
    async function get_user() {
      const url = '/api/auth/me';
      const data = await u.safe_fetch(url, { method: 'GET' });
      return data.data || data;
    }

    /**
     * get_appointments_for_date
     * Attempts a few endpoint shapes to be robust.
     * Returns an array of appointment objects.
     */
    async function get_appointments_for_date(date_iso, domain, user_id) {
      APP_STATE.current_date_iso = u.el('date_input').value;
      const url = `/api/binder/appointments/${encodeURIComponent(date_iso)}?domain=${encodeURIComponent(domain)}&user_id=${encodeURIComponent(user_id)}`;

      try {
        const res = await u.safe_fetch(url, { method: 'GET' });
        // Return appointments array
        return res.data.appointments || [];
      } catch (err) {
        console.warn('get_appointments_for_date attempt failed', err);
        ui.create_toast('Failed to load appointments', 'error');
        return [];
      }
    }


    /**
     * save_appointments
     * PATCH appointments payload for date.
     */
    async function save_appointments(date_iso, appointments, domain, user_id) {
      const url = `/api/binder/appointments/${encodeURIComponent(date_iso)}?domain=${encodeURIComponent(domain)}&user_id=${encodeURIComponent(user_id)}`;
      return await u.safe_fetch(url, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appointments })
      });
    }

    /**
     * lock_appointment
     * POST to lock appointment by number.
     */
    async function lock_appointment(no, domain, date_iso, user_id) {
      const url = `/api/binder/appointments/lock`;
      return await u.safe_fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ no, user_id, date: date_iso, domain }) 
      });
    }


    return { get_user, get_appointments_for_date, save_appointments, lock_appointment };
  })(utils);

  /* =========================
     UI Module
     ========================= */
  const ui = (function (u) {
    const TOAST_CONTAINER_ID = 'toast_container';

    /**
     * create_toast
     * Show a toast message. type: 'info'|'success'|'error'
     */
    function create_toast(message, type = 'info') {
      const container = u.el(TOAST_CONTAINER_ID);
      if (!container) return;
      const el = document.createElement('div');
      el.className = `toast toast-${type}`;
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      el.textContent = message;
      container.appendChild(el);
      setTimeout(() => el.remove(), 3500);
    }

    /**
     * menu_init
     * Wire menu toggle interactions.
     */
    function menu_init() {
      const menuBtn = document.querySelector('.hamburger-menu');
      const menuBar = document.getElementById('menuBar');
      if (!menuBtn || !menuBar) return;
      menuBtn.addEventListener('click', () => {
        menuBar.classList.toggle('menu-active');
      });
      document.addEventListener('click', (ev) => {
        if (!menuBar.contains(ev.target) && menuBar.classList.contains('menu-active')) {
          menuBar.classList.remove('menu-active');
        }
      });
    }

    return { create_toast, menu_init };
  })(utils);

  /* =========================
     Rendering Helpers
     ========================= */

  /**
   * render_slot
   * Build DOM element for a single appointment.
   * Keeps function small and focused (single responsibility).
   */
  function render_slot(a) {
    const slot = document.createElement('div');
    slot.className = 'slot';

    slot.innerHTML = `
      <div>
        <h3>${escape_html(a.name || 'Unknown')}</h3>
        <p class="muted">No. ${escape_html(String(a.no || ''))}</p>
      </div>
      <div class="text-sm muted">${escape_html(String(a.no || ''))}</div>
      <div class="text-sm muted">${escape_html(a.phone || '')}</div>
      <div><textarea class="input" style="min-height:70px;">${escape_html(a.msg || '')}</textarea></div>
      <div class="flex flex-col gap-2">
        <button class="btn-ghost show">Show</button>
        <button class="btn-ghost lock">Lock</button>
      </div>
    `;

    // textarea binding
    const ta = slot.querySelector('textarea');
    ta.addEventListener('input', (e) => { a.msg = e.target.value; });

    // show button
    slot.querySelector('.show').addEventListener('click', () => {
      window.location.href = `/show_search_by_number/${encodeURIComponent(a.no)}`;
    });

    // lock button
    slot.querySelector('.lock').addEventListener('click', async () => {
    try {
      await api.lock_appointment(
        a.no,
        APP_STATE.current_domain,
        APP_STATE.current_date_iso, // will now be sent as 'date'
        APP_STATE.current_user_id
      );
      ui.create_toast('Locked', 'success');
    } catch (err) {
      console.error('lock error', err);
      ui.create_toast('Failed to lock', 'error');
    }
  });


    return slot;
  }

  /**
   * escape_html
   * Small helper to avoid accidental injection when inserting text into innerHTML.
   */
  function escape_html(str) {
    if (!str && str !== 0) return '';
    return String(str).replace(/[&<>"']/g, (c) => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[c]);
  }

  /* =========================
     Controller (page wiring)
     ========================= */
  (function controller(api_mod, ui_mod, utils_mod) {

    const el = utils_mod.el;

    /**
     * render
     * Render appointments list according to selected filter.
     */
    function render() {
      const list = el('list');
      const empty = el('empty');
      const filter = el('filter').value;
      list.innerHTML = '';

      const filtered = APP_STATE.appointments.filter(a => {
        const has = (a.msg || '').trim().length > 0;
        if (filter === 'has') return has;
        if (filter === 'none') return !has;
        return true;
      });

      el('count').textContent = String(filtered.length);

      if (filtered.length === 0) {
        empty.classList.add('visible');
        return;
      }
      empty.classList.remove('visible');

      for (const a of filtered) {
        const slot = render_slot(a);
        list.appendChild(slot);
      }
    }

    /**
     * load_appointments
     * Loads appointments for given date and update state.
     */
    async function load_appointments(date_iso) {
      try {
        const arr = await api_mod.get_appointments_for_date(date_iso, APP_STATE.current_domain, APP_STATE.current_user_id);
        // normalize shape: ensure objects and msg default
        APP_STATE.appointments = (Array.isArray(arr) ? arr : []).map(x => Object.assign({}, x, { msg: x.msg || '' }));
        render();
        ui_mod.create_toast('Loaded', 'success');
      } catch (err) {
        console.error('load error', err);
        APP_STATE.appointments = [];
        render();
        ui_mod.create_toast('Failed to load appointments', 'error');
      }
    }

    /**
     * save_appointments
     * Persist APP_STATE.appointments to server for the date.
     */
    async function save_appointments() {
      const date_iso = el('date_input').value;
      try {
        await api_mod.save_appointments(date_iso, APP_STATE.appointments, APP_STATE.current_domain, APP_STATE.current_user_id);
        ui_mod.create_toast('Saved', 'success');
        // reload to get any server-side normalization
        await load_appointments(date_iso);
      } catch (err) {
        console.error('save error', err);
        ui_mod.create_toast('Failed to save', 'error');
      }
    }

    /**
     * wire_buttons
     * Attach event handlers for page controls.
     */
    function wire_buttons() {
      el('refresh').addEventListener('click', () => load_appointments(el('date_input').value));
      el('save').addEventListener('click', save_appointments);
      el('filter').addEventListener('change', render);
      el('clear').addEventListener('click', () => {
        APP_STATE.appointments.forEach(a => a.msg = '');
        render();
        ui_mod.create_toast('Cleared (local)', 'info');
      });
    }

    /**
     * init
     * Entry point: get user, set defaults, load initial appointments.
     */
    async function init() {
      try {
        ui_mod.menu_init();
        wire_buttons();
        startUsageTracker("/api/binder/track_time");
        // get current user
        const user = await api_mod.get_user();
        APP_STATE.current_user_id = user.id;
        APP_STATE.current_domain = user.domain || 'medical';

        // set date to today
        el('date_input').value = utils_mod.iso_today();

        // initial load
        await load_appointments(el('date_input').value);
      } catch (err) {
        console.error('init error', err);
        ui_mod.create_toast('Failed to initialize page', 'error');
      }
    }

    // start when DOM is ready
    document.addEventListener('DOMContentLoaded', init);

  })(api, ui, utils);
 