/**
 * plan.js — Pricing / Plans Page
 * -------------------------------
 * Displays available subscription plans (starter, pro) with
 * monthly/yearly billing toggle.
 *
 * Plans are fetched from /api/payments/plans. If the API fails
 * or returns empty, MOCK_PLANS are used as a fallback so the
 * page always renders.
 *
 * Yearly price = monthly price * 10 (2 months free).
 */
const PlanPage = (function () {
  const THEME_KEY = 'gradicent_theme';

  const state = {
    plans: [],
    billing: 'monthly'
  };

  const MOCK_PLANS = {
    starter: {
      key: 'starter',
      name: 'Starter',
      badge: 'Best to begin',
      description: 'Start organizing clients, appointments, and daily operations in one simple workflow that saves you hours every week.',
      pitch: 'Perfect for small teams that want to look professional, stay organized, and grow without complexity.',
      price: 12,
      featured: false,
      features: [
        'Client and contact tracking with clean history',
        'Appointment workflow to reduce missed follow-ups',
        'Core analytics dashboard for weekly decisions',
        'Email support and fast onboarding help'
      ]
    },
    pro: {
      key: 'pro',
      name: 'Pro',
      badge: 'Most popular',
      description: 'Scale faster with automation, deeper insights, and premium workflows designed for teams that want measurable growth.',
      pitch: 'Built for ambitious businesses ready to increase revenue, improve retention, and run smarter every day.',
      price: 29,
      featured: true,
      features: [
        'Advanced analytics with clearer revenue and retention insights',
        'Team collaboration tools for smoother daily operations',
        'Priority support for critical business moments',
        'Automation-friendly setup to save recurring manual work'
      ]
    }
  };

  const MARKETING_COPY = {
    starter: {
      badge: 'Best to begin',
      description: 'Start organizing clients, appointments, and daily operations in one simple workflow that saves you hours every week.',
      pitch: 'Perfect for small teams that want to look professional, stay organized, and grow without complexity.',
      features: [
        'Client and contact tracking with clean history',
        'Appointment workflow to reduce missed follow-ups',
        'Core analytics dashboard for weekly decisions',
        'Email support and fast onboarding help'
      ]
    },
    pro: {
      badge: 'Most popular',
      description: 'Scale faster with automation, deeper insights, and premium workflows designed for teams that want measurable growth.',
      pitch: 'Built for ambitious businesses ready to increase revenue, improve retention, and run smarter every day.',
      features: [
        'Advanced analytics with clearer revenue and retention insights',
        'Team collaboration tools for smoother daily operations',
        'Priority support for critical business moments',
        'Automation-friendly setup to save recurring manual work'
      ]
    }
  };

  const elements = {};

  function getTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
    return 'light';
  }

  function applyTheme(theme) {
    const resolved = theme === 'dark' ? 'dark' : 'light';
    document.body.classList.toggle('theme-dark', resolved === 'dark');
    document.documentElement.setAttribute('data-theme', resolved);

    const btn = elements.themeToggle;
    if (!btn) return;

    btn.setAttribute('aria-pressed', String(resolved === 'dark'));
    btn.setAttribute('title', resolved === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    const path = btn.querySelector('svg path');
    if (path) {
      path.setAttribute(
        'd',
        resolved === 'dark'
          ? 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.364 6.364l-1.414-1.414M7.05 7.05 5.636 5.636m12.728 0-1.414 1.414M7.05 16.95l-1.414 1.414M12 8a4 4 0 100 8 4 4 0 000-8z'
          : 'M21 12.79A9 9 0 1111.21 3c-.07.32-.11.65-.11 1a9 9 0 009.9 8.79z'
      );
    }
  }

  function toggleTheme() {
    const next = getTheme() === 'dark' ? 'light' : 'dark';
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  }

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
        ...(MARKETING_COPY[plan.key] || {}),
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
            <p class="plan-pitch">${escapeHtml(plan.pitch || '')}</p>
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
                ${plan.featured ? 'Upgrade Your Plan' : 'Select ' + escapeHtml(plan.name)}
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
      elements.overlay.classList.remove('active');
    } else {
      elements.sidebar.classList.add('open');
      elements.overlay.classList.add('active');
    }
  }

  function closeSidebar() {
    if (!elements.sidebar || !elements.overlay) return;
    elements.sidebar.classList.remove('open');
    elements.overlay.classList.remove('active');
  }

  function bindEvents() {
    elements.menuToggle?.addEventListener('click', toggleSidebar);
    elements.overlay?.addEventListener('click', closeSidebar);
    elements.themeToggle?.addEventListener('click', toggleTheme);

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
    elements.themeToggle = document.getElementById('plan-theme-toggle');

    applyTheme(getTheme());

    bindEvents();
    setBilling('monthly');
    loadPlans();
  }

  document.addEventListener('DOMContentLoaded', init);

  return { toggleSidebar, closeSidebar };
})();
