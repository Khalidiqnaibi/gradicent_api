/**
 * entity.js - Shared controller for entity management pages
 * Supports: clients, products, services, employees
 */

const EntityManager = (function() {
  // Config loaded from window.__ENTITY_CONFIG__
  const CONFIG = window.__ENTITY_CONFIG__ || {};
  const TYPE = window.__ENTITY_TYPE__ || 'entity';

  // State
  const STATE = {
    domain: null,
    user_id: null,
    items: [],
    loading: false
  };

  // DOM helpers
  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  // API helpers
  async function safeFetch(url, opts = {}) {
    try {
      const res = await fetch(url, {
        ...opts,
        headers: { 'Content-Type': 'application/json', ...opts.headers }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
      return data;
    } catch (err) {
      console.error('API Error:', err);
      throw err;
    }
  }

  async function getDomain() {
    try {
      const res = await safeFetch('/api/binder/get_domain');
      return res.data || 'business';
    } catch { return 'business'; }
  }

  async function getUserId() {
    try {
      const res = await safeFetch('/api/auth/me');
      return res.data?.id;
    } catch { return null; }
  }

  // Toast notifications
  function toast(message, type = 'info') {
    const container = $('toasts');
    if (!container) return;

    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.innerHTML = `
      <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
        ${type === 'success' ? '<path d="M20 6L9 17l-5-5"/>' : 
          type === 'error' ? '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/>' :
          '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>'}
      </svg>
      <span>${message}</span>
    `;
    container.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }

  // UI rendering
  function renderItems(items) {
    const container = $('results');
    if (!container) return;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
          </svg>
          <h3>No ${CONFIG.labels?.plural || 'items'} found</h3>
          <p>Try a different search or add a new ${CONFIG.labels?.singular || 'item'}</p>
        </div>
      `;
      return;
    }

    const displayFields = CONFIG.fields?.display || ['name'];
    
    container.innerHTML = `
      <div class="entity-grid">
        ${items.map((item, idx) => `
          <div class="entity-card" data-id="${item.id ?? idx}">
            <div class="entity-card-header">
              <span class="entity-name">${escapeHtml(item.name || item.id || `#${idx + 1}`)}</span>
              ${item.status ? `<span class="entity-badge">${item.status}</span>` : ''}
            </div>
            <div class="entity-meta">
              ${displayFields.slice(1).map(field => item[field] ? `
                <div class="entity-meta-item">
                  <span>${formatLabel(field)}:</span>
                  <strong>${escapeHtml(String(item[field]))}</strong>
                </div>
              ` : '').join('')}
            </div>
            <div class="entity-actions">
              <button class="btn btn-sm btn-secondary" onclick="EntityManager.view('${item.id ?? idx}')">View</button>
              <button class="btn btn-sm btn-ghost" onclick="EntityManager.edit('${item.id ?? idx}')">Edit</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function setLoading(loading) {
    STATE.loading = loading;
    const btn = $('search_btn');
    const addBtn = $('add_btn');
    if (btn) btn.disabled = loading;
    if (addBtn) addBtn.disabled = loading;
  }

  // Actions
  async function search() {
    const query = ($('query_input')?.value || '').trim();
    
    setLoading(true);
    try {
      let items = [];
      
      if (CONFIG.searchEndpoint && query) {
        // Use search endpoint
        const res = await safeFetch(CONFIG.searchEndpoint, {
          method: 'POST',
          body: JSON.stringify({
            query,
            domain: STATE.domain,
            user_id: STATE.user_id
          })
        });
        items = res.data ? Object.values(res.data) : [];
      } else {
        // Use list endpoint and filter client-side
        const res = await safeFetch(`${CONFIG.listEndpoint}?domain=${STATE.domain}&user_id=${STATE.user_id}`);
        items = Array.isArray(res.data) ? res.data : Object.values(res.data || {});
        
        if (query) {
          const q = query.toLowerCase();
          items = items.filter(item => 
            CONFIG.fields?.search?.some(f => 
              String(item[f] || '').toLowerCase().includes(q)
            )
          );
        }
      }

      STATE.items = items;
      renderItems(items);
      
      if (items.length > 0) {
        toast(`Found ${items.length} ${items.length === 1 ? CONFIG.labels?.singular : CONFIG.labels?.plural}`, 'success');
      }
    } catch (err) {
      toast(err.message || 'Search failed', 'error');
    } finally {
      setLoading(false);
    }
  }

  async function loadAll() {
    if (!CONFIG.listEndpoint) {
      // No list endpoint - show add prompt
      const container = $('results');
      if (container) {
        container.innerHTML = `
          <div class="empty-state">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
                d="M12 4v16m8-8H4"/>
            </svg>
            <h3>Add your first ${CONFIG.labels?.singular || 'item'}</h3>
            <p>Click "Add New" to create a new ${CONFIG.labels?.singular?.toLowerCase() || 'item'}</p>
          </div>
        `;
      }
      return;
    }

    setLoading(true);
    try {
      const res = await safeFetch(`${CONFIG.listEndpoint}?domain=${STATE.domain}&user_id=${STATE.user_id}`);
      const items = Array.isArray(res.data) ? res.data : Object.values(res.data || {});
      STATE.items = items;
      renderItems(items);
    } catch (err) {
      // List endpoint failed - show search prompt instead
      const container = $('results');
      if (container) {
        container.innerHTML = `
          <div class="empty-state">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" 
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <h3>Search for ${CONFIG.labels?.plural || 'items'}</h3>
            <p>Enter a search term above to find ${CONFIG.labels?.plural?.toLowerCase() || 'items'}</p>
          </div>
        `;
      }
    } finally {
      setLoading(false);
    }
  }

  async function add() {
    const fields = CONFIG.fields?.add || [];
    const data = {};
    
    for (const field of fields) {
      const el = $(field);
      if (el) {
        data[field] = el.type === 'number' ? (el.value ? Number(el.value) : null) : el.value;
      }
    }

    // Validate required fields (at minimum, name)
    if (!data.name?.trim()) {
      toast('Name is required', 'error');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        domain: STATE.domain,
        user_id: STATE.user_id
      };
      payload[TYPE] = data;

      await safeFetch(CONFIG.apiBase, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      toast(`${CONFIG.labels?.singular || 'Item'} added successfully`, 'success');
      
      // Clear form
      fields.forEach(f => {
        const el = $(f);
        if (el) el.value = '';
      });

      // Close add form and reload
      toggleAddForm();
      await loadAll();
    } catch (err) {
      toast(err.message || 'Failed to add', 'error');
    } finally {
      setLoading(false);
    }
  }

  function view(id) {
    const item = STATE.items.find(i => String(i.id) === String(id));
    if (!item) return;
    
    // Could open modal or navigate - for now just log
    console.log('View item:', item);
    toast(`Viewing ${item.name || id}`, 'info');
    
    // Navigate to detail page if exists
    if (CONFIG.detailUrl) {
      window.location.href = CONFIG.detailUrl.replace('{id}', id);
    }
  }

  function edit(id) {
    const item = STATE.items.find(i => String(i.id) === String(id));
    if (!item) return;
    
    // Switch to add tab and populate fields
    switchTab('add');
    
    const fields = CONFIG.fields?.add || [];
    fields.forEach(f => {
      const el = $(f);
      if (el && item[f] !== undefined) {
        el.value = item[f];
      }
    });
    
    toast(`Editing ${item.name || id}`, 'info');
  }

  // Add form toggle
  function toggleAddForm() {
    const form = $('add-form');
    if (form) {
      const isVisible = form.style.display !== 'none';
      form.style.display = isVisible ? 'none' : 'block';
      if (!isVisible) {
        // Focus first input when opening
        form.querySelector('input')?.focus();
      }
    }
  }

  // Sidebar
  function toggleSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) {
      const isOpen = !sidebar.classList.contains('closed');
      if (isOpen) {
        sidebar.classList.add('closed');
        sidebar.classList.remove('open');
      } else {
        sidebar.classList.remove('closed');
        sidebar.classList.add('open');
      }
    }
    if (overlay) overlay.classList.toggle('open');
  }

  function closeSidebar() {
    const sidebar = $('sidebar');
    const overlay = $('sidebar-overlay');
    if (sidebar) {
      sidebar.classList.remove('open');
      sidebar.classList.add('closed');
    }
    if (overlay) overlay.classList.remove('open');
  }

  // Helpers
  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, c => 
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  function formatLabel(field) {
    return field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  // Initialize
  async function init() {
    try {
      STATE.domain = await getDomain();
      STATE.user_id = await getUserId();
    } catch (err) {
      console.warn('Failed to load user context:', err);
    }

    // Top bar hide on scroll
    let lastScrollY = 0;
    let ticking = false;
    const topBar = document.querySelector('.top-bar');
    
    if (topBar) {
      window.addEventListener('scroll', () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            const currentScrollY = window.scrollY;
            
            // Add scrolled class for shadow
            if (currentScrollY > 10) {
              topBar.classList.add('scrolled');
            } else {
              topBar.classList.remove('scrolled');
            }
            
            // Hide/show based on scroll direction
            if (currentScrollY > lastScrollY && currentScrollY > 80) {
              topBar.classList.add('hidden');
            } else {
              topBar.classList.remove('hidden');
            }
            
            lastScrollY = currentScrollY;
            ticking = false;
          });
          ticking = true;
        }
      }, { passive: true });
    }

    // Search on enter and as you type
    const queryInput = $('query_input');
    if (queryInput) {
      queryInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') search();
      });
      // Real-time search with debounce
      let searchTimeout;
      queryInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => search(), 300);
      });
    }

    // Add form toggle
    $('add_toggle')?.addEventListener('click', toggleAddForm);

    // Add button
    $('add_btn')?.addEventListener('click', add);

    // Sidebar
    $('menu-toggle')?.addEventListener('click', toggleSidebar);
    $('sidebar-overlay')?.addEventListener('click', closeSidebar);

    // Load initial data
    await loadAll();
  }

  // Boot
  document.addEventListener('DOMContentLoaded', init);

  // Public API
  return { search, add, view, edit, loadAll, toggleAddForm, toggleSidebar, closeSidebar };
})();
