import { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api/client.js';
import type { ScanResult, LiveScanVerdict, LiveScanResult } from '../types/index.js';
import ScanResultCard from '../components/ui/ScanResultCard.js';
import ConfidenceBar from '../components/ui/ConfidenceBar.js';
import ExplanationPanel from '../components/ui/ExplanationPanel.js';
import RecommendationList from '../components/ui/RecommendationList.js';

type ScanMode = 'Quick Scan' | 'Live Scan';

// ── Stepper ──────────────────────────────────────────────────────────────────

const STEPS = ['Queued', 'Visiting Site', 'Analyzing', 'Done'] as const;

function stepIndexFromStatus(
  status: 'queued' | 'running' | 'done' | 'failed',
  runningExtra: boolean,
): number {
  if (status === 'queued')  return 0;
  if (status === 'running') return runningExtra ? 2 : 1;
  if (status === 'done')    return 3;
  return 0;
}

function LiveStepper({ status }: { status: 'queued' | 'running' | 'done' | 'failed' }) {
  const [runningExtra, setRunningExtra] = useState(false);

  useEffect(() => {
    if (status !== 'running') { setRunningExtra(false); return; }
    const t = setTimeout(() => setRunningExtra(true), 4000);
    return () => clearTimeout(t);
  }, [status]);

  const activeIdx = stepIndexFromStatus(status, runningExtra);

  return (
    <div className="flex items-center gap-0">
      {STEPS.map((label, i) => {
        const isActive   = i === activeIdx;
        const isComplete = i < activeIdx;
        return (
          <div key={label} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors ${
                isComplete
                  ? 'border-cyan-500 bg-cyan-500 text-slate-900'
                  : isActive
                    ? 'border-cyan-500 bg-slate-900 text-cyan-400'
                    : 'border-slate-700 bg-slate-800 text-slate-600'
              }`}>
                {isComplete ? (
                  <span className="text-xs font-bold">✓</span>
                ) : isActive ? (
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
                ) : (
                  <span className="h-2 w-2 rounded-full bg-slate-600" />
                )}
              </div>
              <span className={`text-xs whitespace-nowrap ${
                isActive ? 'text-cyan-400' : isComplete ? 'text-slate-300' : 'text-slate-600'
              }`}>
                {label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`mx-1 mb-5 h-0.5 w-10 transition-colors ${
                i < activeIdx ? 'bg-cyan-500' : 'bg-slate-700'
              }`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Verdict badge ─────────────────────────────────────────────────────────────

const verdictConfig: Record<LiveScanVerdict, { text: string; cls: string }> = {
  PHISHING:          { text: '🚨 PHISHING',          cls: 'border-red-500    bg-red-950    text-red-400'   },
  SUSPICIOUS:        { text: '⚠ SUSPICIOUS',         cls: 'border-amber-500  bg-amber-950  text-amber-400' },
  LIKELY_SAFE:       { text: '✔ LIKELY SAFE',         cls: 'border-green-500  bg-green-950  text-green-400' },
  COULD_NOT_VERIFY:  { text: 'ℹ COULD NOT VERIFY',   cls: 'border-slate-400  bg-slate-800  text-slate-400' },
};

// ── Evidence severity ─────────────────────────────────────────────────────────

function evidenceIcon(text: string): string {
  const t = text.toLowerCase();
  if (/password|card|brand|form/.test(t)) return '🔴';
  if (/redirect|https/.test(t))           return '🟡';
  if (/iframe/.test(t))                   return 'ℹ️';
  return 'ℹ️';
}

// ── Truncate URL ──────────────────────────────────────────────────────────────

function truncUrl(url: string, max = 60): string {
  return url.length > max ? url.slice(0, max) + '…' : url;
}

// ── Live result view ──────────────────────────────────────────────────────────

function LiveResultView({ result, enteredUrl }: { result: LiveScanResult; enteredUrl: string }) {
  const vc = verdictConfig[result.verdict] ?? verdictConfig.COULD_NOT_VERIFY;
  const urlChanged = result.final_url && result.final_url !== enteredUrl;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35 }}
      className="space-y-4"
    >
      {/* Verdict badge */}
      <div className={`w-full rounded-xl border-2 px-6 py-4 text-center text-xl font-bold tracking-widest ${vc.cls}`}>
        {vc.text}
      </div>

      {/* ML fallback notice */}
      {result.ml_fallback && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-700 bg-amber-950/40 px-4 py-3 text-sm text-amber-400">
          <span>⚠</span>
          <span>Live scan could not verify — showing static analysis only</span>
        </div>
      )}

      {/* Combined score */}
      <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 space-y-4">
        <ConfidenceBar value={result.combined_score / 100} label="Combined score" />

        {/* URL row */}
        {urlChanged ? (
          <div className="space-y-1">
            <p className="text-xs text-slate-400">URL</p>
            <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
              <span className="text-slate-300">{truncUrl(enteredUrl)}</span>
              <span className="text-slate-500">→</span>
              <span className="text-amber-400 font-semibold">{truncUrl(result.final_url)}</span>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-xs text-slate-400">URL</p>
            <p className="font-mono text-xs text-slate-300">{truncUrl(enteredUrl)}</p>
          </div>
        )}

        {/* Page title */}
        {result.title && (
          <div>
            <p className="text-xs text-slate-400">Page title</p>
            <p className="text-sm text-slate-300">{result.title}</p>
          </div>
        )}
      </div>

      {/* Redirect chain */}
      {result.redirect_chain.length > 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-cyan-400">
            Redirect Chain
          </h3>
          <ol className="space-y-2">
            {result.redirect_chain.map((hop, i) => (
              <li key={i} className="flex items-start gap-2 text-xs font-mono">
                <span className="shrink-0 text-cyan-500">→</span>
                <span className="text-slate-300 break-all">{truncUrl(hop, 80)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Evidence */}
      {result.evidence.length > 0 && (
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-amber-400">
            Evidence
          </h3>
          <ul className="space-y-2">
            {result.evidence.map((ev, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                <span className="shrink-0">{evidenceIcon(ev)}</span>
                <span>{ev}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Screenshot */}
      {result.screenshot_b64 && (
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-4 space-y-2">
          <p className="text-xs text-amber-400 font-semibold">
            Screenshot taken in an isolated sandbox. Do not trust the page.
          </p>
          <img
            src={`data:image/jpeg;base64,${result.screenshot_b64}`}
            alt="Site screenshot"
            className="w-full rounded-lg border border-slate-700"
          />
        </div>
      )}

      {/* Explanation */}
      {result.explanation && <ExplanationPanel explanation={result.explanation} />}

      {/* Recommendations */}
      {result.recommendations?.length > 0 && (
        <RecommendationList recommendations={result.recommendations} />
      )}
    </motion.div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function UrlScanner() {
  const [url, setUrl]       = useState('');
  const [error, setError]   = useState('');
  const [mode, setMode]     = useState<ScanMode>('Quick Scan');
  const [jobId, setJobId]   = useState<string | null>(null);
  const [blockedErr, setBlockedErr] = useState(false);

  // Quick Scan mutation
  const mutation = useMutation({ mutationFn: api.scanUrl });

  // Live Scan — start job
  const liveMutation = useMutation({
    mutationFn: api.startLiveScan,
    onSuccess: (data) => { setJobId(data.job_id); setBlockedErr(false); },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { error?: string }; status?: number } });
      const status = msg?.response?.status;
      const text   = msg?.response?.data?.error ?? '';
      if (
        status === 400 ||
        /cannot be scanned|Safety check failed|private/.test(text)
      ) {
        setBlockedErr(true);
      } else {
        setBlockedErr(false);
      }
    },
  });

  // Live Scan — poll job
  const { data: jobData, isError: isJobError } = useQuery({
    queryKey: ['liveJob', jobId],
    queryFn: () => api.getLiveScanJob(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'done' || status === 'failed' ? false : 1500;
    },
    enabled: !!jobId,
  });

  function validate(v: string) {
    if (!v.trim()) return 'URL is required';
    if (v.length > 2048) return 'URL too long (max 2048 chars)';
    try { new URL(v); return ''; }
    catch { return 'Enter a valid URL (include https://)'; }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validate(url);
    if (err) { setError(err); return; }
    setError('');
    if (mode === 'Quick Scan') {
      mutation.mutate(url.trim());
    } else {
      setJobId(null);
      setBlockedErr(false);
      liveMutation.mutate(url.trim());
    }
  }

  function resetAll() {
    mutation.reset();
    liveMutation.reset();
    setJobId(null);
    setBlockedErr(false);
    setError('');
  }

  const isPhishing = mutation.data?.prediction === 'PHISHING';

  // Determine blocked notice for live scan
  const isLiveBlocked =
    blockedErr ||
    (isJobError) ||
    (() => {
      const errMsg = (liveMutation.error as { response?: { data?: { error?: string } } } | null)
        ?.response?.data?.error ?? '';
      return /cannot be scanned|Safety check failed|private/.test(errMsg);
    })();

  const jobFailed  = jobData?.status === 'failed';
  const jobDone    = jobData?.status === 'done' && !!jobData.result;
  const jobPending = !!jobId && !jobDone && !jobFailed;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">URL Scanner</h1>
        <p className="mt-1 text-sm text-slate-400">
          Analyse a URL for phishing indicators — typosquatting, suspicious TLDs, domain age and more.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 rounded-lg border border-slate-700 bg-slate-900 p-1 w-fit">
        {(['Quick Scan', 'Live Scan'] as ScanMode[]).map(m => (
          <button
            key={m}
            type="button"
            onClick={() => { setMode(m); resetAll(); }}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              mode === m
                ? 'bg-cyan-500 text-slate-900'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Input card */}
      <div className="rounded-xl border border-slate-700 bg-slate-900 p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="url" className="mb-1.5 block text-sm font-medium text-slate-300">
              URL to scan
            </label>
            <div className="flex gap-3">
              <input
                id="url"
                type="text"
                value={url}
                onChange={e => { setUrl(e.target.value); setError(''); }}
                placeholder="https://example.com/path?query=value"
                className={`flex-1 rounded-lg border bg-slate-800 px-4 py-2.5 font-mono text-sm text-slate-100 outline-none transition-colors placeholder:text-slate-600 focus:border-cyan-500 ${
                  error ? 'border-red-500' : 'border-slate-700'
                }`}
              />
              <button
                type="submit"
                disabled={mutation.isPending || liveMutation.isPending}
                className="rounded-lg bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {mutation.isPending || liveMutation.isPending ? 'Scanning…' : 'Scan'}
              </button>
            </div>
            {error && <p className="mt-1.5 text-xs text-red-400">{error}</p>}
          </div>

          {/* Live scan consent notice */}
          {mode === 'Live Scan' && (
            <p className="text-xs text-slate-500">
              ℹ The Live Scanner visits the URL from our server in an isolated browser. The site may detect the visit.
            </p>
          )}

          {/* Example URLs */}
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-slate-500">Try:</span>
            {['https://www.google.com', 'http://paypa1-secure.tk/login', 'http://192.168.1.1/verify'].map(ex => (
              <button
                key={ex}
                type="button"
                onClick={() => { setUrl(ex); setError(''); resetAll(); }}
                className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-cyan-400 hover:bg-slate-700"
              >
                {ex.length > 40 ? ex.slice(0, 40) + '…' : ex}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* ── QUICK SCAN results ─────────────────────────────────────────────── */}
      {mode === 'Quick Scan' && (
        <>
          {/* Loading */}
          <AnimatePresence>
            {mutation.isPending && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 p-6">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
                <span className="text-sm text-slate-400">Analysing URL…</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Result */}
          <AnimatePresence>
            {mutation.data && !mutation.isPending && (
              <div className="space-y-4">
                {isPhishing && (
                  <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-3 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3">
                    <span className="text-xl">🚨</span>
                    <p className="text-sm font-semibold text-red-400">
                      Phishing URL detected — do not visit this site.
                    </p>
                  </motion.div>
                )}
                <ScanResultCard result={mutation.data as ScanResult} title="URL Analysis" />
              </div>
            )}
          </AnimatePresence>

          {/* API error */}
          {mutation.isError && (
            <div className="rounded-xl border border-red-800 bg-red-950/30 p-4 text-sm text-red-400">
              Scan failed — make sure the gateway and ML service are running.
            </div>
          )}
        </>
      )}

      {/* ── LIVE SCAN results ──────────────────────────────────────────────── */}
      {mode === 'Live Scan' && (
        <>
          {/* Blocked notice */}
          {isLiveBlocked && !jobFailed && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-700 bg-amber-950/40 px-4 py-3 text-sm text-amber-400">
              <span>⚠</span>
              <span>This address cannot be scanned for safety reasons.</span>
            </div>
          )}

          {/* Generic API error (non-blocked) */}
          {liveMutation.isError && !isLiveBlocked && (
            <div className="rounded-xl border border-red-800 bg-red-950/30 p-4 text-sm text-red-400">
              Scan failed — make sure the gateway and ML service are running.
            </div>
          )}

          {/* Stepper while job is in progress */}
          {jobPending && jobData && (
            <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 space-y-4">
              <p className="text-sm text-slate-400">Live scan in progress…</p>
              <LiveStepper status={jobData.status} />
            </div>
          )}

          {/* Stepper when queued but no jobData yet */}
          {jobPending && !jobData && (
            <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 space-y-4">
              <p className="text-sm text-slate-400">Queuing live scan…</p>
              <div className="flex items-center gap-3">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
              </div>
            </div>
          )}

          {/* Job failed */}
          {jobFailed && (
            <div className="rounded-xl border border-red-800 bg-red-950/30 p-4 text-sm text-red-400">
              {jobData?.error ?? 'Live scan failed.'}
            </div>
          )}

          {/* Done — full result */}
          {jobDone && jobData?.result && (
            <LiveResultView result={jobData.result} enteredUrl={url} />
          )}
        </>
      )}
    </div>
  );
}
