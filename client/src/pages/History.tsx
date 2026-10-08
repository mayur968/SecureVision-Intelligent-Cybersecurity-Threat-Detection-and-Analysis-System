import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '../api/client.js';
import type { HistoryScan, ScanTypeExtended, RiskLevel, Prediction } from '../types/index.js';
import RiskBadge from '../components/ui/RiskBadge.js';

type SortKey = 'created_at' | 'risk_level' | 'scan_type' | 'confidence';
type SortDir = 'asc' | 'desc';

const riskOrder: Record<RiskLevel, number> = { LOW: 0, MEDIUM: 1, HIGH: 2 };

function exportCsv(scans: HistoryScan[]) {
  const header = 'id,scan_type,input_value,prediction,confidence,risk_level,created_at\n';
  const rows = scans.map(s =>
    [s.id, s.scan_type, `"${s.input_value.replace(/"/g, '""')}"`,
     s.prediction, s.confidence, s.risk_level, s.created_at].join(',')
  ).join('\n');
  const blob = new Blob([header + rows], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `securevision_history_${Date.now()}.csv`;
  a.click();
}

export default function History() {
  const [limit, setLimit] = useState(50);
  const [typeFilter, setTypeFilter] = useState<ScanTypeExtended | 'ALL'>('ALL');
  const [riskFilter, setRiskFilter] = useState<RiskLevel | 'ALL'>('ALL');
  const [predFilter, setPredFilter] = useState<Prediction | 'ALL'>('ALL');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['history', limit],
    queryFn: () => api.getHistory(limit),
    refetchInterval: 30_000,
  });

  const scans = data?.scans ?? [];

  // Filter
  const filtered = scans.filter(s => {
    if (typeFilter !== 'ALL' && s.scan_type !== typeFilter) return false;
    if (riskFilter !== 'ALL' && s.risk_level !== riskFilter) return false;
    if (predFilter !== 'ALL' && s.prediction !== predFilter) return false;
    if (search && !s.input_value.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0;
    if (sortKey === 'created_at') cmp = a.created_at.localeCompare(b.created_at);
    else if (sortKey === 'risk_level') cmp = riskOrder[a.risk_level] - riskOrder[b.risk_level];
    else if (sortKey === 'scan_type') cmp = a.scan_type.localeCompare(b.scan_type);
    else if (sortKey === 'confidence') cmp = a.confidence - b.confidence;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  }

  function SortTh({ k, label }: { k: SortKey; label: string }) {
    const active = sortKey === k;
    return (
      <th className="cursor-pointer select-none pb-2 pr-4 text-left" onClick={() => toggleSort(k)}>
        <span className={`text-xs uppercase tracking-wider ${active ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-300'}`}>
          {label} {active ? (sortDir === 'asc' ? '↑' : '↓') : ''}
        </span>
      </th>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Scan History</h1>
          <p className="mt-1 text-sm text-slate-400">{filtered.length} of {scans.length} scans shown</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => refetch()}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700">
            ↻ Refresh
          </button>
          <button onClick={() => exportCsv(sorted)} disabled={!sorted.length}
            className="rounded-lg bg-cyan-500 px-3 py-1.5 text-sm font-semibold text-slate-900 hover:bg-cyan-400 disabled:opacity-40">
            ↓ CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search input value…"
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-500 w-48" />

        {([['Type', ['ALL','URL','MESSAGE','APK','URL_LIVE'], typeFilter, setTypeFilter],
           ['Risk',  ['ALL','LOW','MEDIUM','HIGH'], riskFilter, setRiskFilter],
           ['Result',['ALL','SAFE','PHISHING','MALICIOUS'], predFilter, setPredFilter],
        ] as const).map(([lbl, opts, val, setter]: any) => (
          <select key={lbl} value={val} onChange={e => setter(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 outline-none focus:border-cyan-500">
            {opts.map((o: string) => <option key={o}>{o}</option>)}
          </select>
        ))}

        <select value={limit} onChange={e => setLimit(Number(e.target.value))}
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 outline-none focus:border-cyan-500">
          {[25, 50, 100].map(n => <option key={n} value={n}>Show {n}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <span className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          </div>
        ) : isError ? (
          <p className="p-6 text-sm text-red-400">Failed to load history</p>
        ) : sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-3xl">📋</p>
            <p className="mt-3 text-sm text-slate-400">{scans.length ? 'No results match your filters' : 'No scans yet — try the scanners!'}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-800">
                <tr>
                  <SortTh k="scan_type"  label="Type"       />
                  <th className="pb-2 pr-4 text-left text-xs uppercase tracking-wider text-slate-500">Input</th>
                  <th className="pb-2 pr-4 text-left text-xs uppercase tracking-wider text-slate-500">Result</th>
                  <SortTh k="risk_level" label="Risk"       />
                  <SortTh k="confidence" label="Confidence" />
                  <SortTh k="created_at" label="Time"       />
                </tr>
              </thead>
              <tbody>
                {sorted.map((s, idx) => (
                  <motion.tr key={s.id}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.02 }}
                    className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="py-3 pr-4">
                      <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-cyan-400">
                        {s.scan_type === 'URL_LIVE' ? 'URL' : s.scan_type}
                      </span>
                      {s.scan_type === 'URL_LIVE' && (
                        <span className="ml-1 rounded bg-teal-900/50 px-1.5 py-0.5 text-xs text-teal-400 font-semibold">
                          Live
                        </span>
                      )}
                    </td>
                    <td className="py-3 pr-4 max-w-[200px]">
                      <span className="block truncate font-mono text-xs text-slate-300" title={s.input_value}>
                        {s.input_value}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <RiskBadge prediction={s.prediction} size="sm" />
                    </td>
                    <td className="py-3 pr-4">
                      <RiskBadge level={s.risk_level} size="sm" />
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-slate-400">
                      {Math.round(s.confidence * 100)}%
                    </td>
                    <td className="py-3 text-xs text-slate-500 whitespace-nowrap">
                      {new Date(s.created_at).toLocaleString()}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
