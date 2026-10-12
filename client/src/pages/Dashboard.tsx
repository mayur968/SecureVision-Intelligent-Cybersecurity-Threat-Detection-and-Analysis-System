import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { api } from '../api/client.js';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';

// ── Design tokens for charts ─────────────────────────────────────────────────
const CHART_TOOLTIP = {
  contentStyle: {
    background: '#1a2236',
    border: '1px solid #1f2d45',
    borderRadius: '6px',
    fontSize: '12px',
    color: '#94a3b8',
  },
  itemStyle: { color: '#f1f5f9' },
  cursor: { stroke: '#1f2d45' },
};
const GRID = { stroke: '#1a2236', strokeDasharray: '0' };
const AXIS_TICK = { fill: '#475569', fontSize: 11 };

const PIE_COLORS = ['#22c55e', '#ef4444', '#f97316', '#f59e0b'];

// ── Stat card ─────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: number | string;
  sub?: string;
  accent?: 'default' | 'critical' | 'low' | 'medium';
  icon: React.ReactNode;
}

function StatCard({ label, value, sub, accent = 'default', icon }: StatCardProps) {
  const accentBar = {
    default:  'bg-accent',
    critical: 'bg-sev-critical',
    low:      'bg-sev-low',
    medium:   'bg-sev-medium',
  }[accent];

  return (
    <div className="card relative overflow-hidden p-5">
      {/* Left accent stripe */}
      <div className={`absolute left-0 top-0 h-full w-0.5 ${accentBar}`} />
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="section-label">{label}</p>
          <p className="mt-2 font-mono text-2xl font-bold text-content-primary leading-none">
            {value}
          </p>
          {sub && <p className="mt-1.5 text-xs text-content-muted">{sub}</p>}
        </div>
        <div className="shrink-0 rounded bg-surface-overlay p-2 text-content-muted">
          {icon}
        </div>
      </div>
    </div>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────
const Icons = {
  scan: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="9" cy="9" r="7"/>
      <path d="M9 5v4l3 2"/>
    </svg>
  ),
  threat: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="m9 2 7 4v5c0 3.5-3 6-7 7-4-1-7-3.5-7-7V6l7-4Z"/>
      <path d="M9 7v3M9 12h.01"/>
    </svg>
  ),
  safe: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="m9 2 7 4v5c0 3.5-3 6-7 7-4-1-7-3.5-7-7V6l7-4Z"/>
      <path d="m6 9 2 2 4-4"/>
    </svg>
  ),
  chart: (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M3 13 7 8l3 3 3-5 3 3"/>
      <path d="M1 16h16"/>
    </svg>
  ),
};

// ── Prediction color helper ───────────────────────────────────────────────────
function predColor(p: string) {
  if (p === 'SAFE')      return 'text-sev-low';
  if (p === 'PHISHING')  return 'text-sev-critical';
  if (p === 'MALICIOUS') return 'text-sev-high';
  return 'text-content-muted';
}

function scanTypeLabel(t: string) {
  if (t === 'URL_LIVE') return <><span className="chip">URL</span><span className="ml-1 chip bg-sev-info-bg text-sev-info">Live</span></>;
  return <span className="chip">{t}</span>;
}

