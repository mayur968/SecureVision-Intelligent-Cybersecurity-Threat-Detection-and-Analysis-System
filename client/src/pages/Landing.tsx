import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useMutation } from '@tanstack/react-query';
import { api } from '../api/client.js';
import type { ScanResult } from '../types/index.js';
import logo from '../assets/logo.svg';

// ── Animation variants ─────────────────────────────────────────────────────
const cardContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const cardItem = {
  hidden: { opacity: 0, y: 16 },
  show:   { opacity: 1, y: 0 },
};

// ── Inline icons ───────────────────────────────────────────────────────────
const Icons = {
  Link: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 12a4.42 4.42 0 0 0 6.25 0l2.5-2.5a4.42 4.42 0 0 0-6.25-6.25l-1.375 1.375"/>
      <path d="M12 8a4.42 4.42 0 0 0-6.25 0L3.25 10.5a4.42 4.42 0 0 0 6.25 6.25l1.375-1.375"/>
    </svg>
  ),
  Wifi: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12.55a11 11 0 0 1 14.08 0"/>
      <path d="M1.42 9a16 16 0 0 1 17.16 0"/>
      <path d="M8.53 16.11a6 6 0 0 1 2.94 0"/>
      <circle cx="10" cy="18" r="0.6" fill="currentColor"/>
    </svg>
  ),
  Message: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.5 2.5h-15a1.25 1.25 0 0 0-1.25 1.25v10a1.25 1.25 0 0 0 1.25 1.25H6.25L10 18.75l3.75-3.75h3.75a1.25 1.25 0 0 0 1.25-1.25v-10a1.25 1.25 0 0 0-1.25-1.25Z"/>
      <path d="M6.25 7.5h7.5M6.25 11.25h5"/>
    </svg>
  ),
  Package: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16.5 3.5h-13a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h13a1 1 0 0 0 1-1v-11a1 1 0 0 0-1-1Z"/>
      <path d="M7.5 5.5h5M7.5 8.75h5M7.5 12h3"/>
      <circle cx="12.5" cy="12.25" r="1.25" fill="currentColor" stroke="none"/>
    </svg>
  ),
  Lightbulb: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 2a6 6 0 0 1 6 6c0 2.5-1.5 4.6-3.75 5.5V15h-4.5v-1.5C5.5 12.6 4 10.5 4 8a6 6 0 0 1 6-6Z"/>
      <path d="M7.75 15h4.5M8.5 17.5h3"/>
    </svg>
  ),
  Clock: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="8.25"/>
      <path d="M10 5.75V10l3.125 1.875"/>
    </svg>
  ),
  Lock: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="7" width="10" height="8" rx="1.5"/>
      <path d="M5 7V5a3 3 0 0 1 6 0v2"/>
    </svg>
  ),
  Arrow: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 8h10M9 4l4 4-4 4"/>
    </svg>
  ),
  Menu: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M3 5h14M3 10h14M3 15h14"/>
    </svg>
  ),
  X: () => (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M4 4l12 12M16 4 4 16"/>
    </svg>
  ),
};

// ── Feature card data ──────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: <Icons.Link />,
    title: 'URL Scanner',
    desc: 'Detect phishing and malicious URLs with ML + rule-based analysis.',
  },
  {
    icon: <Icons.Wifi />,
    title: 'Live Scan',
    desc: 'Browser-based live page analysis with screenshot and redirect chain.',
  },
  {
    icon: <Icons.Message />,
    title: 'Message & Email Scanner',
    desc: 'Analyse SMS, chat, and email text for phishing indicators.',
  },
  {
    icon: <Icons.Package />,
    title: 'APK Static Analysis',
    desc: 'Inspect Android APKs for permissions, certificates, and malicious patterns.',
  },
  {
    icon: <Icons.Lightbulb />,
    title: 'Explainable Results',
    desc: 'Every verdict comes with feature-level explanation and actionable recommendations.',
  },
  {
    icon: <Icons.Clock />,
    title: 'Scan History',
    desc: 'Full history of your scans with risk trends and statistics.',
  },
];

// ── How it works steps ─────────────────────────────────────────────────────
const HOW_IT_WORKS = [
  {
    num: 1,
    title: 'Submit',
    desc: 'Paste a URL, message, or upload an APK file.',
  },
  {
    num: 2,
    title: 'Extract Features',
    desc: 'Domain age, redirects, lexical patterns, and more are extracted.',
  },
  {
    num: 3,
    title: 'ML + Rules',
    desc: 'A trained logistic-regression model and rule engine score the input.',
  },
  {
    num: 4,
    title: 'Explanation & Recommendations',
    desc: 'Verdict, confidence score, and specific indicators are returned.',
  },
];

