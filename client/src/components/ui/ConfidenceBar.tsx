import { motion } from 'framer-motion';

interface Props {
  value: number;   // 0–1
  label?: string;
  showPercent?: boolean;
  size?: 'sm' | 'md';
}

function barColor(pct: number): string {
  if (pct >= 80) return 'bg-sev-critical';
  if (pct >= 60) return 'bg-sev-medium';
  if (pct >= 40) return 'bg-accent-glow';
  return 'bg-sev-low';
}

export default function ConfidenceBar({ value, label, showPercent = true, size = 'md' }: Props) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 100)));
  const h   = size === 'sm' ? 'h-1' : 'h-1.5';

  return (
    <div className="w-full">
      {(label || showPercent) && (
        <div className="mb-1.5 flex items-center justify-between">
          {label && <p className="text-2xs text-content-muted">{label}</p>}
          {showPercent && (
            <p className="font-mono text-2xs text-content-secondary">{pct}%</p>
          )}
        </div>
      )}
      <div className={`w-full rounded-full bg-surface-overlay overflow-hidden ${h}`}>
        <motion.div
          className={`${h} rounded-full ${barColor(pct)}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.55, ease: [0.4, 0, 0.2, 1] }}
        />
      </div>
    </div>
  );
}
