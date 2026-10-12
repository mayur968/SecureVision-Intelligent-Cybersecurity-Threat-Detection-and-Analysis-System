import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api/client.js';
import type { ScanResult } from '../types/index.js';
import ScanResultCard from '../components/ui/ScanResultCard.js';

const MAX_CHARS = 10_000;

const SAMPLES = [
  { label: 'Phishing SMS',   text: 'URGENT: Your bank account has been suspended due to suspicious activity. Click here immediately to verify your identity and avoid permanent closure: http://secure-bank-verify.tk/login' },
  { label: 'Phishing Email', text: 'Dear Customer, FINAL NOTICE: Your PayPal account will be permanently limited unless you confirm your information within 24 hours. Act NOW: http://paypa1-secure.com/verify' },
  { label: 'Legitimate',     text: 'Hi team, the sprint review is scheduled for Friday at 2 PM. Please have your demos ready and send any blockers to the project channel beforehand. Thanks!' },
];

const SUSPICIOUS_PATTERNS = /urgent|suspended|verify|click here|immediately|limited|winner|prize/gi;

function AnnotatedText({ text, indicators }: { text: string; indicators: string[] }) {
  if (!indicators.length) return <p className="whitespace-pre-wrap text-sm leading-relaxed text-content-secondary">{text}</p>;
  const parts = text.split(/(https?:\/\/\S+|urgent|suspended|verify|click here|immediately|limited|winner|prize)/gi);
  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed text-content-secondary">
      {parts.map((part, i) => {
        if (/^https?:\/\//i.test(part))
          return <mark key={i} className="rounded bg-sev-medium-bg px-0.5 font-mono text-sev-medium not-italic">{part}</mark>;
        if (SUSPICIOUS_PATTERNS.test(part))
          return <mark key={i} className="rounded bg-sev-critical-bg px-0.5 text-sev-critical not-italic">{part}</mark>;
        return <span key={i}>{part}</span>;
      })}
    </p>
  );
}

export default function MessageScanner() {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const mutation = useMutation({ mutationFn: api.scanMessage });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (text.trim().length < 10) { setError('Message must be at least 10 characters'); return; }
    if (text.length > MAX_CHARS)  { setError(`Message too long (max ${MAX_CHARS.toLocaleString()} chars)`); return; }
    setError('');
    mutation.mutate(text.trim());
  }

  const pct = Math.min(100, Math.round((text.length / MAX_CHARS) * 100));

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-content-primary">Message Scanner</h1>
        <p className="mt-1 text-sm text-content-muted">
          Analyse email or SMS content for social-engineering patterns and phishing indicators.
        </p>
      </div>

      {/* Input card */}
      <div className="card p-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="msg" className="mb-1.5 block text-sm font-medium text-content-secondary">
              Message content
            </label>
            <textarea
              id="msg"
              rows={7}
              value={text}
              onChange={e => { setText(e.target.value); setError(''); }}
              placeholder="Paste an email or SMS message here…"
              className={`input resize-y ${error ? 'border-sev-critical focus:border-sev-critical' : ''}`}
            />
            {/* Character progress + error */}
            <div className="mt-1.5 flex items-center justify-between gap-4">
              <p className={`text-xs ${error ? 'text-sev-critical' : 'text-transparent'}`}>{error || '·'}</p>
              <div className="flex items-center gap-2">
                <div className="h-1 w-24 rounded-full bg-surface-overlay overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${pct > 90 ? 'bg-sev-medium' : 'bg-accent'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className={`font-mono text-xs ${text.length > MAX_CHARS * 0.9 ? 'text-sev-medium' : 'text-content-muted'}`}>
                  {text.length.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Samples */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="section-label">Load sample:</span>
            {SAMPLES.map(s => (
              <button key={s.label} type="button"
                onClick={() => { setText(s.text); setError(''); mutation.reset(); }}
                className="rounded border border-surface-muted px-2 py-0.5 text-xs text-content-secondary hover:border-accent hover:text-accent-glow transition-colors">
                {s.label}
              </button>
            ))}
          </div>

          <button type="submit" disabled={mutation.isPending} className="btn-primary w-full py-2.5">
            {mutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Analysing…
              </span>
            ) : 'Analyse Message'}
          </button>
        </form>
      </div>

      {/* Loading */}
      <AnimatePresence>
        {mutation.isPending && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="card flex items-center gap-3 p-5">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <span className="text-sm text-content-muted">Running NLP analysis…</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Result */}
      <AnimatePresence>
        {mutation.data && !mutation.isPending && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            {/* Annotated preview */}
            {mutation.data.success && (
              <div className="card p-5">
                <p className="section-label mb-3">Annotated Input</p>
                <AnnotatedText
                  text={text.slice(0, 600) + (text.length > 600 ? '…' : '')}
                  indicators={mutation.data.indicators ?? []}
                />
                {mutation.data.indicators && mutation.data.indicators.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {mutation.data.indicators.map((ind, i) => (
                      <span key={i} className="rounded border border-sev-medium/30 bg-sev-medium-bg px-2 py-0.5 text-xs text-sev-medium">
                        {ind}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            <ScanResultCard result={mutation.data as ScanResult} title="Message Analysis" />
          </motion.div>
        )}
      </AnimatePresence>

      {mutation.isError && (
        <div className="card border-sev-critical/30 bg-sev-critical-bg p-4 text-sm text-sev-critical">
          Scan failed — make sure the ML service is running.
        </div>
      )}
    </div>
  );
}
