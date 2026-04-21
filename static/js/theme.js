/**
 * theme.js — Dark / light theme management
 * -----------------------------------------
 * Handles:
 *   - Reading and writing the persisted theme preference.
 *   - Applying theme CSS variables to the document.
 *   - Injecting a theme-toggle button into the sidebar header.
 *   - Injecting the CSS custom-property stylesheet (idempotent).
 *
 * This module is intentionally self-contained and has no runtime imports —
 * it only uses the DOM and localStorage, so it can run very early in the
 * page lifecycle without waiting for other modules.
 */

const THEME_KEY   = 'gradicent_theme';
const STYLE_TAG_ID = 'gradicent-theme-styles';

// ─── Theme CSS ────────────────────────────────────────────────────────────────

const THEME_CSS = `
  :root, [data-theme="light"] {
    --bg-primary:    #ffffff;
    --bg-secondary:  #f5f5f4;
    --bg-sidebar:    #fafaf9;
    --text-primary:  #1c1917;
    --text-secondary:#57534e;
    --border-color:  #e7e5e4;
    --accent:        #0ea5e9;
    --accent-hover:  #0284c7;
    --sidebar-toggle-bg:    transparent;
    --sidebar-toggle-hover: #e7e5e4;
    --sidebar-toggle-icon:  #57534e;
  }

  [data-theme="dark"] {
    --bg-primary:    #0f0f0f;
    --bg-secondary:  #1a1a1a;
    --bg-sidebar:    #141414;
    --text-primary:  #fafaf9;
    --text-secondary:#a8a29e;
    --border-color:  #292524;
    --accent:        #38bdf8;
    --accent-hover:  #7dd3fc;
    --sidebar-toggle-bg:    transparent;
    --sidebar-toggle-hover: #292524;
    --sidebar-toggle-icon:  #a8a29e;
  }

  body, body * {
    transition:
      background-color 0.2s ease,
      color            0.2s ease,
      border-color     0.2s ease;
  }

  .sidebar-theme-toggle {
    display:         flex;
    align-items:     center;
    justify-content: center;
    width:           34px;
    height:          34px;
    padding:         0;
    border:          none;
    border-radius:   8px;
    background:      var(--sidebar-toggle-bg);
    color:           var(--sidebar-toggle-icon);
    cursor:          pointer;
    flex-shrink:     0;
    transition:      background 0.15s ease, color 0.15s ease;
  }

  .sidebar-theme-toggle:hover {
    background: var(--sidebar-toggle-hover);
    color:      var(--text-primary);
  }

  .sidebar-theme-toggle svg {
    width:   18px;
    height:  18px;
    display: block;
  }

  @media (prefers-reduced-motion: no-preference) {
    .sidebar-theme-toggle svg {
      transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .sidebar-theme-toggle:active svg {
      transform: rotate(30deg) scale(0.9);
    }
  }
`;

// ─── Icon paths ───────────────────────────────────────────────────────────────

const ICON = {
  sun  : 'M12 3v2m0 14v2m9-9h-2M5 12H3m15.364 6.364-1.414-1.414M7.05 7.05 5.636 5.636m12.728 0-1.414 1.414M7.05 16.95l-1.414 1.414M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
  moon : 'M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z',
};

// ─── Core helpers ─────────────────────────────────────────────────────────────

/**
 * Read the persisted preference, falling back to the OS preference.
 * @returns {'dark'|'light'}
 */
export function getTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'dark' || stored === 'light') return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Apply a theme to the document and update all toggle buttons.
 * @param {'dark'|'light'} theme
 */
export function applyTheme(theme) {
  const isDark = theme === 'dark';
  document.body.classList.toggle('theme-dark', isDark);
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');

  const iconPath = isDark ? ICON.sun : ICON.moon;
  const label    = isDark ? 'Switch to light mode' : 'Switch to dark mode';

  document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(isDark));
    btn.setAttribute('title',        label);
    btn.setAttribute('aria-label',   label);
    const pathEl   = btn.querySelector('svg path');
    if (pathEl) pathEl.setAttribute('d', iconPath);
    const labelEl  = btn.querySelector('[data-theme-label]');
    if (labelEl) labelEl.textContent = isDark ? 'Dark mode: On' : 'Dark mode: Off';
  });
}

/**
 * Persist and apply a theme.
 * @param {'dark'|'light'} theme
 * @returns {'dark'|'light'}
 */
export function setTheme(theme) {
  const resolved = theme === 'dark' ? 'dark' : 'light';
  localStorage.setItem(THEME_KEY, resolved);
  applyTheme(resolved);
  return resolved;
}

/**
 * Toggle between dark and light and persist the choice.
 * @returns {'dark'|'light'}
 */
export function toggleTheme() {
  return setTheme(getTheme() === 'dark' ? 'light' : 'dark');
}

// ─── Stylesheet injection ─────────────────────────────────────────────────────

/**
 * Inject the theme stylesheet into <head> once (idempotent).
 */
export function injectThemeStyles() {
  if (document.getElementById(STYLE_TAG_ID)) return;
  const style       = document.createElement('style');
  style.id          = STYLE_TAG_ID;
  style.textContent = THEME_CSS;
  document.head.appendChild(style);
}

// ─── Sidebar toggle button ────────────────────────────────────────────────────

/**
 * Inject a theme-toggle button into .sidebar-header (if present and not
 * already inserted).
 *
 * Returns the toggle function so the caller can register it via the
 * centralised event listener registry (_on), keeping cleanup consistent.
 *
 * This avoids the previous pattern where the button's listener was registered
 * directly with addEventListener inside this function, making it invisible to
 * the cleanup() registry.  The caller is responsible for calling _on(btn, …).
 *
 * @returns {{ button: HTMLElement|null }}
 */
export function ensureSidebarThemeToggle() {
  const header = document.querySelector('.sidebar-header');
  if (!header) return { button: null };
  if (document.getElementById('sidebar-theme-toggle')) return { button: document.getElementById('sidebar-theme-toggle') };

  const btn       = document.createElement('button');
  btn.type        = 'button';
  btn.id          = 'sidebar-theme-toggle';
  btn.className   = 'sidebar-theme-toggle';
  btn.setAttribute('data-theme-toggle', 'sidebar');
  btn.innerHTML   = `
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=""/>
    </svg>
  `;

  const closeBtn = header.querySelector('.sidebar-close');
  closeBtn ? header.insertBefore(btn, closeBtn) : header.appendChild(btn);

  // Apply current theme so icon is correct immediately.
  applyTheme(getTheme());

  return { button: btn };
}