// ── Verdict chip helper ────────────────────────────────────────────────────
function verdictChipClass(prediction: string): string {
  if (prediction === 'SAFE')      return 'bg-sev-low text-surface-base';
  if (prediction === 'PHISHING' || prediction === 'MALICIOUS') return 'bg-sev-critical text-white';
  return 'bg-sev-medium text-white';
}

// ── Main Landing component ─────────────────────────────────────────────────
export default function Landing() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [quickUrl, setQuickUrl]     = useState('');

  const navigate = useNavigate();

  const scanMutation = useMutation<ScanResult, Error, string>({
    mutationFn: (url: string) => api.scanUrl(url),
  });

  function handleQuickScan(e: React.FormEvent) {
    e.preventDefault();
    if (!quickUrl.trim()) return;
    scanMutation.mutate(quickUrl.trim());
  }

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    setMobileOpen(false);
  }

  return (
    <div className="min-h-screen bg-surface-base text-content-primary">

      {/* ── SECTION A: Sticky nav ──────────────────────────────────────── */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-surface-raised/80 border-b border-surface-border">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <img src={logo} alt="SecureVision" className="h-7 w-7 shrink-0" />
            <span className="text-sm font-semibold text-content-primary tracking-tight">
              SecureVision
            </span>
          </div>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-6">
            <button
              onClick={() => scrollTo('features')}
              className="text-sm text-content-secondary hover:text-accent-glow transition-colors"
            >
              Features
            </button>
            <button
              onClick={() => scrollTo('how-it-works')}
              className="text-sm text-content-secondary hover:text-accent-glow transition-colors"
            >
              How it works
            </button>
            <Link to="/dashboard" className="btn-primary text-sm px-3 py-1.5">
              Open App
            </Link>
            <Link to="/login" className="text-sm text-accent hover:text-accent-hover transition-colors">
              Sign in
            </Link>
          </nav>

          {/* Mobile hamburger */}
          <button
            className="md:hidden text-content-secondary hover:text-content-primary"
            onClick={() => setMobileOpen(v => !v)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileOpen ? <Icons.X /> : <Icons.Menu />}
          </button>
        </div>

        {/* Mobile nav dropdown */}
        {mobileOpen && (
          <div className="md:hidden border-t border-surface-border bg-surface-raised px-4 py-3 flex flex-col gap-3">
            <button
              onClick={() => scrollTo('features')}
              className="text-sm text-left text-content-secondary hover:text-accent-glow transition-colors"
            >
              Features
            </button>
            <button
              onClick={() => scrollTo('how-it-works')}
              className="text-sm text-left text-content-secondary hover:text-accent-glow transition-colors"
            >
              How it works
            </button>
            <Link to="/dashboard" className="btn-primary text-sm text-center" onClick={() => setMobileOpen(false)}>
              Open App
            </Link>
            <Link to="/login" className="text-sm text-accent" onClick={() => setMobileOpen(false)}>
              Sign in
            </Link>
          </div>
        )}
      </header>

      {/* ── SECTION B: Hero ───────────────────────────────────────────── */}
      <section className="mx-auto max-w-4xl px-4 pt-20 pb-16 text-center sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <h1 className="text-4xl lg:text-5xl font-bold text-content-primary leading-tight mb-4">
            Detect threats before they reach you
          </h1>
          <p className="text-lg text-content-secondary mb-8 max-w-2xl mx-auto">
            AI-powered phishing, malware, and email threat detection — no account required.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link to="/dashboard" className="btn-primary px-6 py-2.5 text-base">
              Open Dashboard
            </Link>
            <Link to="/scan/url" className="btn-ghost px-6 py-2.5 text-base">
              Try URL Scanner
            </Link>
          </div>
        </motion.div>
      </section>

      {/* ── SECTION C: Quick-scan strip ───────────────────────────────── */}
      <section className="mx-auto max-w-2xl px-4 pb-16 sm:px-6">
        <p className="section-label text-center mb-4">
          Instant URL check — no account needed
        </p>
        <form onSubmit={handleQuickScan} className="flex gap-2">
          <input
            className="input flex-1"
            type="url"
            placeholder="https://example.com"
            value={quickUrl}
            onChange={e => setQuickUrl(e.target.value)}
            aria-label="URL to scan"
          />
          <button
            type="submit"
            className="btn-primary shrink-0"
            disabled={scanMutation.isPending || !quickUrl.trim()}
          >
            {scanMutation.isPending ? (
              <span className="animate-spin border-2 border-accent-glow border-t-transparent rounded-full inline-block h-4 w-4" />
            ) : (
              'Scan'
            )}
          </button>
        </form>

        {/* Result area */}
        <div className="mt-3 min-h-[2rem] text-center">
          {scanMutation.isIdle && (
            <p className="text-xs text-content-disabled">Enter a URL above to get an instant verdict.</p>
          )}
          {scanMutation.isPending && (
            <p className="text-xs text-content-muted">Analysing URL…</p>
          )}
          {scanMutation.isError && (
            <p className="text-xs text-sev-critical">{scanMutation.error?.message ?? 'Scan failed. Please try again.'}</p>
          )}
          {scanMutation.isSuccess && scanMutation.data && (
            <div className="flex items-center justify-center gap-2">
              <span className={`chip px-3 py-1 text-xs font-semibold ${verdictChipClass(scanMutation.data.prediction)}`}>
                {scanMutation.data.prediction}
              </span>
              <span className="text-xs text-content-muted">
                {Math.round(scanMutation.data.confidence * 100)}% confidence
              </span>
            </div>
          )}
        </div>
      </section>

      {/* ── SECTION D: Feature cards ──────────────────────────────────── */}
      <section id="features" className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-bold text-content-primary text-center mb-10">Features</h2>
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          variants={cardContainer}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.1 }}
        >
          {FEATURES.map(f => (
            <motion.div key={f.title} variants={cardItem} className="card p-5">
              <div className="mb-3 text-accent-glow">{f.icon}</div>
              <h3 className="font-semibold text-content-primary mb-1">{f.title}</h3>
              <p className="text-sm text-content-secondary leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ── SECTION E: How it works ───────────────────────────────────── */}
      <section id="how-it-works" className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-bold text-content-primary text-center mb-10">How it works</h2>
        <div className="flex flex-wrap gap-4 items-center justify-center">
          {HOW_IT_WORKS.map((step, i) => (
            <div key={step.num} className="flex items-center gap-4">
              {/* Step card */}
              <div className="flex flex-col items-center text-center max-w-[140px]">
                <div className="h-8 w-8 rounded-full bg-accent flex items-center justify-center text-white font-bold text-sm mb-3 shrink-0">
                  {step.num}
                </div>
                <h3 className="font-semibold text-content-primary text-sm mb-1">{step.title}</h3>
                <p className="text-xs text-content-secondary leading-relaxed">{step.desc}</p>
              </div>
              {/* Arrow between steps */}
              {i < HOW_IT_WORKS.length - 1 && (
                <span className="hidden md:block text-content-disabled shrink-0">
                  <Icons.Arrow />
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION F: Privacy & Safety ──────────────────────────────── */}
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <h2 className="text-2xl font-bold text-content-primary text-center mb-8">Privacy &amp; Safety</h2>
        <div className="space-y-4">
          {[
            'APKs are analysed statically — they are never executed in any environment.',
            'URLs are not visited during Quick Scan — only the URL string itself is analysed by ML and rule-based checks.',
            'Email bodies are not stored — only verdict, risk score, indicators, and a subject snippet are retained.',
          ].map(text => (
            <div key={text} className="flex items-start gap-3 card p-4">
              <span className="text-sev-low mt-0.5 shrink-0"><Icons.Lock /></span>
              <p className="text-sm text-content-secondary leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION G: Footer ─────────────────────────────────────────── */}
      <footer className="border-t border-surface-border bg-surface-raised">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 py-8 text-center sm:flex-row sm:justify-between sm:px-6">
          <div className="flex items-center gap-2">
            <img src={logo} alt="" className="h-5 w-5 opacity-60" aria-hidden="true" />
            <span className="text-xs text-content-disabled">© 2024 SecureVision</span>
          </div>
          <nav className="flex gap-6">
            <a
              href="#features"
              onClick={e => { e.preventDefault(); scrollTo('features'); }}
              className="text-sm text-content-secondary hover:text-accent-glow transition-colors"
            >
              About
            </a>
            <a
              href="https://scikit-learn.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-content-secondary hover:text-accent-glow transition-colors"
            >
              Models
            </a>
            <a
              href="https://github.com/mayur968/SecureVision-Intelligent-Cybersecurity-Threat-Detection-and-Analysis-System"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-content-secondary hover:text-accent-glow transition-colors"
            >
              GitHub
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
