    /**
     * stats.js — Analytics Dashboard
     * ------------------------------
     * Four tabs: ROI, Productivity, Finance, Clients.
     *
     * Plan gating:
     *   - "roi" and "productivity" tabs are available on ALL plans.
     *   - "finance" and "clients" tabs require "pro" or "ultra" plan.
     *   - On "starter" / "free" plans the finance & clients tab buttons
     *     are hidden entirely.
     *   - Non-pro users see a "upgrade to pro" overlay if they reach
     *     a gated tab via direct navigation.
     *
     * Charts:
     *   Uses Chart.js. Charts are cached in the `charts` object so
     *   switching tabs reuses the same canvas instead of re-creating.
     *   Colors are pulled from CSS variables (--secondary, --accent).
     *
     * client_list:
     *   Populated by the finance/clients API response. Used to
     *   navigate to a search-by-clients page via show_clients().
     */

    const APP_STATE = {
        plan: null,
        domain: null, // e.g., 'medical' | 'lab'
        user_id: null
      };
    const THEME_KEY = 'gradicent_theme';
    var client_list = []

    function getTheme() {
      const stored = localStorage.getItem(THEME_KEY);
      if (stored === 'dark' || stored === 'light') return stored;
      return 'dark';
    }

    function applyTheme(theme) {
      const resolved = theme === 'light' ? 'light' : 'dark';
      document.body.classList.toggle('theme-dark', resolved === 'dark');
      document.documentElement.setAttribute('data-theme', resolved);

      const toggleBtn = document.getElementById('sidebar-theme-toggle');
      if (toggleBtn) {
        toggleBtn.setAttribute('title', resolved === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
        toggleBtn.setAttribute('aria-pressed', String(resolved === 'dark'));
        const icon = toggleBtn.querySelector('svg path');
        if (icon) {
          const iconPath = resolved === 'dark'
            ? 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.364 6.364l-1.414-1.414M7.05 7.05 5.636 5.636m12.728 0-1.414 1.414M7.05 16.95l-1.414 1.414M12 8a4 4 0 100 8 4 4 0 000-8z'
            : 'M21 12.79A9 9 0 1111.21 3c-.07.32-.11.65-.11 1a9 9 0 009.9 8.79z';
          icon.setAttribute('d', iconPath);
        }
      }
    }

    function setTheme(theme) {
      const resolved = theme === 'light' ? 'light' : 'dark';
      localStorage.setItem(THEME_KEY, resolved);
      applyTheme(resolved);
      return resolved;
    }

    function toggleTheme() {
      const next = getTheme() === 'dark' ? 'light' : 'dark';
      setTheme(next);
      reloadCurrentTab();
    }

    function setClientsButtonVisible(show) {
      const clientsEl = document.getElementById("clients");
      if (clientsEl) clientsEl.style.display = show ? "block" : "none";
    }
      
    document.addEventListener("DOMContentLoaded", async function() {
      applyTheme(getTheme());

      // Sidebar controls (must be attached before any async operations)
      const menuToggle = document.getElementById('menu-toggle');
      const overlay = document.getElementById('sidebar-overlay');
      const themeToggle = document.getElementById('sidebar-theme-toggle');
      if (menuToggle) menuToggle.addEventListener('click', StatsPage.toggleSidebar);
      if (overlay) overlay.addEventListener('click', StatsPage.closeSidebar);
      if (themeToggle) themeToggle.addEventListener('click', toggleTheme);

      const clientsEl = document.getElementById("clients");
      setClientsButtonVisible(false);

      const usage = startUsageTracker("/api/binder/track_time");
      APP_STATE.user_id = await api.get_user_id();
      APP_STATE.domain = await api.get_domain();
      let res = await api.get_plan_status();
      APP_STATE.plan = res?.plan || "free";

      if (["starter","free"].includes(APP_STATE.plan)){
        const financeTab = document.querySelector('.tab-btn[data-tab="finance"]');
        const clientsTab = document.querySelector('.tab-btn[data-tab="clients"]');
        if (financeTab) financeTab.style.display = 'none';
        if (clientsTab) clientsTab.style.display = 'none';
      }
      

      if (clientsEl) {
        clientsEl.addEventListener("click", function (event) {
          event.preventDefault();
          show_clients();
        });
      }

      
      setFiltersToLastWeek();
      // prefer to show ROI tab on load
      currentTab = 'roi';
      // ensure UI tab button is active
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active-tab'));
      const activeBtn = document.querySelector('.tab-btn[data-tab="roi"]');
      if (activeBtn) activeBtn.classList.add('active-tab');
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
      document.getElementById('tab-roi').classList.remove('hidden');

      loadTab('roi');

    });

    // ===== Utilities =====
    const u = (function(){
      async function safe_fetch(url, options={}) {
        try {
          const res = await fetch(url, options);
          if (!res.ok) {
            const text = await res.text();
            throw new Error(`Fetch error ${res.status}: ${text}`);
          }
          const data = await res.json();
          return data;
        } catch (err) {
          console.error('safe_fetch error:', err);
          throw err;
        }
      }
      return { safe_fetch };
    })();

    const api = (function(u) {
      async function get_user(){
        const url = `/api/auth/me`;
        const data = await u.safe_fetch(url, { method: 'GET' });
        return data.data;    
      }

      async function get_user_id(){
        const user = await get_user();
        return user.id;    
      }

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
      return { get_plan_status, get_user, get_user_id, get_domain };
    })(u);  
    
    function show_clients() {
      const safeClients = Array.isArray(client_list) ? client_list : [];
      window.location.href = `/search_stats?clients=${encodeURIComponent(JSON.stringify(safeClients))}`;
    }

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

    function hexToRgba(hex, alpha=1) {
      if (!hex) return `rgba(0,0,0,${alpha})`;
      const h = hex.replace('#','').trim();
      const bigint = parseInt(h.length === 3 ? h.split('').map(ch=>ch+ch).join('') : h, 16);
      const r = (bigint >> 16) & 255;
      const g = (bigint >> 8) & 255;
      const b = bigint & 255;
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    // ===== Utilities =====
    const fmtMoney = v => typeof v === 'number' ? '$' + v.toFixed(2) : v;

    function formatDateInput(d) {
      // returns YYYY-MM-DD using local date parts
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}`;
    }

    // read CSS variable
    function getCssVar(name, fallback = '') {
      const val = getComputedStyle(document.documentElement).getPropertyValue(name);
      return (val || fallback).trim();
    }

    // build a gradient from any 2d context and a hex color
    function makeGradientFromCtx(ctx, hex) {
      const g = ctx.createLinearGradient(0, 0, 0, 220);
      g.addColorStop(0, hexToRgba(hex, 0.92));
      g.addColorStop(1, hexToRgba(hex, 0.08));
      return g;
    }

    // ===== Default filter object (will be set to last 7 days) =====
    const filters = { from: null, to: null};

    // set date inputs to last 7 days and update filters
    function setFiltersToLastWeek() {
      const today = new Date();
      const to = new Date(today.getFullYear(), today.getMonth(), today.getDate()); // midnight local
      const from = new Date(to);
      from.setDate(to.getDate() - 6); // include today => 7 days total (from .. to)
      const fromStr = formatDateInput(from);
      const toStr = formatDateInput(to);
      filters.from = fromStr;
      filters.to = toStr;
      const dateFromEl = document.getElementById('dateFrom');
      const dateToEl = document.getElementById('dateTo');
      if (dateFromEl) dateFromEl.value = fromStr;
      if (dateToEl) dateToEl.value = toStr;
    }

    // wire form submit to update filters and reload
    const filtersForm = document.getElementById('filters');
    if (filtersForm) {
      filtersForm.addEventListener('submit', e=>{
        e.preventDefault();
        const f = document.getElementById('dateFrom').value;
        const t = document.getElementById('dateTo').value;
        filters.from = f || null;
        filters.to = t || null;
        
        reloadCurrentTab();
      });
    }

    // builds a query string only with present filters
    async function buildQsFromFilters() {
      if (!APP_STATE.domain || !APP_STATE.user_id) {
        APP_STATE.domain  = await api.get_domain();
        APP_STATE.user_id = await api.get_user_id();
      }
      const params = new URLSearchParams();
      if (filters.from) params.append('from', filters.from);
      if (filters.to) params.append('to', filters.to);
      if (APP_STATE.domain) params.append('domain', APP_STATE.domain);
      if (APP_STATE.user_id) params.append('user_id', APP_STATE.user_id);
      return params.toString();
    }

    async function fetchMetric(metric, extra = {}) {
      const qs = await buildQsFromFilters();
      const params = new URLSearchParams(qs);
      params.set('metric', metric);
      Object.entries(extra).forEach(([k, v]) => {
        if (v != null && v !== '') params.set(k, String(v));
      });

      const payload = await u.safe_fetch(`/api/gaia/compute?${params.toString()}`, { method: 'GET' });
      if (!payload || payload.status === 'error') {
        throw new Error(payload?.message || `Failed to fetch ${metric} metric`);
      }
      return payload.data || {};
    }

    // ===== Pro upgrade overlay =====
    function showProOverlay(panelId, title, description) {
      const panel = document.getElementById(panelId);
      if (!panel) return;
      panel.innerHTML = `
        <div class="pro-overlay">
          <div class="pro-icon">&#9733;</div>
          <div class="pro-title">${title}</div>
          <p class="pro-desc">${description}</p>
          <a href="/plan" class="pro-btn">Upgrade to Pro</a>
        </div>`;
    }

    // ===== Tabs wiring =====
    // loadTab() is called whenever a tab button is clicked.
    // The tab name ("roi", "productivity", "finance", "clients")
    // determines which API endpoint to call and which DOM panel to fill.
    document.querySelectorAll('.tab-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active-tab'));
        btn.classList.add('active-tab');
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-panel').forEach(p=>p.classList.add('hidden'));
        document.getElementById('tab-'+tab).classList.remove('hidden');
        currentTab = tab;
        loadTab(tab);
      });
    });
    let currentTab = 'roi';

    // ===== Charts cache =====
    let charts = {};
    function ensureChart(id, type, opts) {
      const el = document.getElementById(id);
      if (!el) return null;
      if (charts[id]) return charts[id];
      // Chart.js requires a canvas context
      const ctx = el.getContext('2d');
      charts[id] = new Chart(ctx, Object.assign({ type, data:{labels:[], datasets:[]}}, opts||{}));
      return charts[id];
    }

    // ===== Data loader for each tab =====
    // Plan gating logic:
    //   tbs = tabs available to ALL plans (roi, productivity)
    //   pln = plans that unlock ALL tabs (pro, ultra)
    //   If the tab is in tbs OR the user's plan is in pln, show data.
    //   Otherwise show the pro upgrade overlay.
    async function loadTab(tab) {
      let tbs = ["productivity" , "roi"];    // free-tier tabs
      let pln = ["pro" , "ultra"];           // plans that unlock everything
      
      if(tbs.includes(tab) || pln.includes(APP_STATE.plan) || tab === 'finance' || tab === 'clients'){
          let data = {};

        try {
            if (tab === 'roi') {
            setClientsButtonVisible(false);
            data = await fetchMetric('roi', { plan: APP_STATE.plan });
              document.getElementById('roi-hours').innerText = (data.hours_saved || 0).toFixed(2) + ' hrs';
            document.getElementById('roi-dollar').innerText = fmtMoney(data.roi || 0);
              document.getElementById('roi-payback').innerText = data.payback_period_hours ? data.payback_period_hours + ' hrs' : '—';
              const tasksEl = document.getElementById('roi-tasks'); tasksEl.innerHTML = '';
              
              const taskCounts = {};
              
              // Aggregate counts by type
              for (const [key, task] of Object.entries(data.tasks || {})) {
              const type = task.type;
              if (type) {
                taskCounts[type] = (taskCounts[type] || 0) + (task.count || 1);
              }
              }
              
              // Display each type once with its total count
              for (const [type, count] of Object.entries(taskCounts)) {
              const d = document.createElement('div');
              d.className = 'p-2 border rounded text-center';
              const inner = document.createElement('div');
              inner.className = 'text-sm';
              inner.textContent = type;
              d.appendChild(inner);
              
              const countEl = document.createElement('div');
              countEl.className = 'text-2xl font-semibold';
              countEl.innerText = count;
              d.appendChild(countEl);
              tasksEl.appendChild(d);
              }
            }

            if (tab === 'productivity') {
              setClientsButtonVisible(false);
              data = await fetchMetric('productivity');
              document.getElementById('prod-total-time').innerText = (data.total_time_minutes || 0) + ' mins';
              document.getElementById('prod-avg-session').innerText = (data.avg_time_per_session_minutes || 0) + ' mins';
              document.getElementById('prod-productive').innerText = (data.percent_productive || 0) + '%';
              document.getElementById('prod-visits-hour').innerText = (data.visits_per_active_hour || 0) + ' visits/hr';

              const ch = ensureChart('prod-time-vs-clients', 'line', { options: { responsive: true, maintainAspectRatio: false } });
              if (ch) {
                ch.data.labels = data.time_vs_clients?.labels || [];
                // make gradients using the chart's canvas context
                const ctx = ch.canvas.getContext('2d');
                const secondaryColor = getCssVar('--secondary', '#78cee6');
                const accentColor = getCssVar('--accent', '#ce7a35');
                const lineGradDebit = makeGradientFromCtx(ctx, secondaryColor);
                const lineGradPayed = makeGradientFromCtx(ctx, accentColor);

                ch.data.datasets = [
                  { label: 'Minutes', data: data.time_vs_clients?.minutes || [], borderWidth: 2,
                    borderColor: hexToRgba(secondaryColor, 1),
                    backgroundColor: lineGradDebit, fill: true },
                  { label: 'clients Added', data: data.time_vs_clients?.clients || [], borderWidth: 2,
                    borderColor: hexToRgba(accentColor, 1),
                    backgroundColor: lineGradPayed, fill: true }
                ];
                ch.update();
              }
            }

            if (tab === 'finance' && !["pro" , "ultra"].includes(APP_STATE.plan )){
              setClientsButtonVisible(false);
              showProOverlay('tab-finance', 'Finance Analytics', 'Finance metrics like revenue, outstanding balances, and trends are available on the Pro and Ultra plans.');
            }
            else if (tab === 'finance') {
              data = await fetchMetric('finance');
              setClientsButtonVisible(true);
              client_list = Array.isArray(data.clients) ? data.clients : [];
              document.getElementById('fin-total-rev').innerText = fmtMoney(data.total_revenue || 0);
              document.getElementById('fin-unpaid').innerText = fmtMoney(data.total_unpaid || 0);
              document.getElementById('fin-avg-per-client').innerText = fmtMoney(data.avg_revenue_per_client || 0);

              const ch = ensureChart('fin-revenue-trend', 'line', { options: { responsive: true, maintainAspectRatio: false } });
              if (ch) {
                ch.data.labels = data.trends?.date || [];
                const ctx = ch.canvas.getContext('2d');
                const secondaryColor = getCssVar('--secondary', '#78cee6');
                const accentColor = getCssVar('--accent', '#ce7a35');
                const lineGradDebit = makeGradientFromCtx(ctx, secondaryColor);
                const lineGradPayed = makeGradientFromCtx(ctx, accentColor);

                ch.data.datasets = [
                  { label: 'Revenue', data: data.trends?.revenue || [], borderWidth: 2, fill: true,
                    borderColor: hexToRgba(secondaryColor, 1),
                    backgroundColor: lineGradDebit },
                  { label: 'Unpaid', data: data.trends?.unpaid || [], borderWidth: 2, fill: true,
                    borderColor: hexToRgba(accentColor, 1),
                    backgroundColor: lineGradPayed }
                ];
                ch.update();
              }
            }
            if (tab === 'clients' && !["pro" , "ultra"].includes(APP_STATE.plan )){
              setClientsButtonVisible(false);
              showProOverlay('tab-clients', 'Customer Analytics', 'Customer insights like retention, top services, and weekly trends are available on the Pro and Ultra plans.');
            }
            else if (tab === 'clients') {
              data = await fetchMetric('total_customers');
              setClientsButtonVisible(true);
              client_list = Array.isArray(data.clients) ? data.clients : [];
              document.getElementById('pat-total').innerText = data.total_customers || 0;
              document.getElementById('pat-returning').innerText = data.returning_customers || 0;
              document.getElementById('pat-avg-visits').innerText = (data.avg_visits_per_customer || 0).toFixed(2);

              const ch = ensureChart('pat-weekly', 'bar', { options: { responsive: true, maintainAspectRatio: false } });
              if (ch) {
                ch.data.labels = data.weekly?.labels || [];
                const ctx = ch.canvas.getContext('2d');
                const secondaryColor = getCssVar('--secondary', '#78cee6');
                const accentColor = getCssVar('--accent', '#ce7a35');
                const lineGradDebit = makeGradientFromCtx(ctx, secondaryColor);
                const lineGradPayed = makeGradientFromCtx(ctx, accentColor);

                // returning clients per week: prefer an array from the API, else fallback to a same-length array of the scalar returning_clients
                const returningWeekly = data.weekly?.returning_counts ||
                  (Array.isArray(data.weekly?.counts) ? new Array(data.weekly.counts.length).fill(data.returning_customers || 0) : []);

                ch.data.datasets = [
                  { label: 'New clients', data: data.weekly?.counts || [], borderWidth: 1 , fill: true,
                    borderColor: hexToRgba(secondaryColor, 1),
                    backgroundColor: lineGradDebit },
                  { label: 'Returning clients', data: returningWeekly, borderWidth: 1, fill: true,
                    borderColor: hexToRgba(accentColor, 1),
                    backgroundColor: lineGradPayed }
                ];
                ch.update();
              }

              const list = document.getElementById('pat-top-list'); list.innerHTML = '';
              (data.top_diagnoses || []).forEach(x => {
                const e = document.createElement('div'); e.innerText = `${x.name} — ${x.count}`; list.appendChild(e);
              });
            }
          } catch (err) {
            console.error('Error loading tab', tab, err);
          }
      }else{
        showProOverlay('tab-' + tab, 'Pro Feature', 'This feature is only available on the Pro and Ultra plans. Upgrade now to unlock advanced analytics.');
      };
    }

    function reloadCurrentTab() { 
      loadTab(currentTab); 
    }

    // Sidebar controls
    function toggleSidebar() {
      const sidebar = document.getElementById('sidebar');
      const overlay = document.getElementById('sidebar-overlay');
      if (!sidebar || !overlay) return;
      const isOpen = sidebar.classList.contains('open');
      if (isOpen) {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
      } else {
        sidebar.classList.add('open');
        overlay.classList.add('active');
      }
    }

    function closeSidebar() {
      const sidebar = document.getElementById('sidebar');
      const overlay = document.getElementById('sidebar-overlay');
      if (!sidebar || !overlay) return;
      sidebar.classList.remove('open');
      overlay.classList.remove('active');
    }

    // Export for template
    window.StatsPage = { toggleSidebar, closeSidebar };
  