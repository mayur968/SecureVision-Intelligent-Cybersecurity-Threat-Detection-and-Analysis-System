import { motion } from 'framer-motion';

interface Props { recommendations: string[] }

export default function RecommendationList({ recommendations }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: 0.08 }}
      className="card p-4"
    >
      <p className="section-label mb-3">Recommendations</p>
      <ol className="space-y-2.5">
        {recommendations.map((rec, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-accent-subtle font-mono text-2xs font-bold text-accent-glow">
              {i + 1}
            </span>
            <span className="text-sm text-content-secondary leading-relaxed">{rec}</span>
          </li>
        ))}
      </ol>
    </motion.div>
  );
}
