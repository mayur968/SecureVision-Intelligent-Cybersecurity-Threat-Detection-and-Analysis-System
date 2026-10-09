import type { RiskLevel, Prediction } from '../../types/index.js';

interface Props {
  level?: RiskLevel;
  prediction?: Prediction;
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
}

// Risk level styles — severity-coded, professional
const riskStyles: Record<RiskLevel, { cls: string; dot: string; label: string }> = {
  LOW:    { cls: 'bg-sev-low-bg    text-sev-low      border-sev-low/30',      dot: 'bg-sev-low',      label: 'LOW'    },
  MEDIUM: { cls: 'bg-sev-medium-bg text-sev-medium   border-sev-medium/30',   dot: 'bg-sev-medium',   label: 'MEDIUM' },
  HIGH:   { cls: 'bg-sev-critical-bg text-sev-critical border-sev-critical/30', dot: 'bg-sev-critical', label: 'HIGH'   },
};

const predStyles: Record<string, { cls: string; dot: string; label: string }> = {
  SAFE:      { cls: 'bg-sev-low-bg      text-sev-low       border-sev-low/30',       dot: 'bg-sev-low',       label: 'SAFE'      },
  PHISHING:  { cls: 'bg-sev-critical-bg text-sev-critical  border-sev-critical/30',  dot: 'bg-sev-critical',  label: 'PHISHING'  },
  MALICIOUS: { cls: 'bg-sev-high-bg     text-sev-high      border-sev-high/30',      dot: 'bg-sev-high',      label: 'MALICIOUS' },
  UNKNOWN:   { cls: 'bg-surface-overlay text-content-muted  border-surface-muted',   dot: 'bg-content-muted', label: 'UNKNOWN'   },
  ERROR:     { cls: 'bg-surface-overlay text-content-muted  border-surface-muted',   dot: 'bg-content-muted', label: 'ERROR'     },
};

const sizes = {
  sm: 'px-2 py-0.5 text-2xs gap-1.5',
  md: 'px-2.5 py-1 text-xs gap-1.5',
  lg: 'px-3 py-1.5 text-sm gap-2',
};

export default function RiskBadge({ level, prediction, size = 'md', dot = true }: Props) {
  const style = (level ? riskStyles[level] : predStyles[prediction ?? 'UNKNOWN']) ?? predStyles['UNKNOWN'];
  return (
    <span className={`inline-flex items-center rounded border font-mono font-semibold tracking-wider ${style.cls} ${sizes[size]}`}>
      {dot && <span className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${style.dot}`} />}
      {style.label}
    </span>
  );
}
