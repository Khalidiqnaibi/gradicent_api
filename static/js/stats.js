
      const APP_STATE = {
        plan: null,
        domain: null, // e.g., 'medical' | 'lab'
        user_id: null
      };
    var client_list = []
      
    document.addEventListener("DOMContentLoaded", async function() {
      document.getElementById("clients").style.display = "none";
      const menuBtn = document.querySelector('.hamburger-menu');
      const menuBar = document.getElementById('menuBar');

      const usage = startUsageTracker("/api/binder/track_time");
      APP_STATE.user_id = await api.get_user_id();
      APP_STATE.domain = await api.get_domain();
      let res = await api.get_plan_status();
      APP_STATE.plan = res.plan;
      // Toggle menu and spin transition
      menuBtn.addEventListener('click', () => {
        menuBar.classList.toggle('menu-active');
      });

      if (["starter","free"].includes(APP_STATE.plan)){
        document.querySelector('.tab-btn[data-tab="finance"').style.display= 'none';
        document.querySelector('.tab-btn[data-tab="clients"').style.display= 'none';
      }
      

      document.getElementById("clients").addEventListener("click", function () {
        show_clients();
      });

      
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
        user = await get_user();
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
      window.location.href = `/search_stats?clients=${client_list}`
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
      document.getElementById('dateFrom').value = fromStr;
      document.getElementById('dateTo').value = toStr;
    }

    // wire form submit to update filters and reload
    document.getElementById('filters').addEventListener('submit', e=>{
      e.preventDefault();
      const f = document.getElementById('dateFrom').value;
      const t = document.getElementById('dateTo').value;
      filters.from = f || null;
      filters.to = t || null;
      
      reloadCurrentTab();
    });

    // builds a query string only with present filters
    async function buildQsFromFilters() {
      if (APP_STATE.domain && APP_STATE.user_id){
        const params = new URLSearchParams();
        if (filters.from) params.append('from', filters.from);
        if (filters.to) params.append('to', filters.to);
        if (APP_STATE.domain) params.append('domain', APP_STATE.domain);
        if (APP_STATE.user_id) params.append('user_id', APP_STATE.user_id);
        return params.toString();
      }else{
        APP_STATE.domain  = await api.get_domain()
        APP_STATE.user_id = await api.get_user_id()
        
        const params = new URLSearchParams();
        if (filters.from) params.append('from', filters.from);
        if (filters.to) params.append('to', filters.to);
        if (APP_STATE.domain) params.append('domain', APP_STATE.domain);
        if (APP_STATE.user_id) params.append('user_id', APP_STATE.user_id);
        return params.toString();
      }
    }

    // ===== Tabs wiring =====
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
    async function loadTab(tab) {
      let tbs = ["productivity" , "roi"];
      let pln = ["pro" , "ultra"];
      
      if(tbs.includes(tab) || pln.includes(APP_STATE.plan)){
      {
        const qs = await buildQsFromFilters();
        let url = `/api/gaia/`;

        try {
            if (tab === 'roi') {
              document.getElementById("clients").style.display = "none";
              url = `/api/gaia/compute?metric=roi&${qs}&plan=${APP_STATE.plan}`;
              const res = await fetch(url);
              if (!res.ok) {
              console.error('API error', res.status, await res.text());
              return;
              }
              let data = await res.json();
              data = data.data;
              document.getElementById('roi-hours').innerText = (data.hours_saved || 0).toFixed(2) + ' hrs';
              document.getElementById('roi-dollar').innerText = fmtMoney(data.binder_roi || 0);
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
              d.innerHTML = `<div class="text-sm">${type}</div>`;
              
              const countEl = document.createElement('div');
              countEl.className = 'text-2xl font-semibold';
              countEl.innerText = count;
              d.appendChild(countEl);
              tasksEl.appendChild(d);
              }
            }

            if (tab === 'productivity') {
              document.getElementById("clients").style.display = "none";
              url = `/api/gaia/compute?metric=productivity&${qs}`;
              const res = await fetch(url);
              if (!res.ok) {
                console.error('API error', res.status, await res.text());
                return;
              }
              let data = await res.json();
              data = data.data;
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
              alert("CANT DO THAT NOW ,CAN U SILLY?");
            }
            else if (tab === 'finance') {
              url = `/api/gaia/compute?metric=finance&${qs}`;
              const res = await fetch(url);
              if (!res.ok) {
                console.error('API error', res.status, await res.text());
                return;
              }
              let data = await res.json();
              document.getElementById("clients").style.display = "block";
              data = data.data;
              client_list = data.clients;
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
              alert("CANT DO THAT NOW ,CAN U SILLY?");
            }
            else if (tab === 'clients') {
              url = `/api/gaia/compute?metric=total_customers&${qs}`;
              const res = await fetch(url);
              if (!res.ok) {
                console.error('API error', res.status, await res.text());
                return;
              }
              let data = await res.json();

              document.getElementById("clients").style.display = "block";
              data = data.data;
              client_list = data.clients;
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
                  (Array.isArray(data.weekly?.counts) ? new Array(data.weekly.counts.length).fill(data.returning_clients || 0) : []);

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
        }
      }else{
        alert("CANT DO THAT NOW ,CAN U SILLY?");
      };
    }

    function reloadCurrentTab() { 
      loadTab(currentTab); 
    }

  