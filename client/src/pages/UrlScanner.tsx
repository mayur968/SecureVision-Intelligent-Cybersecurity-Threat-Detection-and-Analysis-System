import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api/client.js';
import type { ScanResult, LiveScanVerdict, LiveScanResult } from '../types/index.js';
import ScanResultCard from '../components/ui/ScanResultCard.js';
import ConfidenceBar from '../components/ui/ConfidenceBar.js';
import ExplanationPanel from '../components/ui/ExplanationPanel.js';
import RecommendationList from '../components/ui/RecommendationList.js';

type ScanMode = 'quick' | 'live';

// ── Stepper ──────────────────────────────────────────────────────────────────
const STEPS: { label: string; desc: string }[] = [
  { label: 'Queued',       desc: 'Waiting for a worker slot' },
  { label: 'Visiting',     desc: 'Browser opening the page'  },
  { label: 'Analysing',    desc: 'Collecting evidence'       },
  { label: 'Complete',     desc: 'Verdict ready'             },
];

function stepIndex(status: string, extra: boolean) {
  if (status === 'queued')  return 0;
  if (status === 'running') return extra ? 2 : 1;
  if (status === 'done')    return 3;
  return 0;
}

function LiveStepper({ status }: { status: string }) {
  const [extra, setExtra] = useState(false);
  useEffect(() => {
    if (status !== 'running') { setExtra(false); return; }
    const t = setTimeout(() => setExtra(true), 4000);
    return () => clearTimeout(t);
  }, [status]);

  const active = stepIndex(status, extra);

  return (
    <div className="flex items-center gap-0">
      {STEPS.map((step, i) => {
        const done = i < active;
        const cur  = i === active;
        return (
          <div key={step.label} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div className={`flex h-7 w-7 items-center justify-center rounded-full border text-xs font-bold transition-all duration-200 ${
                done ? 'border-sev-low bg-sev-low text-surface-base'
                     : cur  ? 'border-accent bg-accent-subtle text-accent-glow'
                             : 'border-surface-muted bg-surface-overlay text-content-disabled'
              }`}>
                {done ? (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="m2 6 3 3 5-5"/>
                  </svg>
                ) : cur ? (
                  <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-accent-glow border-t-transparent" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-surface-muted" />
                )}
              </div>
              <span className={`text-2xs whitespace-nowrap transition-colors ${
                cur ? 'text-accent-glow font-medium' : done ? 'text-content-secondary' : 'text-content-disabled'
              }`}>
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`mx-1.5 mb-4 h-px w-10 transition-colors ${i < active ? 'bg-sev-low' : 'bg-surface-muted'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Verdict badge ─────────────────────────────────────────────────────────────
const VERDICT_CFG: Record<LiveScanVerdict, { label: string; cls: string; dot: string }> = {
  PHISHING:         { label: 'PHISHING',          cls: 'border-sev-critical/40 bg-sev-critical-bg text-sev-critical', dot: 'bg-sev-critical' },
  SUSPICIOUS:       { label: 'SUSPICIOUS',         cls: 'border-sev-medium/40  bg-sev-medium-bg  text-sev-medium',   dot: 'bg-sev-medium'   },
  LIKELY_SAFE:      { label: 'LIKELY SAFE',        cls: 'border-sev-low/40    bg-sev-low-bg    text-sev-low',       dot: 'bg-sev-low'      },
  COULD_NOT_VERIFY: { label: 'COULD NOT VERIFY',   cls: 'border-surface-muted bg-surface-overlay text-content-secondary', dot: 'bg-content-muted' },
};

function VerdictBadge({ verdict }: { verdict: LiveScanVerdict }) {
  const cfg = VERDICT_CFG[verdict] ?? VERDICT_CFG.COULD_NOT_VERIFY;
  return (
    <div className={`flex items-center justify-center gap-2 rounded border-2 px-6 py-3 ${cfg.cls}`}>
      <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
      <span className="font-mono text-base font-bold tracking-widest">{cfg.label}</span>
    </div>
  );
}

// ── Evidence icon ─────────────────────────────────────────────────────────────
function EvidenceIcon({ text }: { text: string }) {
  const t = text.toLowerCase();
  if (/password|card|brand|form|impersonat/.test(t))
    return <span className="h-1.5 w-1.5 mt-1.5 shrink-0 rounded-full bg-sev-critical" />;
  if (/redirect|https|http/.test(t))
    return <span className="h-1.5 w-1.5 mt-1.5 shrink-0 rounded-full bg-sev-medium" />;
  return <span className="h-1.5 w-1.5 mt-1.5 shrink-0 rounded-full bg-sev-info" />;
}

function truncUrl(url: string, max = 64) {
  return url.length > max ? url.slice(0, max) + '…' : url;
}

// ── Live result ───────────────────────────────────────────────────────────────
function LiveResult({ result, entered }: { result: LiveScanResult; entered: string }) {
  const urlChanged = result.final_url && result.final_url !== entered;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="space-y-4">
      {/* Verdict */}
      <VerdictBadge verdict={result.verdict} />

      {/* ML fallback notice */}
      {result.ml_fallback && (
        <div className="flex items-center gap-2 rounded border border-sev-medium/30 bg-sev-medium-bg px-4 py-2.5 text-sm text-sev-medium">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><circle cx="7" cy="7" r="5.5"/><path d="M7 4.5v3M7 9.5h.01"/></svg>
          Live scan could not verify — showing static analysis only
        </div>
      )}

      {/* Main details card */}
      <div className="card p-5 space-y-4">
        <ConfidenceBar value={result.combined_score / 100} label="Combined risk score" />

        {/* URL diff */}
        <div>
          <p className="section-label mb-1.5">URL</p>
          {urlChanged ? (
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="text-content-secondary">{truncUrl(entered)}</span>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="#475569" strokeWidth="1.5" strokeLinecap="round"><path d="m5 3 4 3-4 3"/></svg>
              <span className="rounded bg-sev-medium-bg px-1.5 py-0.5 text-sev-medium font-semibold">{truncUrl(result.final_url)}</span>
            </div>
          ) : (
            <p className="font-mono text-xs text-content-secondary">{truncUrl(entered)}</p>
          )}
        </div>

        {result.title && (
          <div>
            <p className="section-label mb-1">Page Title</p>
            <p className="text-sm text-content-secondary">{result.title}</p>
          </div>
        )}

        <div className="flex items-center gap-4 text-xs text-content-muted">
          <span>Load time: <span className="font-mono text-content-secondary">{result.load_time_ms}ms</span></span>
          {result.redirect_chain.length > 0 && (
            <span>Redirects: <span className="font-mono text-content-secondary">{result.redirect_chain.length}</span></span>
          )}
        </div>
      </div>

      {/* Redirect chain */}
      {result.redirect_chain.length > 0 && (
        <div className="card p-4">
          <p className="section-label mb-3">Redirect Chain</p>
          <ol className="space-y-2">
            {result.redirect_chain.map((hop, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <div className="flex flex-col items-center gap-0.5">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-overlay font-mono text-2xs text-content-muted">{i + 1}</span>
                  {i < result.redirect_chain.length - 1 && <span className="w-px flex-1 bg-surface-border" style={{ minHeight: 8 }} />}
                </div>
                <span className="font-mono text-xs text-content-secondary break-all pt-0.5">{truncUrl(hop, 80)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Evidence */}
      {result.evidence.length > 0 && (
        <div className="card p-4">
          <p className="section-label mb-3 text-sev-medium">Evidence</p>
          <ul className="space-y-2">
            {result.evidence.map((ev, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-content-secondary">
                <EvidenceIcon text={ev} />
                {ev}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Screenshot */}
      {result.screenshot_b64 && (
        <div className="card overflow-hidden">
          <div className="flex items-center gap-2 border-b border-surface-border bg-sev-medium-bg px-4 py-2">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round"><circle cx="6" cy="6" r="4.5"/><path d="M6 3.5v2.5l1.5 1"/></svg>
            <p className="text-xs font-medium text-sev-medium">
              Screenshot taken in an isolated sandbox — do not trust this page
            </p>
          </div>
          <img
            src={`data:image/jpeg;base64,${result.screenshot_b64}`}
            alt="Sandboxed page screenshot"
            className="w-full"
            loading="lazy"
          />
        </div>
      )}

      {result.explanation && <ExplanationPanel explanation={result.explanation} />}
      {result.recommendations?.length > 0 && <RecommendationList recommendations={result.recommendations} />}
    </motion.div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
const EXAMPLES = ['https://www.google.com', 'http://paypa1-secure.tk/login', 'https://httpbin.org/redirect/2'];

export default function UrlScanner() {
  const [url, setUrl]           = useState('');
  const [error, setError]       = useState('');
  const [mode, setMode]         = useState<ScanMode>('quick');
  const [jobId, setJobId]       = useState<string | null>(null);
  const [blockedErr, setBlockedErr] = useState(false);

  const mutation   = useMutation({ mutationFn: api.scanUrl });
  const liveMutation = useMutation({
    mutationFn: api.startLiveScan,
    onSuccess: d => { setJobId(d.job_id); setBlockedErr(false); },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: string }; status?: number } };
      if (e?.response?.status === 400 || /cannot be scanned|safety|private/i.test(e?.response?.data?.error ?? ''))
        setBlockedErr(true);
    },
  });

  const { data: jobData, isError: jobErr } = useQuery({
    queryKey: ['liveJob', jobId],
    queryFn:  () => api.getLiveScanJob(jobId!),
    refetchInterval: q => ['done','failed'].includes(q.state.data?.status ?? '') ? false : 1500,
    enabled:  !!jobId,
  });

  function validate(v: string) {
    if (!v.trim()) return 'URL is required';
    if (v.length > 2048) return 'URL too long (max 2048 chars)';
    try { new URL(v); return ''; } catch { return 'Enter a valid URL including https://'; }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validate(url);
    if (err) { setError(err); return; }
    setError('');
    if (mode === 'quick') {
      mutation.mutate(url.trim());
    } else {
      setJobId(null); setBlockedErr(false); liveMutation.mutate(url.trim());
    }
  }

  function reset() {
    mutation.reset(); liveMutation.reset(); setJobId(null); setBlockedErr(false); setError('');
  }

  const isPhishing   = mutation.data?.prediction === 'PHISHING';
  const isBlocked    = blockedErr || jobErr;
  const jobFailed    = jobData?.status === 'failed';
  const jobDone      = jobData?.status === 'done' && !!jobData.result;
  const jobPending   = !!jobId && !jobDone && !jobFailed;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-content-primary">URL Scanner</h1>
        <p className="mt-1 text-sm text-content-muted">
          Analyse URLs for phishing indicators — typosquatting, TLD risk, domain age and more.
        </p>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-0 rounded-md border border-surface-muted bg-surface-raised p-0.5 w-fit">
        {([['quick', 'Quick Scan'], ['live', 'Live Scan']] as const).map(([m, label]) => (
          <button key={m} type="button" onClick={() => { setMode(m); reset(); }}
            className={`rounded px-4 py-1.5 text-sm font-medium transition-all duration-150 ${
              mode === m
                ? 'bg-accent text-white shadow-glow-sm'
                : 'text-content-secondary hover:text-content-primary'
            }`}>
            {label}
            {m === 'live' && <span className="ml-1.5 rounded-sm bg-surface-overlay px-1 py-0.5 text-2xs text-content-muted">visits site</span>}
          </button>
        ))}
      </div>

      {/* Input card */}
      <div className="card p-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="url-input" className="mb-1.5 block text-sm font-medium text-content-secondary">
              Target URL
            </label>
            <div className="flex gap-2.5">
              <input
                id="url-input"
                type="text"
                value={url}
                onChange={e => { setUrl(e.target.value); setError(''); }}
                placeholder="https://example.com/path"
                className={`input flex-1 font-mono ${error ? '!border-sev-critical' : ''}`}
              />
              <button type="submit"
                disabled={mutation.isPending || liveMutation.isPending}
                className="btn-primary px-5 shrink-0">
                {mutation.isPending || liveMutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Scanning
                  </span>
                ) : 'Scan'}
              </button>
            </div>
            {error && <p className="mt-1 text-xs text-sev-critical">{error}</p>}
          </div>

          {mode === 'live' && (
            <p className="flex items-center gap-1.5 text-xs text-content-muted">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><circle cx="6" cy="6" r="4.5"/><path d="M6 3.5v2.5l1.5 1"/></svg>
              The Live Scanner visits the URL from our server in an isolated browser. The site may detect the visit.
            </p>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <span className="section-label">Examples:</span>
            {EXAMPLES.map(ex => (
              <button key={ex} type="button"
                onClick={() => { setUrl(ex); setError(''); reset(); }}
                className="rounded border border-surface-muted px-2 py-0.5 font-mono text-xs text-content-secondary hover:border-accent/50 hover:text-accent-glow transition-colors">
                {ex.length > 38 ? ex.slice(0, 38) + '…' : ex}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* ── Quick scan results ────────────────────────────────────────── */}
      {mode === 'quick' && (
        <>
          <AnimatePresence>
            {mutation.isPending && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="card flex items-center gap-3 p-5">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                <span className="text-sm text-content-muted">Analysing URL…</span>
              </motion.div>
            )}
          </AnimatePresence>

          {mutation.data && !mutation.isPending && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              {isPhishing && (
                <div className="flex items-center gap-3 rounded border border-sev-critical/40 bg-sev-critical-bg px-4 py-3">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"><path d="m8 2 7 12H1L8 2Z"/><path d="M8 7v3M8 12h.01"/></svg>
                  <p className="text-sm font-semibold text-sev-critical">Phishing URL detected — do not visit this site</p>
                </div>
              )}
              <ScanResultCard result={mutation.data as ScanResult} title="URL Analysis" />
            </motion.div>
          )}

          {mutation.isError && (
            <div className="card border-sev-critical/30 bg-sev-critical-bg p-4 text-sm text-sev-critical">
              Scan failed — make sure the ML service is running.
            </div>
          )}
        </>
      )}

      {/* ── Live scan results ─────────────────────────────────────────── */}
      {mode === 'live' && (
        <>
          {isBlocked && !jobFailed && (
            <div className="flex items-center gap-2.5 rounded border border-sev-medium/30 bg-sev-medium-bg px-4 py-3 text-sm text-sev-medium">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><circle cx="7" cy="7" r="5.5"/><path d="M7 4.5v3M7 9.5h.01"/></svg>
              This address cannot be scanned for safety reasons.
            </div>
          )}

          {liveMutation.isError && !isBlocked && (
            <div className="card border-sev-critical/30 bg-sev-critical-bg p-4 text-sm text-sev-critical">
              Scan failed — make sure the ML service is running.
            </div>
          )}

          {jobPending && (
            <div className="card p-6 space-y-5">
              <div className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                <p className="text-sm text-content-secondary">Live scan in progress…</p>
              </div>
              <LiveStepper status={jobData?.status ?? 'queued'} />
            </div>
          )}

          {jobFailed && (
            <div className="card border-sev-critical/30 bg-sev-critical-bg p-4 text-sm text-sev-critical">
              {jobData?.error ?? 'Live scan failed.'}
            </div>
          )}

          {jobDone && jobData?.result && (
            <LiveResult result={jobData.result} entered={url} />
          )}
        </>
      )}
    </div>
  );
}
