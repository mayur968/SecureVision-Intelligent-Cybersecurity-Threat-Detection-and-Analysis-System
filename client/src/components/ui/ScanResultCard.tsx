import { motion } from 'framer-motion';
import type { ScanResult } from '../../types/index.js';
import RiskBadge from './RiskBadge.js';
import ConfidenceBar from './ConfidenceBar.js';
import ExplanationPanel from './ExplanationPanel.js';
import RecommendationList from './RecommendationList.js';

interface Props { result: ScanResult; title?: string }

function riskScoreColor(score: number): string {
  if (score >= 70) return 'text-sev-critical';
  if (score >= 45) return 'text-sev-medium';
  return 'text-sev-low';
}

export default function ScanResultCard({ result, title = 'Scan Result' }: Props) {
  if (!result.success) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="card border-sev-critical/30 bg-sev-critical-bg p-5"
      >
        <p className="font-semibold text-sev-critical">Scan failed</p>
        <p className="mt-1 text-sm text-content-secondary">{result.error ?? 'Unknown error'}</p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="space-y-3"
    >
      {/* ── Header card ─────────────────────────────────────────────── */}
      <div className="card p-5">
        {/* Title + badges */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-surface-border">
          <p className="text-sm font-semibold text-content-primary">{title}</p>
          <div className="flex items-center gap-2">
            <RiskBadge prediction={result.prediction} size="md" />
            <RiskBadge level={result.risk_level} size="sm" />
          </div>
        </div>

        {/* Metrics row */}
        <div className="mt-4 grid grid-cols-2 gap-6">
          <div>
            <p className="section-label mb-1.5">Risk Score</p>
            <p className={`font-mono text-3xl font-bold leading-none ${riskScoreColor(result.risk_score)}`}>
              {result.risk_score}
              <span className="ml-1 text-sm font-normal text-content-muted">/100</span>
            </p>
          </div>
          <div className="flex flex-col justify-center">
            <ConfidenceBar value={result.confidence} label="Model confidence" />
          </div>
        </div>
      </div>

      {/* ── Indicators ──────────────────────────────────────────────── */}
      {result.indicators && result.indicators.length > 0 && (
        <div className="card p-4">
          <p className="section-label mb-3 text-sev-medium">Threat Indicators</p>
          <ul className="space-y-1.5">
            {result.indicators.map((ind, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-content-secondary">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-sev-medium" />
                {ind}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Explanation ─────────────────────────────────────────────── */}
      {result.explanation && <ExplanationPanel explanation={result.explanation} />}

      {/* ── Recommendations ─────────────────────────────────────────── */}
      {result.recommendations?.length > 0 && (
        <RecommendationList recommendations={result.recommendations} />
      )}

      {/* ── Analysis note ───────────────────────────────────────────── */}
      {result.analysis_note && (
        <p className="px-1 text-xs italic text-content-disabled">{result.analysis_note}</p>
      )}
    </motion.div>
  );
}
