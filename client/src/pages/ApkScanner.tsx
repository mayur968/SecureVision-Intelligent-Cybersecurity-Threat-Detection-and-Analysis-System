import { useState, useRef, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api/client.js';
import type { ScanResult } from '../types/index.js';
import ScanResultCard from '../components/ui/ScanResultCard.js';

const MAX_MB    = 50;
const MAX_BYTES = MAX_MB * 1024 * 1024;

const INFO_ITEMS = [
  'Extracts manifest, permissions and component metadata via Androguard',
  'Detects dangerous permission combinations (SMS, call interception, admin)',
  'Scans DEX bytecode for suspicious API patterns (reflection, dynamic loading)',
  'Validates signing certificate and checks for obfuscation indicators',
];

export default function ApkScanner() {
  const [file, setFile]       = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState(0);
  const [fileError, setFileError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({ mutationFn: (f: File) => api.scanApk(f, pct => setProgress(pct)) });

  function validateFile(f: File): string {
    if (!f.name.toLowerCase().endsWith('.apk')) return 'Only .apk files are accepted';
    if (f.size > MAX_BYTES) return `File too large — max ${MAX_MB} MB`;
    if (f.size === 0) return 'File is empty';
    return '';
  }

  function pickFile(f: File) {
    const err = validateFile(f);
    if (err) { setFileError(err); return; }
    setFileError('');
    setFile(f);
    setProgress(0);
    mutation.reset();
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) pickFile(dropped);
  }, []);

  const result = mutation.data as ScanResult | undefined;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-content-primary">APK Scanner</h1>
        <p className="mt-1 text-sm text-content-muted">
          Static analysis of Android APK files — permissions, API calls, certificates and obfuscation.{' '}
          <span className="font-medium text-sev-medium">The file is never executed.</span>
        </p>
      </div>

      {/* Upload card */}
      <div className="card p-5">
        <form onSubmit={e => { e.preventDefault(); if (file) mutation.mutate(file); }} className="space-y-4">
          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded border-2 border-dashed py-10 transition-all duration-150 ${
              dragOver
                ? 'border-accent bg-accent-subtle'
                : fileError
                ? 'border-sev-critical/50 bg-sev-critical-bg/30'
                : file
                ? 'border-sev-low/50 bg-sev-low-bg/30'
                : 'border-surface-muted hover:border-accent/50 hover:bg-surface-overlay'
            }`}
          >
            {file ? (
              <>
                {/* APK icon */}
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent-subtle">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="1.5" strokeLinecap="round">
                    <rect x="4" y="2" width="16" height="20" rx="2"/>
                    <path d="M9 7h6M9 12h6M9 17h4"/>
                  </svg>
                </div>
                <p className="mt-3 font-mono text-sm font-medium text-content-primary">{file.name}</p>
                <p className="mt-0.5 text-xs text-content-muted">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <button
                  type="button"
                  onClick={e => { e.stopPropagation(); setFile(null); mutation.reset(); }}
                  className="mt-2 text-xs text-content-muted hover:text-sev-critical transition-colors"
                >
                  Remove
                </button>
              </>
            ) : (
              <>
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-surface-overlay">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5" strokeLinecap="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
                <p className="mt-3 text-sm text-content-secondary">Drag & drop an APK file, or <span className="text-accent-glow underline underline-offset-2">browse</span></p>
                <p className="mt-1 text-xs text-content-muted">Max {MAX_MB} MB · .apk only</p>
              </>
            )}
          </div>

          <input ref={inputRef} type="file" accept=".apk" className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) pickFile(f); }} />

          {fileError && <p className="text-xs text-sev-critical">{fileError}</p>}

          {/* Upload progress */}
          {mutation.isPending && (
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <span className="text-xs text-content-muted">
                  {progress < 100 ? 'Uploading…' : 'Running static analysis…'}
                </span>
                <span className="font-mono text-xs text-content-muted">{progress}%</span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-surface-overlay">
                <motion.div className="h-full rounded-full bg-accent"
                  animate={{ width: `${Math.min(progress, 100)}%` }}
                  transition={{ duration: 0.3 }} />
              </div>
            </div>
          )}

          <button type="submit" disabled={!file || mutation.isPending} className="btn-primary w-full py-2.5">
            {mutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Analysing…
              </span>
            ) : 'Analyse APK'}
          </button>
        </form>
      </div>

      {/* Result */}
      <AnimatePresence>
        {result && !mutation.isPending && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            {result.success && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded border border-surface-border bg-surface-overlay px-4 py-2.5">
                <span className="font-mono text-sm text-content-primary">{result.filename}</span>
                <span className="text-content-disabled">·</span>
                <span className="text-xs text-content-muted">{result.file_size?.toFixed(2)} MB</span>
                {result.analysis_note && (
                  <>
                    <span className="text-content-disabled">·</span>
                    <span className="text-xs italic text-sev-medium">{result.analysis_note}</span>
                  </>
                )}
              </div>
            )}
            <ScanResultCard result={result} title="APK Analysis" />
          </motion.div>
        )}
      </AnimatePresence>

      {mutation.isError && (
        <div className="card border-sev-critical/30 bg-sev-critical-bg p-4 text-sm text-sev-critical">
          Scan failed — make sure the ML service is running.
        </div>
      )}

      {/* Info box */}
      <div className="rounded border border-surface-border bg-surface-raised p-4">
        <p className="section-label mb-3">How APK Analysis Works</p>
        <ul className="space-y-1.5">
          {INFO_ITEMS.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-content-muted">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-content-disabled" />
              {item}
            </li>
          ))}
          <li className="flex items-start gap-2 text-xs">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-sev-medium" />
            <span><span className="font-medium text-sev-medium">The APK is never executed</span> — purely static analysis</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