// ── Custom tooltip ─────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={CHART_TOOLTIP.contentStyle} className="px-3 py-2 text-xs">
      <p className="mb-1 text-content-muted">Scan #{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['statistics'],
    queryFn:  api.getStatistics,
    refetchInterval: 30_000,
  });
  const { data: histData } = useQuery({
    queryKey: ['history', 20],
    queryFn:  () => api.getHistory(20),
    refetchInterval: 30_000,
  });

  const stats = data?.statistics;
  const scans = histData?.scans ?? [];

  if (isLoading) return <Skeleton />;
  if (isError || !stats) return <ErrorState />;

  const detRate = stats.total_scans
    ? Math.round((stats.threats_detected / stats.total_scans) * 100)
    : 0;

  const pieData = [
    { name: 'Safe',      value: stats.safe_results },
    { name: 'URL Threats',  value: stats.threat_breakdown.url },
    { name: 'Msg Threats',  value: stats.threat_breakdown.message },
    { name: 'APK Threats',  value: stats.threat_breakdown.apk },
  ].filter(d => d.value > 0);

  const areaData = scans.slice(0, 12).reverse().map((s, i) => ({
    x:    i + 1,
    safe: s.prediction === 'SAFE' ? 1 : 0,
    risk: s.prediction !== 'SAFE' ? 1 : 0,
  }));

  return (
    <div className="space-y-6 max-w-screen-xl">
      {/* ── Page header ───────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-content-primary">Security Dashboard</h1>
          <p className="mt-0.5 text-sm text-content-muted">Real-time threat detection overview</p>
        </div>
        <span className="flex items-center gap-1.5 rounded border border-surface-muted bg-surface-raised px-3 py-1.5 text-xs text-content-muted">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-sev-low animate-pulse-dot" />
          Live — auto-refreshes every 30s
        </span>
      </div>

      {/* ── KPI cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }}>
          <StatCard label="Total Scans"      value={stats.total_scans}       icon={Icons.scan}   accent="default"  />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <StatCard label="Threats Detected" value={stats.threats_detected}  icon={Icons.threat} accent="critical" sub={`${detRate}% detection rate`} />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <StatCard label="Safe Results"     value={stats.safe_results}       icon={Icons.safe}   accent="low"     />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <StatCard label="Scans by Type"    value={`${stats.url_scans} · ${stats.message_scans} · ${stats.apk_scans}`} icon={Icons.chart} sub="URL · MSG · APK" />
        </motion.div>
      </div>

      {/* ── Charts row ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4">
        {/* Activity area chart — full width */}
        <div className="card p-5">
          <p className="section-label mb-4">Recent Activity</p>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={areaData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gSafe" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gRisk" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="x" tick={AXIS_TICK} tickLine={false} axisLine={false} />
              <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="safe" name="Safe" stroke="#22c55e" fill="url(#gSafe)" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="risk" name="Threats" stroke="#ef4444" fill="url(#gRisk)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Second row: pie + table ────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {/* Pie chart */}
        <div className="card p-5">
          <p className="section-label mb-4">Result Distribution</p>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={72} paddingAngle={2}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} strokeWidth={0} />
                  ))}
                </Pie>
                <Legend
                  iconType="circle" iconSize={8}
                  formatter={(v) => <span style={{ color: '#94a3b8', fontSize: 11 }}>{v}</span>}
                />
                <Tooltip contentStyle={CHART_TOOLTIP.contentStyle} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-48 items-center justify-center">
              <p className="text-sm text-content-disabled">No scan data yet</p>
            </div>
          )}
        </div>

        {/* Recent scans table */}
        <div className="card overflow-hidden xl:col-span-2">
          <div className="flex items-center justify-between border-b border-surface-border px-5 py-3">
            <p className="section-label">Recent Scans</p>
            <span className="text-xs text-content-muted">Latest {Math.min(scans.length, 8)}</span>
          </div>
          <RecentTable scans={scans.slice(0, 8)} />
        </div>
      </div>
    </div>
  );
}

// ── Recent scans table ─────────────────────────────────────────────────────────
function RecentTable({ scans }: { scans: any[] }) {
  if (!scans.length) {
    return (
      <div className="flex h-40 items-center justify-center">
        <p className="text-sm text-content-disabled">No scans yet</p>
      </div>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-border">
            {['Type', 'Input', 'Result', 'Risk', 'Time'].map(h => (
              <th key={h} className="px-5 py-2.5 text-left">
                <span className="section-label">{h}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {scans.map((s: any, i: number) => (
            <motion.tr
              key={s.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              className="border-b border-surface-border/50 hover:bg-surface-overlay transition-colors"
            >
              <td className="px-5 py-3">
                {s.scan_type === 'URL_LIVE' ? (
                  <div className="flex items-center gap-1">
                    <span className="chip">URL</span>
                    <span className="chip bg-sev-info-bg text-sev-info">Live</span>
                  </div>
                ) : (
                  <span className="chip">{s.scan_type}</span>
                )}
              </td>
              <td className="px-5 py-3 max-w-[180px]">
                <span className="block truncate font-mono text-xs text-content-secondary" title={s.input_value}>
                  {s.input_value}
                </span>
              </td>
              <td className="px-5 py-3">
                <span className={`font-mono text-xs font-semibold ${predColor(s.prediction)}`}>
                  {s.prediction}
                </span>
              </td>
              <td className="px-5 py-3 text-xs text-content-secondary">{s.risk_level}</td>
              <td className="px-5 py-3 text-xs text-content-muted whitespace-nowrap">
                {new Date(s.created_at).toLocaleTimeString()}
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-6 w-52 rounded bg-surface-overlay" />
      <div className="grid grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => <div key={i} className="card h-24" />)}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="card h-52 xl:col-span-2" />
        <div className="card h-52" />
      </div>
    </div>
  );
}

// ── Error state ───────────────────────────────────────────────────────────────
function ErrorState() {
  return (
    <div className="flex h-72 flex-col items-center justify-center gap-3 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-sev-critical-bg">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round">
          <circle cx="10" cy="10" r="8.5"/>
          <path d="M10 6v4M10 13.5h.01"/>
        </svg>
      </div>
      <p className="font-semibold text-content-primary">Could not load statistics</p>
      <p className="text-sm text-content-muted">Make sure both the ML service and gateway are running.</p>
    </div>
  );
}
