import { useState, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api/client.js';
import type { EmailScanResult } from '../types/index.js';
import RiskBadge from '../components/ui/RiskBadge.js';

function fmt_bytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(2)} MB`;
}

function AuthChip({ label, value }: { label: string; value: string }) {
  const v = value.toLowerCase();
  const cls = v === 'pass'
    ? 'border-sev-low/40 bg-sev-low-bg text-sev-low'
    : v === 'fail' || v === 'softfail'
    ? 'border-sev-critical/40 bg-sev-critical-bg text-sev-critical'
    : 'border-surface-muted bg-surface-overlay text-content-muted';
  return (
    <span className={`chip inline-flex items-center gap-1 rounded border px-2 py-0.5 font-mono text-xs font-semibold ${cls}`}>
      {label}: {value || 'unknown'}
    </span>
  );
}

export default function EmailScanner() {
  const [file, setFile]     = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [result, setResult] = useState<EmailScanResult | null>(null);
  const [error, setError]   = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: (f: File) => api.scanEmail(f),
    onSuccess: (data) => { setResult(data); setError(null); },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: string } } };
      setError(e?.response?.data?.error ?? 'Scan failed. Please try again.');
    },
  });

  function handleFile(f: File | null) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.eml')) {
      setError('Only .eml files are accepted.');
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setError('File too large (max 5 MB).');
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
  }

  function reset() {
    setFile(null); setResult(null); setError(null); mutation.reset();
    if (inputRef.current) inputRef.current.value = '';
  }

  const scanning = mutation.isPending;
  const predColor: Record<string, string> = {
    PHISHING:   'text-sev-critical',
    SUSPICIOUS: 'text-sev-warning',
    SAFE:       'text-sev-low',
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-content-primary">Email Scanner</h1>
        <p className="mt-1 text-sm text-content-muted">
          Upload an .eml file to scan for phishing, spoofing, and malicious links.
        </p>
      </div>

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Drop .eml file here or click to browse"
        onClick={() => inputRef.current?.click()}
        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => {
          e.preventDefault(); setDragOver(false);
          const f = e.dataTransfer.files[0];
          if (f) handleFile(f);
        }}
        className={`card flex cursor-pointer flex-col items-center justify-center gap-3 p-10 transition-colors ${
          dragOver
            ? 'border-accent bg-accent-subtle'
            : 'border-dashed border-surface-border hover:border-accent/50'
        }`}
      >
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-content-muted">
          <rect x="3" y="7" width="34" height="26" rx="3"/>
          <path d="M3 7l17 13L37 7"/>
        </svg>
        <p className="text-sm text-content-secondary">
          Drop <span className="font-mono text-accent-glow">.eml</span> file here or{' '}
          <span className="underline text-accent-glow">click to browse</span>
        </p>
        <p className="text-xs text-content-muted">Max 5 MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".eml"
        className="hidden"
        onChange={e => handleFile(e.target.files?.[0] ?? null)}
      />

      {/* Selected file */}
      {file && (
        <div className="card flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-glow shrink-0">
              <rect x="3" y="1" width="10" height="14" rx="1.5"/>
              <path d="M6 5h4M6 8h4M6 11h2"/>
            </svg>
            <div>
              <p className="text-sm font-medium text-content-primary">{file.name}</p>
              <p className="text-xs text-content-muted">{fmt_bytes(file.size)}</p>
            </div>
          </div>
          <button onClick={reset} className="btn-ghost text-xs px-3 py-1.5" aria-label="Remove file">
            ✕ Remove
          </button>
        </div>
      )}

      {/* Analyze button */}
      <button
        onClick={() => file && mutation.mutate(file)}
        disabled={!file || scanning}
        className="btn-primary w-full py-2.5 disabled:opacity-50"
      >
        {scanning ? (
          <span className="flex items-center justify-center gap-2">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Analyzing…
          </span>
        ) : 'Analyze Email'}
      </button>

      {/* Error */}
      {(error || mutation.isError) && (
        <div className="card border-sev-critical/30 bg-sev-critical-bg p-4">
          <p className="text-sm text-sev-critical">{error ?? 'An error occurred. Please try again.'}</p>
          <button onClick={reset} className="mt-2 text-xs text-sev-critical underline">Try again</button>
        </div>
      )}

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{opacity: 0, y: 8}}
            animate={{opacity: 1, y: 0}}
            transition={{duration: 0.3}}
            className="space-y-4"
          >
            {/* Verdict banner */}
            <div className="card p-5 flex items-center justify-between gap-4">
              <div>
                <p className={`text-2xl font-bold font-mono tracking-wider ${predColor[result.prediction] ?? 'text-content-primary'}`}>
                  {result.prediction}
                </p>
                <p className="text-sm text-content-muted mt-1">Risk score: {result.risk_score}/100</p>
              </div>
              <RiskBadge level={result.risk_level} size="lg" />
            </div>

            {/* Sender card */}
            <div className="card p-5 space-y-3">
              <p className="section-label">Sender</p>
              <div className="space-y-1.5 text-sm">
                <p className="text-content-secondary">
                  <span className="text-content-muted">From: </span>
                  &ldquo;{result.sender.from_display}&rdquo; &lt;{result.sender.from_email}&gt;
                  {result.sender.display_name_mismatch && (
                    <span className="ml-2 rounded border border-sev-medium/40 bg-sev-medium-bg px-1.5 py-0.5 text-xs text-sev-medium font-medium">
                      ⚠ Display name mismatch
                    </span>
                  )}
                </p>
                <p className="text-content-muted">
                  <span>Domain: </span>
                  <span className="font-mono text-content-secondary">{result.sender.from_domain}</span>
                </p>
                {result.sender.reply_to && (
                  <p className="text-content-secondary">
                    <span className="text-content-muted">Reply-To: </span>
                    {result.sender.reply_to}
                    {result.sender.reply_to_mismatch && (
                      <span className="ml-2 rounded border border-sev-critical/40 bg-sev-critical-bg px-1.5 py-0.5 text-xs text-sev-critical font-medium">
                        ⚠ Mismatched domain
                      </span>
                    )}
                  </p>
                )}
              </div>
            </div>

            {/* Auth header */}
            <div className="card p-4">
              <p className="section-label mb-3">Email Authentication</p>
              <div className="flex flex-wrap gap-2">
                <AuthChip label="SPF"   value={result.auth_results.spf}  />
                <AuthChip label="DKIM"  value={result.auth_results.dkim} />
                <AuthChip label="DMARC" value={result.auth_results.dmarc} />
              </div>
            </div>

            {/* Subject + Date */}
            <div className="card p-4">
              <p className="section-label mb-2">Message Info</p>
              <p className="text-sm text-content-secondary">
                <span className="text-content-muted">Subject: </span>{result.subject_snippet}
              </p>
              {result.date && (
                <p className="text-xs text-content-muted mt-1">{result.date}</p>
              )}
            </div>

            {/* Links table */}
            {result.links.length > 0 && (
              <div className="card p-4">
                <p className="section-label mb-3">Scanned Links ({result.links.length})</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-surface-border text-content-muted">
                        <th className="pb-2 text-left font-medium">URL</th>
                        <th className="pb-2 text-left font-medium">Result</th>
                        <th className="pb-2 text-left font-medium">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border">
                      {result.links.map((link, i) => (
                        <tr key={i}>
                          <td className="py-2 font-mono text-content-secondary max-w-xs truncate" title={link.url}>
                            {link.url.length > 50 ? link.url.slice(0, 50) + '…' : link.url}
                          </td>
                          <td className="py-2">
                            <RiskBadge prediction={link.prediction as never} size="sm" />
                          </td>
                          <td className="py-2 text-content-muted">
                            {Math.round(link.confidence * 100)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Attachments table */}
            {result.attachments.length > 0 && (
              <div className="card p-4">
                <p className="section-label mb-3">Attachments ({result.attachments.length})</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-surface-border text-content-muted">
                        <th className="pb-2 text-left font-medium">Filename</th>
                        <th className="pb-2 text-left font-medium">Extension</th>
                        <th className="pb-2 text-left font-medium">Risk</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border">
                      {result.attachments.map((att, i) => (
                        <tr key={i}>
                          <td className="py-2 font-mono text-content-secondary">{att.filename}</td>
                          <td className="py-2">
                            <span className="chip rounded border border-surface-muted bg-surface-overlay px-1.5 py-0.5 font-mono text-content-muted">
                              {att.extension || '—'}
                            </span>
                          </td>
                          <td className="py-2">
                            <RiskBadge level={att.risk as never} size="sm" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Evidence */}
            {result.evidence.length > 0 && (
              <div className="card p-4">
                <p className="section-label mb-3 text-sev-warning">Evidence &amp; Indicators</p>
                <ul className="space-y-2">
                  {result.evidence.map((ev, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-sev-warning">
                      <span className="mt-0.5 shrink-0">⚠</span>
                      <span>{ev}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
