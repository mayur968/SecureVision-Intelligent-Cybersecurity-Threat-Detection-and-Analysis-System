import { Link, Navigate } from 'react-router-dom';
import logo from '../assets/logo.svg';
import { useAuth } from '../context/AuthContext.js';

function GoogleIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      aria-hidden="true"
      className="shrink-0"
    >
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"
      />
    </svg>
  );
}

function Spinner() {
  return (
    <div className="flex h-full min-h-screen items-center justify-center bg-surface-base">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-surface-border border-t-accent-primary" />
    </div>
  );
}

export default function Login() {
  const { user, loading } = useAuth();

  if (loading) return <Spinner />;

  // Already signed in → go straight to dashboard
  if (user?.authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const googleEnabled = user?.google_enabled ?? false;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-base px-4">
      {/* Logo */}
      <div className="mb-8 flex items-center gap-3">
        <img src={logo} alt="SecureVision" className="h-12 w-12" />
        <span className="text-2xl font-bold text-content-primary tracking-tight">
          SecureVision
        </span>
      </div>

      {/* Card */}
      <div className="card w-full max-w-sm p-8 text-center">
        <h1 className="mb-2 text-2xl font-bold text-content-primary">
          Welcome to SecureVision
        </h1>
        <p className="mb-6 text-sm text-content-secondary">
          Intelligent cybersecurity threat detection.
        </p>

        {googleEnabled ? (
          <div className="flex flex-col gap-3">
            {/* Google sign-in — full navigation so OAuth redirect works */}
            <a
              href="/auth/google/login"
              className="flex items-center justify-center gap-3 rounded px-4 py-2.5 font-medium text-white transition-opacity hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2"
              style={{ backgroundColor: '#4285F4' }}
            >
              <GoogleIcon />
              Continue with Google
            </a>

            <Link to="/dashboard" className="btn-ghost text-sm">
              Continue as guest
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="rounded border border-surface-muted bg-surface-overlay px-4 py-3 text-sm text-content-muted">
              Sign-in not configured — running in guest mode.
            </div>
            <Link to="/dashboard" className="btn-ghost">
              Open Dashboard
            </Link>
          </div>
        )}

        <p className="mt-6 text-xs text-content-disabled leading-relaxed">
          Signing in lets you scan your Gmail inbox. Your scan results are private to your
          account. We only request read-only email access when you explicitly connect Gmail.
        </p>
      </div>

      <p className="mt-6 text-xs text-content-disabled">
        No account required for URL, message, or APK scanning.
      </p>
    </div>
  );
}
