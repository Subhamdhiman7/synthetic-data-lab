import { useEffect, useState } from "react";
import { getApiError, getAnalysis, getHistory } from "../lib/api";
import type { AnalysisResponse, GenerationMetadata } from "../types/api";
import { AnalysisPanel } from "../components/AnalysisPanel";
import { ErrorState, LoadingState, PageHeader, EmptyState } from "../components/ui";
import { Reveal } from "../components/motion";

export function AnalyticsPage() {
  const [items, setItems] = useState<GenerationMetadata[]>([]); const [selectedId, setSelectedId] = useState(""); const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null); const [loading, setLoading] = useState(true); const [analysisLoading, setAnalysisLoading] = useState(false); const [error, setError] = useState("");
  useEffect(() => { getHistory(100, 0).then((response) => { setItems(response.items); setSelectedId(response.items[0]?.generation_id || ""); }).catch((reason) => setError(getApiError(reason))).finally(() => setLoading(false)); }, []);
  useEffect(() => { if (!selectedId) { setAnalysis(null); return; } setAnalysisLoading(true); setError(""); getAnalysis(selectedId).then(setAnalysis).catch((reason) => setError(getApiError(reason))).finally(() => setAnalysisLoading(false)); }, [selectedId]);
  if (loading) return <LoadingState label="Loading analytics" />; if (error && !analysis) return <ErrorState message={error} />; if (!items.length) return <div><PageHeader eyebrow="Explore" title="Analytics" description="Profile and inspect a generated dataset." /><EmptyState title="No data to analyze" description="Generate a dataset first. Analytics will use the real CSV returned by the backend." /></div>;
  return <div><Reveal><PageHeader eyebrow="Explore / 04" title="Analytics" description="A visual read of the selected CSV: distributions, quality signals, and relationships from actual backend analysis." actions={<select aria-label="Dataset for analytics" value={selectedId} onChange={(event) => setSelectedId(event.target.value)} className="field-input w-full sm:w-72">{items.map((item) => <option key={item.generation_id} value={item.generation_id}>{item.dataset_name} · {item.task}</option>)}</select>} /></Reveal>{analysisLoading ? <LoadingState label="Profiling dataset" /> : analysis ? <Reveal delay={.08}><AnalysisPanel analysis={analysis} /></Reveal> : <EmptyState title="No analysis available" description="The selected generation did not return an analysis payload." />}</div>;
}
