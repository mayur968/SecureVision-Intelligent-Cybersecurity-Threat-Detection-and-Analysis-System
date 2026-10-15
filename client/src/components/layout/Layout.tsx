import { useRef, useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar.js';
import { useAuth } from '../../context/AuthContext.js';

function UserAvatar({ name, picture }: { name?: string; picture?: string }) {
  const initials = name
    ? name
        .split(' ')
        .slice(0, 2)
        .map((w) => w[0])
        .join('')
        .toUpperCase()
    : '?';

  if (picture) {
    return (
      <img
        src={picture}
        alt={name ?? 'User avatar'}
        className="h-7 w-7 rounded-full object-cover"
        referrerPolicy="no-referrer"
      />
    );
  }

  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-primary text-xs font-semibold text-white">
      {initials}
    </span>
  );
}

export default function Layout() {
  const { user, loading, refetch } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  async function handleSignOut() {
    try {
      await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch {
      // Best-effort — clear local state regardless
    }
    await refetch();
    setDropdownOpen(false);
    navigate('/');
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-base">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* ── Top bar ───────────────────────────────────────────────── */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-surface-border bg-surface-raised px-6">
          <div className="flex items-center gap-2 text-sm text-content-muted">
            <span className="text-content-disabled">SecureVision</span>
            <span className="text-content-disabled">/</span>
            <span className="text-content-secondary font-medium" id="page-title">Dashboard</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="rounded-sm bg-surface-overlay px-2 py-0.5 font-mono text-2xs text-content-muted">
              ML API :5000
            </span>

            {/* Auth state */}
            {loading ? (
              <span className="h-7 w-7 animate-pulse rounded-full bg-surface-muted" />
            ) : user?.authenticated ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-accent-primary focus:ring-offset-1"
                  onClick={() => setDropdownOpen((o) => !o)}
                  aria-haspopup="true"
                  aria-expanded={dropdownOpen}
                  aria-label="Account menu"
                >
                  <UserAvatar name={user.name} picture={user.picture} />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded border border-surface-border bg-surface-raised shadow-lg z-50">
                    <div className="px-4 py-3">
                      <p className="truncate text-sm font-medium text-content-primary">
                        {user.name ?? 'User'}
                      </p>
                      <p className="truncate text-xs text-content-muted">{user.email}</p>
                    </div>
                    <div className="border-t border-surface-border" />
                    <div className="py-1">
                      <button
                        type="button"
                        className="w-full px-4 py-2 text-left text-sm text-content-secondary hover:bg-surface-overlay"
                        onClick={handleSignOut}
                      >
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Link
                to="/login"
                className="btn-ghost text-xs px-3 py-1.5"
              >
                Sign in
              </Link>
            )}
          </div>
        </header>

        {/* ── Page content ──────────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
