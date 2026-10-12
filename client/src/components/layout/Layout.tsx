import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar.js';

export default function Layout() {
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
