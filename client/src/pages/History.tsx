import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '../api/client.js';
import type { HistoryScan, ScanTypeExtended, RiskLevel, Prediction } from '../types/index.js';
import RiskBadge from '../components/ui/RiskBadge.js';

type SortKey = 'created_at' | 'risk_level' | 'scan_type' | 'confidence';
type SortDir  = 'asc' | 'desc';
const riskOrder: Record<RiskLevel, number> = { LOW: 0, MEDIUM: 1, HIGH: 2 };

function exportCsv(scans: HistoryScan[]) {
  const header = 'id,scan_type,input_value,prediction,confidence,risk_level,created_at\n';
  const rows   = scans.map(s =>
    [s.id, s.scan_type, `"${s.input_value.replace(/"/g, '""')}"`,
     s.prediction, s.confidence, s.risk_level, s.created_at].join(',')
  ).join('\n');
  const a = Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(new Blob([header + rows], { type: 'text/csv' })),
    download: `securevision_${Date.now()}.csv`,
  });
  a.click();
}

export default function History() {
  const [limit,      setLimit]      = useState(50);
  const [typeFilter, setTypeFilter] = useState<ScanTypeExtended | 'ALL'>('ALL');
  const [riskFilter, setRiskFilter] = useState<RiskLevel | 'ALL'>('ALL');
  const [predFilter, setPredFilter] = useState<Prediction | 'ALL'>('ALL');
  const [search,     setSearch]     = useState('');
  const [sortKey,    setSortKey]    = useState<SortKey>('created_at');
  const [sortDir,    setSortDir]    = useState<SortDir>('desc');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['history', limit],
    queryFn:  () => api.getHistory(limit),
    refetchInterval: 30_000,
  });

  const scans = data?.scans ?? [];

  const filtered = scans.filter(s => {
    if (typeFilter !== 'ALL' && s.scan_type !== typeFilter) return false;
    if (riskFilter !== 'ALL' && s.risk_level !== riskFilter) return false;
    if (predFilter !== 'ALL' && s.prediction !== predFilter) return false;
    if (search && !s.input_value.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if      (sortKey === 'created_at') cmp = a.created_at.localeCompare(b.created_at);
    else if (sortKey === 'risk_level') cmp = (riskOrder[a.risk_level ?? 'LOW'] ?? 0) - (riskOrder[b.risk_level ?? 'LOW'] ?? 0);
    else if (sortKey === 'scan_type')  cmp = (a.scan_type ?? '').localeCompare(b.scan_type ?? '');
    else if (sortKey === 'confidence') cmp = (a.confidence ?? 0) - (b.confidence ?? 0);
    return sortDir === 'asc' ? cmp : -cmp;
  });

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  }

  function SortTh({ k, label }: { k: SortKey; label: string }) {
    const active = sortKey === k;
    return (
      <th className="cursor-pointer select-none px-4 py-3 text-left" onClick={() => toggleSort(k)}>
        <span className={`section-label inline-flex items-center gap-1 ${active ? 'text-accent-glow' : 'hover:text-content-secondary'}`}>
          {label}
          <span className="text-2xs">{active ? (sortDir === 'asc' ? '↑' : '↓') : ''}</span>
        </span>
      </th>
    );
  }

  const SelectFilter = ({ label, opts, value, onChange }: {
    label: string; opts: string[]; value: string; onChange: (v: string) => void;
  }) => (
    <select value={value} onChange={e => onChange(e.target.value)}
      className="rounded border border-surface-muted bg-surface-raised px-2.5 py-1.5 text-xs text-content-secondary outline-none focus:border-accent transition-colors">
      {opts.map(o => <option key={o}>{o}</option>)}
    </select>
  );

  return (
    <div className="space-y-5 max-w-screen-xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-content-primary">Scan History</h1>
          <p className="mt-0.5 text-sm text-content-muted">
            {filtered.length} of {scans.length} records
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => refetch()} className="btn-ghost text-xs px-3 py-1.5">
            <span className="flex items-center gap-1.5">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M10 6A4 4 0 1 1 6 2M10 2v4H6"/></svg>
              Refresh
            </span>
          </button>
          <button onClick={() => exportCsv(sorted)} disabled={!sorted.length} className="btn-primary text-xs px-3 py-1.5">
            <span className="flex items-center gap-1.5">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M6 1v7M3 5l3 3 3-3"/><path d="M2 9v1.5a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 .5-.5V9"/></svg>
              Export CSV
            </span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <svg className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-content-muted" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><circle cx="5" cy="5" r="3.5"/><path d="m7.5 7.5 2.5 2.5"/></svg>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search…"
            className="rounded border border-surface-muted bg-surface-raised py-1.5 pl-7 pr-3 text-xs text-content-secondary outline-none placeholder:text-content-disabled focus:border-accent w-40 transition-colors" />
        </div>

        <SelectFilter label="Type"   opts={['ALL','URL','MESSAGE','APK','URL_LIVE']} value={typeFilter} onChange={v => setTypeFilter(v as any)} />
        <SelectFilter label="Risk"   opts={['ALL','LOW','MEDIUM','HIGH']}            value={riskFilter} onChange={v => setRiskFilter(v as any)} />
        <SelectFilter label="Result" opts={['ALL','SAFE','PHISHING','MALICIOUS']}    value={predFilter} onChange={v => setPredFilter(v as any)} />

        <select value={limit} onChange={e => setLimit(Number(e.target.value))}
          className="rounded border border-surface-muted bg-surface-raised px-2.5 py-1.5 text-xs text-content-secondary outline-none focus:border-accent transition-colors">
          {[25, 50, 100].map(n => <option key={n} value={n}>Show {n}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div data-testid="loading-state" className="flex h-48 items-center justify-center">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          </div>
        ) : isError ? (
          <div data-testid="error-state" className="flex h-48 flex-col items-center justify-center gap-3 text-center p-5">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round"><circle cx="16" cy="16" r="13"/><path d="M16 10v6M16 21v1"/></svg>
            <p className="text-sm font-semibold text-sev-critical">Failed to load history</p>
            <p className="text-xs text-content-muted">Check that the Flask backend is running on port 5000.</p>
            <button onClick={() => refetch()} className="btn-ghost text-xs px-3 py-1.5 mt-1">Retry</button>
          </div>
        ) : sorted.length === 0 ? (
          <div data-testid="empty-state" className="flex h-48 flex-col items-center justify-center gap-2 text-center">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="#334155" strokeWidth="1.5" strokeLinecap="round"><rect x="4" y="4" width="24" height="24" rx="3"/><path d="M10 10h12M10 16h12M10 22h6"/></svg>
            <p className="text-sm text-content-muted">
              {scans.length ? 'No results match your filters' : 'No scans yet — run a scan to see history'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="border-b border-surface-border">
              <tr>
                <SortTh k="scan_type"  label="Type"       />
                <th className="px-4 py-3 text-left"><span className="section-label">Input</span></th>
                <th className="px-4 py-3 text-left"><span className="section-label">Result</span></th>
                <SortTh k="risk_level" label="Risk"       />
                <SortTh k="confidence" label="Confidence" />
                <th className="px-4 py-3 text-left"><span className="section-label">Model</span></th>
                <SortTh k="created_at" label="Time"       />
              </tr>
            </thead>
            <tbody>
              {sorted.map((s, i) => (
                <motion.tr key={s.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: Math.min(i * 0.015, 0.3) }}
                  className="border-b border-surface-border/40 hover:bg-surface-overlay transition-colors">
                  {/* Type */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="chip">{s.scan_type === 'URL_LIVE' ? 'URL' : s.scan_type}</span>
                      {s.scan_type === 'URL_LIVE' && (
                        <span className="chip bg-sev-info-bg text-sev-info">Live</span>
                      )}
                    </div>
                  </td>
                  {/* Input */}
                  <td className="px-4 py-3 max-w-[200px]">
                    <span className="block truncate font-mono text-xs text-content-secondary" title={s.input_value}>
                      {s.input_value}
                    </span>
                  </td>
                  {/* Result */}
                  <td className="px-4 py-3">
                    <RiskBadge prediction={s.prediction} size="sm" />
                  </td>
                  {/* Risk */}
                  <td className="px-4 py-3">
                    <RiskBadge level={s.risk_level} size="sm" />
                  </td>
                  {/* Confidence */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-16 rounded-full bg-surface-overlay overflow-hidden">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(s.confidence * 100)}%` }} />
                      </div>
                      <span className="font-mono text-xs text-content-muted">{Math.round(s.confidence * 100)}%</span>
                    </div>
                  </td>
                  {/* Model Version */}
                  <td className="px-4 py-3">
                    {s.model_version === 'legacy' || s.model_version == null ? (
                      <span className="chip bg-surface-overlay text-content-disabled">legacy</span>
                    ) : (
                      <code className="chip font-mono text-2xs text-content-secondary">{s.model_version}</code>
                    )}
                  </td>
                  {/* Time */}
                  <td className="px-4 py-3 text-xs text-content-muted whitespace-nowrap">
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
