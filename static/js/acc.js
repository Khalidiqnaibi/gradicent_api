
  /**
   * account_page.js (single-file modular structure)
   * ------------------------------------------------
   * Single HTML file with embedded JS structured as small modules:
   * - utils: helpers (time, dom)
   * - api: network calls (binder/gaia)
   * - ui: menu and toast components
   * - controller: page initialization and wiring
   *
   * Conventions:
   * - snake_case function and variable names
   * - small functions (aim <= 30 lines)
   * - explicit APP_STATE object (no hidden state)
   */

  /* =========================
     Constants & Explicit State
     ========================= */
  const API_TIMEOUT_MS = 10_000;
  const POLL_TRACK_INTERVAL_MS = 60_000;

  /**
   * APP_STATE is explicit single source of truth for this page.
   * This avoids hidden / implicit state and makes testing easier.
   */
  const APP_STATE = {
    user_name: null,
    plan: null,
    days_left: 0,
    domain: null, // e.g., 'medical' | 'lab'
    btn1_href: '/api/auth/signout',
    btn2_href: '/login'
  };


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
     * Wrapper around fetch that adds a timeout and throws on non-OK.
     * @param {string} url
     * @param {object} opts
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

    return { iso_today, safe_fetch };
  })();

  /* =========================
     API Module (Binder / Gaia)
     ========================= */
  const api = (function (u) {
    /**
     * get_user_id
     * Fetches current user ID from /api/auth/me.
     */

    async function get_user(){
      const url = `/api/auth/me`;
      const data = await u.safe_fetch(url, { method: 'GET' });
      return data.data;    
    }

    async function get_user_id(){
      user = await get_user();
      return user.id;    
    }

    /**
     * get_appointments_for_date
     * Fetch appointments from server for given date (YYYY-MM-DD).
     * Returns an array.
     */
    async function get_appointments_for_date(date_iso, domain, user_id) {
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
     * get_patients_count(total_customers)
     * Uses Gaia compute endpoint that returns { patient_count: number }.
     */
    async function get_patients_count(user_id,domain) {
      const url = `/api/gaia/compute?metric=total_customers&domain=${encodeURIComponent(domain)}&user_id=${encodeURIComponent(user_id)}`;
      const data = await u.safe_fetch(url, { method: 'GET' });
      if (data && typeof data.total_customers === 'number') return data.total_customers;
      // some older responses may embed in data.data
      if (data && data.data && typeof data.data.total_customers === 'number') return data.data.total_customers;
      return 0;
    }

    /**
     * get_domain
     * Returns domain string (e.g., 'medical' or 'lab').
     */
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

    return { get_appointments_for_date, get_patients_count, get_domain, get_plan_status ,get_user_id,get_user};
  })(utils);

  /* =========================
     UI Module (toast + menu)
     ========================= */
  const ui = (function () {
    const TOAST_CONTAINER_ID = 'toast_container';

    /**
     * create_toast
     * Small, reusable toast implementation.
     * type: 'info' | 'success' | 'error'
     */
    function create_toast(message, type = 'info') {
      const container = document.getElementById(TOAST_CONTAINER_ID);
      if (!container) return;

      const el = document.createElement('div');
      el.className = `toast toast-${type}`;
      el.setAttribute('role', 'status');
      el.setAttribute('aria-live', 'polite');
      el.innerHTML = `<span>${escape_html(String(message))}</span>`;

      container.appendChild(el);
      setTimeout(() => el.remove(), 4000);
    }

    /**
     * escape_html
     * Minimal escaping to avoid accidental HTML injection in toasts.
     */
    function escape_html(str) {
      return str.replace(/[&<>"']/g, (c) => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[c]);
    }

    /**
     * menu_init
     * Wire menu toggle and ARIA updates.
     */
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

    return { create_toast, menu_init };
  })();

  /* =========================
     Controller (page wiring)
     ========================= */
  (function controller(api_mod, ui_mod, utils_mod) {
    /**
     * wire_buttons
     * Attach behaviour to primary buttons. Keeps logic explicit.
     */
    function wire_buttons() {
      const btn1 = document.getElementById('btn1');
      const btn2 = document.getElementById('btn2');
      if (btn1) btn1.addEventListener('click', () => { window.location.href = APP_STATE.btn1_href; });
      if (btn2) btn2.addEventListener('click', () => { window.location.href = APP_STATE.btn2_href; });
    }

    /**
     * render_plan_status
     * Update plan badge and trial text.
     */
    function render_plan_status(days, plan) {
      const plan_badge = document.getElementById('plan_badge');
      const trial_days = document.getElementById('trial_days');

      if (!plan_badge || !trial_days) return;

      if (Number(days) > 0) {
        plan_badge.innerHTML = '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg><span class="ml-1">Trial</span>';
        trial_days.textContent = `${days} day${days > 1 ? 's' : ''} left`;
      } else {
        plan_badge.innerHTML = '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3"/></svg><span class="ml-1">Active</span>';
        trial_days.textContent = 'No trial';
      }
    }

    /**
     * render_user_header
     * Update main header text and message.
     */
    function render_user_header(name, plan) {
      const hello = document.getElementById('hello');
      const msg = document.getElementById('msg');
      if (hello) hello.textContent = name ? `Welcome, ${name}` : 'Welcome';
      if (msg) msg.textContent = plan ? `Plan: ${plan}` : 'Thank you for supporting us';
    }

    /**
     * update_counts
     * Set counts on the page.
     */
    function update_counts(patients_count, appointments_count) {
      const pat_el = document.getElementById('patients_count');
      const app_el = document.getElementById('appointments_count');
      if (pat_el) pat_el.textContent = String(patients_count ?? 0);
      if (app_el) app_el.textContent = String(appointments_count ?? 0);
    }

    /**
     * load_and_render_counts
     * Fetch counts and update UI. Errors are surfaced to the user via toasts.
     */
    async function load_and_render_counts() {
      
      try {
        const user_id = await api_mod.get_user_id();
        const date_iso = utils_mod.iso_today();
        const [appointments, patients_count] = await Promise.allSettled([
          api_mod.get_appointments_for_date(date_iso,APP_STATE.domain,user_id),
          api_mod.get_patients_count(user_id,APP_STATE.domain)
        
        ]);

        const appointments_list = (appointments.status === 'fulfilled') ? (appointments.value || []) : [];
        if (appointments.status === 'rejected') {
          console.error('appointments error', appointments.reason);
          ui_mod.create_toast('Failed to load appointments', 'error');
        }

        const patient_count_value = (patients_count.status === 'fulfilled') ? (patients_count.value || 0) : 0;
        if (patients_count.status === 'rejected') {
          console.error('patients_count error', patients_count.reason);
          ui_mod.create_toast('Failed to load patients count', 'error');
        }
        update_counts(Number(patient_count_value), Array.isArray(appointments_list) ? appointments_list.length : 0);
      } catch (err) {
        console.error('load_and_render_counts', err);
        ui_mod.create_toast('Unexpected error while loading counts', 'error');
        update_counts(0, 0);
      }
    }

    /**
     * customize_for_binder_type
     * Applies binder-specific UI changes (example: lab).
     */
    function customize_for_binder_type(binder_type) {
      if (!binder_type) return;
      if (binder_type === 'lab') {
        const appa = document.getElementById('appa');
        const appimg = document.getElementById('appimg');
        const apph6 = document.getElementById('apph6');
        const link = document.querySelector("link[rel~='icon']");

        if (appa) { appa.title = 'Search Lab'; appa.href = '/srchlab'; }
        if (appimg) appimg.src = '/static/images/srchlab.png';
        if (apph6) apph6.textContent = 'Search Lab';
        if (link) link.href = '/static/images/binderlab.jpg';
        document.title = 'Binder Laboratory';
      }
    }

    

    /**
     * init
     * Main entrypoint for the page.
     * Loads plan + domain, wires UI, then fetches counts.
     */
    async function init() {
      try {
        const usage = startUsageTracker("/api/binder/track_time");
        ui_mod.menu_init();
        wire_buttons();

        // Prefetch plan and domain concurrently
        const [plan_res, domain_res] = await Promise.allSettled([
          api_mod.get_plan_status(),
          api_mod.get_domain()
        ]);

        const plan_payload = (plan_res.status === 'fulfilled' && plan_res.value) ? plan_res.value : { days: 0, plan: null };
        const domain_payload = (domain_res.status === 'fulfilled') ? domain_res.value : null;

        // Persist to explicit app state
        APP_STATE.days_left = Number(plan_payload.days || 0);
        APP_STATE.plan = plan_payload.plan || null;
        APP_STATE.domain = domain_payload || null;

        // render header and plan
        render_plan_status(APP_STATE.days_left, APP_STATE.plan);
        render_user_header(APP_STATE.user_name, APP_STATE.plan);

        // apply binder customizations (lab variant etc.)
        customize_for_binder_type(APP_STATE.domain);

        // set default button hrefs (can be overridden by other flows)
        APP_STATE.btn1_href = '/logout';
        APP_STATE.btn2_href = '/logme';

        // initial load
        await load_and_render_counts();
      } catch (err) {
        console.error('init error', err);
        ui_mod.create_toast('Failed to initialize user data', 'error');
      }
    }

    // start when DOM is ready
    document.addEventListener('DOMContentLoaded', init);
  })(api, ui, utils);