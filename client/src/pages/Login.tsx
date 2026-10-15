import { Link } from 'react-router-dom';
import logo from '../assets/logo.svg';

export default function Login() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-base px-4">
      {/* Logo */}
      <div className="mb-6 flex items-center gap-3">
        <img src={logo} alt="SecureVision" className="h-10 w-10" />
        <span className="text-xl font-semibold text-content-primary tracking-tight">
          SecureVision
        </span>
      </div>

      {/* Card */}
      <div className="card w-full max-w-sm p-8 text-center">
        <h1 className="mb-2 text-2xl font-bold text-content-primary">Sign In</h1>
        <p className="mb-6 text-sm text-content-secondary">
          Access your scan history and Gmail features.
        </p>

        {/* Coming in Stage 2 notice */}
        <div className="rounded border border-surface-muted bg-surface-overlay px-4 py-4 mb-6">
          <p className="text-sm text-content-muted">
            Authentication coming in Stage 2.
          </p>
        </div>

        <Link
          to="/dashboard"
          className="inline-block w-full btn-ghost text-center"
        >
          Continue as guest →
        </Link>
      </div>

      <p className="mt-6 text-xs text-content-disabled">
        No account required to use URL, message, or APK scanning.
      </p>
    </div>
  );
}
