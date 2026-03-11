const PlanPage = (function () {
  const state = {
    plans: [],
    billing: 'monthly'
  };

  const MOCK_PLANS = {
    starter: {
      key: 'starter',
      name: 'Starter',
      badge: 'Great for solo',
      description: 'Core client management and light reporting for new teams.',
      price: 12,
      featured: false,
      features: [
        'Client and contact tracking',
        'Basic analytics dashboards',
        'Email support'
      ]
    },
    pro: {
      key: 'pro',
      name: 'Pro',
      badge: 'Most popular',
      description: 'Automation-ready workflows with deeper reporting insights.',
      price: 29,
      featured: true,
      features: [
        'Advanced analytics views',
        'Team collaboration tools',
        'Priority support'
      ]
    }
  };

  const elements = {};

  async function safeFetch(url, opts = {}) {
    const res = await fetch(url, {
      ...opts,
      headers: { 'Content-Type': 'application/json', ...opts.headers }
    });
    const payload = await res.json();
    if (!res.ok) {
      throw new Error(payload.message || `HTTP ${res.status}`);
    }
    return payload;
  }

  function formatPrice(value, billing) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return 'Contact sales';
    }
    if (billing === 'yearly') {
      return `$${Number(value).toFixed(0)}`;
    }
    return `$${Number(value).toFixed(0)}`;
  }

  function mergePlans(plansData) {
    if (!plansData || typeof plansData !== 'object') {
      return [];
    }
    
    // Convert plans object to array and filter to show only starter and pro
    const planArray = Object.values(plansData)
      .filter(plan => plan.key === 'starter' || plan.key === 'pro')
      .map(plan => ({
        ...plan,
        yearlyPrice: plan.price !== null && plan.price !== undefined
          ? Number(plan.price) * 10
          : null
      }));
    
    // Sort to ensure consistent order: starter first, then pro
    return planArray.sort((a, b) => {
      const order = { starter: 0, pro: 1 };
      return order[a.key] - order[b.key];
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function renderPlans(plans) {
    if (!elements.grid) return;

    if (!plans.length) {
      elements.grid.innerHTML = '<div class="plan-note">No plans match your search.</div>';
      return;
    }

    elements.grid.innerHTML = plans
      .map((plan) => {
        const isYearly = state.billing === 'yearly';
        const priceValue = isYearly ? plan.yearlyPrice : plan.price;
        const priceLabel = formatPrice(priceValue, state.billing);
        const priceSuffix = isYearly ? 'per year (2 months free)' : 'per month';
        return `
          <article class="plan-card ${plan.featured ? 'featured' : ''}" data-plan="${escapeHtml(plan.key)}">
            <div class="plan-header">
              <div class="plan-name">${escapeHtml(plan.name)}</div>
              <span class="plan-badge">${escapeHtml(plan.badge)}</span>
            </div>
            <div class="plan-price">${priceLabel} <span>${priceSuffix}</span></div>
            <p class="plan-description">${escapeHtml(plan.description)}</p>
            <div class="plan-features">
              ${plan.features
                .map(
                  (feature) => `
                    <div class="plan-feature">
                      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                      </svg>
                      <span>${escapeHtml(feature)}</span>
                    </div>
                  `
                )
                .join('')}
            </div>
            <div class="plan-actions">
              <button class="btn ${plan.featured ? 'btn-primary' : 'btn-secondary'}" type="button">
                ${plan.featured ? 'Upgrade to ' + escapeHtml(plan.name) : 'Select ' + escapeHtml(plan.name)}
              </button>
            </div>
          </article>
        `;
      })
      .join('');
  }

  function setBilling(mode) {
    if (!mode || state.billing === mode) return;
    state.billing = mode;
    const isYearly = mode === 'yearly';
    elements.billingMonthly?.classList.toggle('is-active', !isYearly);
    elements.billingYearly?.classList.toggle('is-active', isYearly);
    elements.billingMonthly?.setAttribute('aria-pressed', String(!isYearly));
    elements.billingYearly?.setAttribute('aria-pressed', String(isYearly));
    elements.billingTrack?.classList.toggle('is-yearly', isYearly);
    renderPlans(state.plans);
  }

  async function loadPlans() {
    try {
      const res = await safeFetch('/api/payments/plans');
      const priceMap = res?.data?.plans || {};
      state.plans = mergePlans(priceMap);
      if (!state.plans.length) {
        state.plans = mergePlans(MOCK_PLANS);
      }
    } catch (err) {
      console.warn('Failed to load plans:', err);
      state.plans = mergePlans(MOCK_PLANS);
    }

    renderPlans(state.plans);
  }

  function toggleSidebar() {
    if (!elements.sidebar || !elements.overlay) return;
    const isOpen = elements.sidebar.classList.contains('open');
    if (isOpen) {
      elements.sidebar.classList.remove('open');
      elements.sidebar.classList.add('closed');
      elements.overlay.classList.remove('open');
    } else {
      elements.sidebar.classList.add('open');
      elements.sidebar.classList.remove('closed');
      elements.overlay.classList.add('open');
    }
  }

  function closeSidebar() {
    if (!elements.sidebar || !elements.overlay) return;
    elements.sidebar.classList.remove('open');
    elements.sidebar.classList.add('closed');
    elements.overlay.classList.remove('open');
  }

  function bindEvents() {
    elements.menuToggle?.addEventListener('click', toggleSidebar);
    elements.overlay?.addEventListener('click', closeSidebar);

    elements.billingMonthly?.addEventListener('click', () => setBilling('monthly'));
    elements.billingYearly?.addEventListener('click', () => setBilling('yearly'));
    elements.billingTrack?.addEventListener('click', () => {
      setBilling(state.billing === 'yearly' ? 'monthly' : 'yearly');
    });
  }

  function init() {
    elements.grid = document.getElementById('plan-grid');
    elements.billingMonthly = document.getElementById('billing-monthly');
    elements.billingYearly = document.getElementById('billing-yearly');
    elements.billingTrack = document.getElementById('billing-track');
    elements.menuToggle = document.getElementById('menu-toggle');
    elements.sidebar = document.getElementById('sidebar');
    elements.overlay = document.getElementById('sidebar-overlay');

    bindEvents();
    setBilling('monthly');
    loadPlans();
  }

  document.addEventListener('DOMContentLoaded', init);

  return { toggleSidebar, closeSidebar };
})();
