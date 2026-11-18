import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { BarChart3, Database, FlaskConical, History, LayoutDashboard, Menu, Moon, Settings, Sparkles, Sun, X } from "lucide-react";
import { getHealth } from "../lib/api";
import { IconButton, StatusBadge } from "./ui";

const navigation = [
  { index: "01", label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { index: "02", label: "Generate", to: "/generate", icon: FlaskConical },
  { index: "03", label: "Datasets", to: "/datasets", icon: Database },
  { index: "04", label: "Analytics", to: "/analytics", icon: BarChart3 },
  { index: "05", label: "History", to: "/history", icon: History },
  { index: "06", label: "Settings", to: "/settings", icon: Settings },
];

type Theme = "dark" | "light";
type ThemeContextValue = { theme: Theme; toggleTheme: () => void };
const ThemeContext = createContext<ThemeContextValue | null>(null);
type BackendStatus = "checking" | "online" | "offline";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("sdl-theme") as Theme) || "dark");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("sdl-theme", theme);
  }, [theme]);
  return <ThemeContext.Provider value={{ theme, toggleTheme: () => setTheme((current) => current === "dark" ? "light" : "dark") }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used within ThemeProvider");
  return context;
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    let active = true;
    setBackendStatus("checking");
    getHealth()
      .then(() => {
        if (!active) return;
        setBackendStatus("online");
      })
      .catch(() => {
        if (!active) return;
        setBackendStatus("offline");
      });
    return () => { active = false; };
  }, [location.pathname]);

  const current = navigation.find((item) => location.pathname.startsWith(item.to));
  const backendLabel = backendStatus === "checking" ? "Checking backend…" : backendStatus === "online" ? "Local engine online" : "Backend offline";
  const backendDot = backendStatus === "checking" ? "bg-amber animate-pulse" : backendStatus === "online" ? "bg-mint shadow-[0_0_12px_rgba(155,232,189,.75)]" : "bg-danger";

  return <div className="min-h-screen bg-ink text-slate-100">
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-24 flex-col border-r border-line/60 bg-ink/90 px-3 py-5 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="relative flex flex-col items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-full bg-cyan text-ink shadow-[0_0_26px_rgba(217,255,92,.22)]"><Sparkles size={20} /></span>
        <span className="font-mono text-[9px] tracking-[.16em] text-cyan">SDL / 01</span>
        <button type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)} className="absolute -right-1 -top-1 rounded-full bg-panelSoft p-1.5 text-slate-400 hover:text-cyan lg:hidden"><X size={14} /></button>
      </div>
      <nav className="mt-12 flex flex-1 flex-col items-center gap-3" aria-label="Primary navigation">
        {navigation.map(({ index, label, to, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setMobileOpen(false)} aria-label={label} title={label} className={({ isActive }) => `group flex w-16 flex-col items-center gap-1.5 rounded-2xl px-2 py-3 text-[9px] uppercase tracking-[.1em] transition ${isActive ? "bg-cyan/10 text-cyan" : "text-slate-500 hover:bg-panelSoft hover:text-slate-100"}`}>
          <span className="font-mono text-[9px] opacity-60">{index}</span><Icon size={17} /><span>{label}</span>
        </NavLink>)}
      </nav>
      <div className="flex flex-col items-center gap-4"><div className="h-px w-8 bg-line" /><span className={`h-2 w-2 rounded-full ${backendDot}`} title={backendLabel} /></div>
    </aside>
    <div className="min-h-screen lg:pl-24">
      <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between border-b border-line/50 bg-ink/80 px-5 backdrop-blur-xl sm:px-8 lg:px-12">
        <div className="flex items-center gap-4"><IconButton label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={20} /></IconButton><div><p className="status-line">{current?.index || "00"} / {current?.label || "Workspace"}</p><p className="mt-1 hidden text-xs text-slate-500 sm:block">Build data. Explore possibilities.</p></div></div>
        <div className="flex items-center gap-2 sm:gap-4"><div className="hidden items-center gap-2 font-mono text-[10px] uppercase tracking-[.12em] text-slate-500 sm:flex"><span className={`h-1.5 w-1.5 rounded-full ${backendDot}`} />{backendLabel}</div><IconButton label="Toggle theme" onClick={toggleTheme}>{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</IconButton><div className="hidden sm:block"><StatusBadge value="Private workspace" /></div></div>
      </header>
      <main className="mx-auto max-w-[1680px] px-5 py-8 sm:px-8 lg:px-12"><Outlet /></main>
    </div>
  </div>;
}
