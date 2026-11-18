import { lazy, Suspense } from "react";
import { AnimatePresence } from "framer-motion";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppLayout, ThemeProvider } from "./components/Layout";
import { PageTransition } from "./components/motion";
import { LoadingState } from "./components/ui";

const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage").then(({ AnalyticsPage }) => ({ default: AnalyticsPage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then(({ DashboardPage }) => ({ default: DashboardPage })));
const DatasetDetailPage = lazy(() => import("./pages/DatasetDetailPage").then(({ DatasetDetailPage }) => ({ default: DatasetDetailPage })));
const DatasetsPage = lazy(() => import("./pages/DatasetsPage").then(({ DatasetsPage }) => ({ default: DatasetsPage })));
const GeneratePage = lazy(() => import("./pages/GeneratePage").then(({ GeneratePage }) => ({ default: GeneratePage })));
const HistoryPage = lazy(() => import("./pages/HistoryPage").then(({ HistoryPage }) => ({ default: HistoryPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then(({ SettingsPage }) => ({ default: SettingsPage })));

export default function App() {
  return <ThemeProvider><BrowserRouter><Suspense fallback={<LoadingState label="Loading workspace" />}><Routes><Route element={<AppLayout />}><Route index element={<Navigate to="/dashboard" replace />} /><Route path="/dashboard" element={<AnimatedRoute><DashboardPage /></AnimatedRoute>} /><Route path="/generate" element={<AnimatedRoute><GeneratePage /></AnimatedRoute>} /><Route path="/datasets" element={<AnimatedRoute><DatasetsPage /></AnimatedRoute>} /><Route path="/datasets/:generationId" element={<AnimatedRoute><DatasetDetailPage /></AnimatedRoute>} /><Route path="/analytics" element={<AnimatedRoute><AnalyticsPage /></AnimatedRoute>} /><Route path="/history" element={<AnimatedRoute><HistoryPage /></AnimatedRoute>} /><Route path="/settings" element={<AnimatedRoute><SettingsPage /></AnimatedRoute>} /><Route path="*" element={<Navigate to="/dashboard" replace />} /></Route></Routes></Suspense></BrowserRouter></ThemeProvider>;
}

function AnimatedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return <AnimatePresence mode="wait" initial={false}><PageTransition key={location.pathname}>{children}</PageTransition></AnimatePresence>;
}
