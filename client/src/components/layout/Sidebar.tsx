import { NavLink } from 'react-router-dom';
import logo from '../../assets/logo.svg';

/* ── SVG icon set — clean line icons, no emoji ─────────────────────────── */
const Icon = {
  Dashboard: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="1" width="6" height="6" rx="1"/>
      <rect x="9" y="1" width="6" height="6" rx="1"/>
      <rect x="1" y="9" width="6" height="6" rx="1"/>
      <rect x="9" y="9" width="6" height="6" rx="1"/>
    </svg>
  ),
  Url: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6.5 9.5a3.536 3.536 0 0 0 5 0l2-2a3.536 3.536 0 0 0-5-5l-1.1 1.1"/>
      <path d="M9.5 6.5a3.536 3.536 0 0 0-5 0l-2 2a3.536 3.536 0 0 0 5 5L8.6 12.4"/>
    </svg>
  ),
  Message: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H2a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h3l2 2 2-2h5a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1Z"/>
      <path d="M5 6h6M5 9h4"/>
    </svg>
  ),
  Apk: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="1" width="10" height="14" rx="1.5"/>
      <path d="M6 4h4M6 7h4M6 10h2"/>
      <circle cx="10" cy="10.5" r="1.25" fill="currentColor" stroke="none"/>
    </svg>
  ),
  Email: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="3" width="14" height="10" rx="1.5"/>
      <path d="M1 3l7 5 7-5"/>
      <path d="M1 8l4 2M15 8l-4 2"/>
    </svg>
  ),
  History: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="6.5"/>
      <path d="M8 4.5V8l2.5 1.5"/>
    </svg>
  ),
  Shield: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1.5 2 4v4.5c0 3 2.5 5.5 6 6 3.5-.5 6-3 6-6V4L8 1.5Z"/>
      <path d="m5.5 8 1.5 1.5 3.5-3"/>
    </svg>
  ),
};

const NAV_ITEMS = [
  { to: '/dashboard',    icon: Icon.Dashboard, label: 'Dashboard'       },
  { to: '/scan/url',     icon: Icon.Url,       label: 'URL Scanner'     },
  { to: '/scan/message', icon: Icon.Message,   label: 'Message Scanner' },
  { to: '/scan/apk',     icon: Icon.Apk,       label: 'APK Scanner'     },
  { to: '/scan/email',   icon: Icon.Email,     label: 'Email Scanner'   },
  { to: '/history',      icon: Icon.History,   label: 'Scan History'    },
];

export default function Sidebar() {
  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col border-r border-surface-border bg-surface-raised">
      {/* ── Brand ──────────────────────────────────────────────────────── */}
      <div className="flex h-14 items-center gap-2.5 border-b border-surface-border px-4">
        <img src={logo} alt="SecureVision" className="h-7 w-7 shrink-0" />
        <div className="leading-none">
          <p className="text-sm font-semibold text-content-primary tracking-tight">SecureVision</p>
          <p className="text-2xs text-content-muted mt-0.5">Threat Platform</p>
        </div>
      </div>

      {/* ── Navigation ─────────────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        <p className="section-label mb-2 px-2">Detection</p>
        <ul className="space-y-0.5">
          {NAV_ITEMS.map(({ to, icon: IconComp, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/dashboard'}
                className={({ isActive }) =>
                  `group flex items-center gap-2.5 rounded px-2.5 py-2 text-sm font-medium transition-all duration-100 ${
                    isActive
                      ? 'bg-accent-subtle text-accent-glow'
                      : 'text-content-secondary hover:bg-surface-overlay hover:text-content-primary'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span className={`shrink-0 transition-colors ${isActive ? 'text-accent-glow' : 'text-content-muted group-hover:text-content-secondary'}`}>
                      <IconComp />
                    </span>
                    {label}
                    {isActive && (
                      <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent-glow" />
                    )}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* ── Status footer ──────────────────────────────────────────────── */}
      <div className="border-t border-surface-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="live-dot text-2xs font-medium text-sev-low" />
          <span className="text-2xs text-content-muted">ML Service Online</span>
        </div>
        <p className="mt-1 text-2xs text-content-disabled">v2.0 · SecureVision</p>
      </div>
    </aside>
  );
}
