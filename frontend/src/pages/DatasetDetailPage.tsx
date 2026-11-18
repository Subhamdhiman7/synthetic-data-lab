import { useEffect, useState } from "react";
import { ArrowLeft, Download, FileText, RefreshCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { getApiError, getAnalysis, getDatasetDetails, getDownloadUrl, getPreview } from "../lib/api";
import type { AnalysisResponse, GenerationMetadata, PreviewResponse } from "../types/api";
import { DatasetPreviewTable } from "../components/DatasetPreviewTable";
import { AnalysisPanel } from "../components/AnalysisPanel";
import { Button, ErrorState, LoadingState, PageHeader, Panel, TaskBadge } from "../components/ui";
import { Reveal } from "../components/motion";

export function DatasetDetailPage() {
  const { generationId } = useParams<{ generationId: string }>(); const [details, setDetails] = useState<GenerationMetadata | null>(null); const [preview, setPreview] = useState<PreviewResponse | null>(null); const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const load = () => { if (!generationId) return; setLoading(true); setError(""); Promise.all([getDatasetDetails(generationId), getPreview(generationId), getAnalysis(generationId)]).then(([metadata, previewResult, analysisResult]) => { setDetails(metadata); setPreview(previewResult); setAnalysis(analysisResult); }).catch((reason) => setError(getApiError(reason))).finally(() => setLoading(false)); }; useEffect(load, [generationId]);
  if (loading) return <LoadingState label="Loading dataset" />; if (error || !details) return <ErrorState message={error || "This dataset could not be found."} onRetry={load} />;
  return <div><Reveal><PageHeader eyebrow="Dataset inspector / 03" title={details.dataset_name} description={`Generated ${new Date(details.created_at).toLocaleString()} · ${details.generation_id}`} actions={<><Link to="/datasets"><Button variant="ghost"><ArrowLeft size={15} /> Back</Button></Link><a href={getDownloadUrl(details.generation_id)}><Button><Download size={15} /> Download CSV</Button></a></>} /></Reveal><Reveal delay={.08}><Panel className="mb-6"><div className="grid gap-4 sm:grid-cols-4"><DetailMetric label="Task" value={<TaskBadge task={details.task} />} /><DetailMetric label="Rows" value={details.rows.toLocaleString()} /><DetailMetric label="Features" value={details.feature_count.toString()} /><DetailMetric label="Artifacts" value={`${Object.values(details.files).filter(Boolean).length}/3 ready`} /></div><div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-4 text-xs text-slate-500"><span className="inline-flex items-center gap-1.5"><FileText size={13} /> Generation ID <code className="text-slate-400">{details.generation_id}</code></span></div></Panel></Reveal><div className="space-y-6"><Reveal delay={.12}><DatasetPreviewTable preview={preview} /></Reveal>{analysis && <Reveal delay={.16}><AnalysisPanel analysis={analysis} /></Reveal>}</div><div className="mt-5 flex justify-end"><Button variant="ghost" onClick={load}><RefreshCw size={15} /> Refresh data</Button></div></div>;
}

function DetailMetric({ label, value }: { label: string; value: React.ReactNode }) { return <div className="rounded-xl border border-line bg-panelSoft/40 p-4"><p className="text-xs text-slate-500">{label}</p><div className="mt-2 font-display text-xl font-semibold text-white">{value}</div></div>; }
