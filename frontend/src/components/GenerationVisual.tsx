import { motion, useReducedMotion } from "framer-motion";

const points = [
  [12, 68], [25, 42], [37, 58], [48, 26], [61, 46], [73, 18], [87, 34],
];

export function GenerationVisual({ active = false }: { active?: boolean }) {
  const reduce = useReducedMotion();
  return <div className={`data-field ${active ? "data-field-active" : ""}`} aria-label={active ? "Dataset generation visual" : "Synthetic data field visual"} role="img">
    <div className="data-field-grid" />
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="data-field-lines" aria-hidden="true">
      {points.slice(0, -1).map((point, index) => <line key={`${point[0]}-${point[1]}`} x1={point[0]} y1={point[1]} x2={points[index + 1][0]} y2={points[index + 1][1]} />)}
    </svg>
    {points.map(([left, top], index) => <motion.span key={`${left}-${top}`} className="data-point" style={{ left: `${left}%`, top: `${top}%` }} animate={reduce ? undefined : { opacity: active ? [0.35, 1, 0.35] : [0.45, 0.75, 0.45], scale: active ? [1, 1.22, 1] : [1, 1.05, 1] }} transition={{ duration: 2.6 + index * 0.15, repeat: Infinity, delay: index * 0.16, ease: "easeInOut" }} />)}
    <div className="data-field-caption"><span className="signal-dot" />{active ? "ENGINE RUNNING" : "LOCAL SIGNAL FIELD"}</div>
  </div>;
}
