import type { ReactNode } from "react";
import { ArrowUpRight, LoaderCircle, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { hoverLift } from "./motion";

export function Button({ children, variant = "primary", type = "button", disabled = false, onClick, className = "" }: { children: ReactNode; variant?: "primary" | "secondary" | "ghost" | "danger"; type?: "button" | "submit" | "reset"; disabled?: boolean; onClick?: () => void; className?: string }) {
  const variants = {
    primary: "bg-cyan text-ink shadow-[0_0_28px_rgba(217,255,92,.14)] hover:bg-cyan/90",
    secondary: "border border-line bg-panelSoft text-slate-100 hover:border-cyan/60 hover:text-cyan",
    ghost: "text-slate-400 hover:bg-panelSoft hover:text-slate-100",
    danger: "border border-danger/30 bg-danger/10 text-danger hover:bg-danger/15",
  };
  return <motion.button type={type} disabled={disabled} onClick={onClick} whileHover={disabled ? undefined : hoverLift} whileTap={disabled ? undefined : { scale: .98 }} className={`inline-flex items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}>{children}</motion.button>;
}

export function IconButton({ label, children, onClick }: { label: string; children: ReactNode; onClick?: () => void }) {
  return <motion.button type="button" aria-label={label} title={label} onClick={onClick} whileHover={hoverLift} whileTap={{ scale: .94 }} className="rounded-full p-2.5 text-slate-400 transition hover:bg-panelSoft hover:text-slate-100">{children}</motion.button>;
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return <div className="mb-10 flex flex-col justify-between gap-6 lg:flex-row lg:items-end"><div><p className="eyebrow">{eyebrow || "Workspace"}</p><h1 className="mt-3 font-display text-4xl font-medium tracking-[-.055em] text-white sm:text-5xl">{title}</h1>{description && <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">{description}</p>}</div>{actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}</div>;
}

export function Panel({ children, className = "", glow = false }: { children: ReactNode; className?: string; glow?: boolean }) { return <section className={`panel ${glow ? "shadow-glow" : ""} ${className}`}>{children}</section>; }

export function StatCard({ label, value, detail, icon, tone = "cyan" }: { label: string; value: string; detail?: string; icon: ReactNode; tone?: "cyan" | "mint" | "amber" | "violet" }) {
  const tones = { cyan: "bg-cyan/10 text-cyan", mint: "bg-mint/10 text-mint", amber: "bg-amber/10 text-amber", violet: "bg-coral/10 text-coral" };
  return <motion.div whileHover={hoverLift} className="relative border-t border-line py-5"><div className="flex items-start justify-between gap-4"><div><p className="status-line">{label}</p><p className="mt-3 font-display text-3xl font-medium tracking-[-.05em] text-white">{value}</p>{detail && <p className="mt-2 max-w-[13rem] text-xs leading-5 text-slate-500">{detail}</p>}</div><span className={`rounded-full p-2.5 ${tones[tone]}`}>{icon}</span></div></motion.div>;
}

export function LoadingState({ label = "Loading data" }: { label?: string }) { return <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-[1.4rem] border border-dashed border-line bg-panel/40 text-sm text-slate-400"><LoaderCircle className="animate-spin text-cyan" size={22} /><span>{label}…</span></div>; }
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) { return <div className="rounded-[1.4rem] border border-danger/25 bg-danger/10 p-5 text-sm text-rose-100"><p className="font-semibold text-danger">Could not load this view</p><p className="mt-1 leading-6 text-rose-100/70">{message}</p>{onRetry && <Button variant="danger" className="mt-4" onClick={onRetry}><RefreshCw size={15} /> Retry</Button>}</div>; }
export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) { return <div className="flex min-h-56 flex-col items-center justify-center rounded-[1.4rem] border border-dashed border-line bg-panel/30 px-6 text-center"><div className="mb-4 rounded-full bg-panelSoft p-3 text-cyan"><ArrowUpRight size={20} /></div><h3 className="font-display text-lg font-semibold text-white">{title}</h3><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p>{action && <div className="mt-5">{action}</div>}</div>; }
export function StatusBadge({ value }: { value: string }) { return <span className="inline-flex items-center gap-1.5 rounded-full border border-mint/20 bg-mint/10 px-2.5 py-1 text-xs font-semibold text-mint"><span className="h-1.5 w-1.5 rounded-full bg-mint" />{value}</span>; }
export function TaskBadge({ task }: { task: string }) { const isClassification = task === "classification"; return <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${isClassification ? "bg-cyan/10 text-cyan" : "bg-amber/10 text-amber"}`}>{isClassification ? "Classification" : "Regression"}</span>; }
