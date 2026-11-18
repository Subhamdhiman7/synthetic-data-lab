import { useRef, type ReactNode } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";

export const motionEase = [0.22, 1, 0.36, 1] as const;

export function PageTransition({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion();
  return <motion.div initial={reduce ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduce ? 0 : 0.32, ease: motionEase }}>{children}</motion.div>;
}

export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.12 });
  const reduce = useReducedMotion();
  return <motion.div ref={ref} className={className} initial={reduce ? false : { opacity: 0, y: 18 }} animate={inView ? { opacity: 1, y: 0 } : undefined} transition={{ duration: reduce ? 0 : 0.52, delay: reduce ? 0 : delay, ease: motionEase }}>{children}</motion.div>;
}

export const hoverLift = { y: -3, transition: { duration: 0.18, ease: motionEase } };

export function AnimatedNumber({ value, className = "" }: { value: string | number; className?: string }) {
  const reduce = useReducedMotion();
  return <motion.span key={String(value)} className={className} initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduce ? 0 : 0.35, ease: motionEase }}>{value}</motion.span>;
}
