    /**
     * settings.js — User Settings Page
     * ---------------------------------
     * Lets the user configure:
     *   - drname   : Doctor/business display name
     *   - msg      : Default message template (e.g. for appointment SMS)
     *   - pkey     : External API key (custom integrations)
     *   - code     : Activation / embed code (hidden by default)
     *   - send     : Toggle for auto-sending messages (checkbox cbx-3)
     *
     * Plan gating:
     *   - "sec" plan hides the code section entirely (#ccc element).
     *     This plan has restricted features.
     *
     * Domain variants:
     *   - "lab" domain changes icons, titles, and links to lab-specific
     *     pages (same pattern as acc.js).
     *
     * Settings are stored in user.metadata.settings on the backend.
     * If no settings exist yet, defaults are created locally.
     */

    const API_TIMEOUT_MS = 10_000;
    const POLL_TRACK_INTERVAL_MS = 60_000;
    
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

    async function get_user_id(){
      const url = `/api/auth/me`;
      const data = await safe_fetch(url, { method: 'GET' });
      return data.data.id;    
    }

    async  function get_user(user_id,domain='') {
      const data = await safe_fetch(`/api/binder/user?user_id=${user_id}&domain=${domain}`, { method: 'GET' });
      return data.data;
    }

    async function get_domain() {
      try {
        const data = await safe_fetch('/api/binder/get_domain', { method: 'GET' });
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
        const data = await safe_fetch('/api/binder/get_plan_status', { method: 'GET' });
        // expected shape: { data: { days: N, plan: 'x' } } or { days: N, plan: 'x' }
        if (!data) return null;
        const payload = data.data || data;
        return { days: Number(payload.days || 0), plan: payload.plan || null };
      } catch (err) {
        return null;
      }
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

    // small toast helper
    function showToast(text, ms = 1800){
      const toast = document.getElementById('toast');
      toast.textContent = text;
      toast.classList.add('show');
      clearTimeout(toast._t);
      toast._t = setTimeout(()=> toast.classList.remove('show'), ms);
    }


    // Module-level state so savePatientInfo() can access them
    let _user = {};        // full user object from API
    let _user_id = '';     // user ID string

    // Save settings (keeps your original semantics)
    function savePatientInfo(){
      _user.drname = document.getElementById("drname").value;
      _user.msg = document.getElementById("msg").value;
      _user.pkey = document.getElementById("pkey").value;
      _user.code = document.getElementById("code").value;
      _user.send = document.getElementById("cbx-3").checked;
      fetch('/api/binder/user', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({user_id: _user_id, user: _user })
      })
      .then(r => r.json())
      .then(()=> showToast('Settings saved'))
      .catch(e => { console.error(e); showToast('Save failed'); });
    }


    document.addEventListener('DOMContentLoaded', async function() {
      const menuBtn=document.querySelector('.hamburger-menu');
      const menuBar=document.getElementById('menuBar');
      if (menuBtn && menuBar) menuBtn.addEventListener('click',()=>menuBar.classList.toggle('menu-active'));
      
      let plan = 'free';
      let domain = '';

      const usage = startUsageTracker("/api/binder/track_time");

      let res = await get_plan_status()

      plan = res.plan
      _user_id = await get_user_id();
      domain = await get_domain();

      _user = await get_user(_user_id,domain);

      // \"sec\" plan: hide the code section entirely
      if(plan==='sec'){ 
        try { 
          document.getElementById("ccc").style.display="none"; 
        } catch(e){} 
      }

      // Build default settings object if user has none saved yet
      let sett = (_user.metadata && _user.metadata.settings) || null;
      
      if (!sett){
        sett = {
          "send": false,
          "pkey": "",
          "drname" : _user.name,
          "msg": "",
          "ac" : {
            "code": "/* no code yet */",
          }
        }
      }
      document.getElementById("cbx-3").checked=!!sett.send??false;
      document.getElementById("pkey").value=sett.pkey ?? '';
      document.getElementById("drname").value=sett.drname ?? _user.name;
      document.getElementById("msg").value=sett.msg ?? '';
      if (plan !=='sec'){
        document.getElementById("code").value=(sett.ac && sett.ac.code) ? sett.ac.code : '';
      }else {
        document.getElementById("code").value= "This feature is not available on your plan.";
      }
      // also show preview content initially hidden
      document.getElementById("codePreview").textContent = (sett.ac && sett.ac.code) ? sett.ac.code : '/* no code yet */';
      
      
      // copy code to clipboard
      document.getElementById("copy-code").addEventListener("click", async (e) => {
        e.preventDefault();
        const code = document.getElementById("codePreview").textContent || document.getElementById("code").value;
        if(!code) { showToast('Nothing to copy'); return; }
        try {
          await navigator.clipboard.writeText(code);
          showToast('Code copied');
        } catch (err) {
          console.error(err);
          showToast('Copy failed');
        }
      });

      let isVisible = false;
      document.getElementById("toggle-visibility").addEventListener("click", (e)=>{
        e.preventDefault();
        const codeInput = document.getElementById("code");
        isVisible = !isVisible;
        codeInput.type = isVisible ? "text" : "password";
        const btn = e.currentTarget;
        btn.setAttribute('aria-pressed', String(isVisible));
        // change small label
        btn.querySelector('span') && (btn.querySelector('span').textContent = isVisible ? 'Hide' : 'Show');
      });

      // refresh code (hits same endpoint you used before)
      document.getElementById("refresh-code").addEventListener("click", async (e) => {
        e.preventDefault();
        try {
          const res = await fetch('/api/binder/code', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ user_id: _user_id, domain,  code: document.getElementById("code").value})
          });
          const d = await res.json();
          if (d?.data) {
            document.getElementById("code").value = d.data;
            document.getElementById("codePreview").textContent = d.data;
            showToast('Code refreshed');
          } else showToast('No code returned');
        } catch (err) {
          console.error(err);
          showToast('Refresh failed');
        }
      });

      // settings dark mode toggle (syncs with sidebar moon button)
      const settingsThemeBtn = document.getElementById('theme-toggle-settings');
      if (settingsThemeBtn) {
        settingsThemeBtn.addEventListener('click', () => {
          if (window.EntityManager && typeof window.EntityManager.toggleTheme === 'function') {
            window.EntityManager.toggleTheme();
            return;
          }

          // Fallback if shared manager is unavailable
          const isDark = document.body.classList.contains('theme-dark');
          document.body.classList.toggle('theme-dark', !isDark);
          localStorage.setItem('gradicent_theme', isDark ? 'light' : 'dark');
          const label = settingsThemeBtn.querySelector('[data-theme-label]');
          if (label) label.textContent = isDark ? 'Dark mode: Off' : 'Dark mode: On';
        });
      }

      // "lab" domain variant: override icons, titles, and links
      if(domain==='lab'){
        const appa=document.getElementById('appa');
        const appimg=document.getElementById('appimg');
        const apph6=document.getElementById('apph6');
        const link=document.querySelector("link[rel~='icon']");
        if(appa){ appa.title='Binder Lab'; appa.href='/srchlab'; }
        if(appimg) appimg.src='/static/images/srchlab.png';
        if(apph6) apph6.textContent='Binder Lab';
        document.title='Binder Laboratory';
        if(link) link.href='/static/images/binderlab.jpg';
        // optional lab label update
        try { document.getElementById("namee").textContent="Lab name:"; } catch(e){}
      }
})
    
  