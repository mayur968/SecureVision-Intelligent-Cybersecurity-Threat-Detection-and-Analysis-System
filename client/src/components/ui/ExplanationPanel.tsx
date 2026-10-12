import { motion } from 'framer-motion';

interface Props { explanation: string }

export default function ExplanationPanel({ explanation }: Props) {
  const lines = explanation.split('\n').map(l => l.replace(/^[•\-\*]\s*/, '').trim()).filter(Boolean);
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="card p-4"
    >
      <p className="section-label mb-3">Analysis</p>
      <ul className="space-y-2">
        {lines.map((line, i) => (
          <li key={i} className="flex items-start gap-2.5">
            <span className="mt-1 shrink-0 h-1 w-1 rounded-full bg-accent-glow" />
            <span className="text-sm text-content-secondary leading-relaxed">{line}</span>
          </li>
        ))}
      </ul>
    </motion.div>
  );
}
