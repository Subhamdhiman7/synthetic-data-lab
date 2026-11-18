import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { getApiError, getHistory } from "../lib/api";
import { DatasetTable } from "../components/DatasetTable";
import { ErrorState, LoadingState, PageHeader, Panel } from "../components/ui";
import { Reveal } from "../components/motion";
import type { GenerationMetadata } from "../types/api";

export function DatasetsPage() {
  const [items, setItems] = useState<GenerationMetadata[]>([]); const [query, setQuery] = useState(""); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const load = () => { setLoading(true); getHistory(100, 0).then((response) => setItems(response.items)).catch((reason) => setError(getApiError(reason))).finally(() => setLoading(false)); }; useEffect(load, []);
  const filtered = useMemo(() => items.filter((item) => `${item.dataset_name} ${item.task} ${item.generation_id}`.toLowerCase().includes(query.toLowerCase())), [items, query]);
  return <div><Reveal><PageHeader eyebrow="Library / 03" title="My datasets" description="Every generated artifact persisted by the backend, arranged for quick inspection and retrieval." /></Reveal><Reveal delay={.08}><Panel className="p-0"><div className="flex flex-col gap-4 border-b border-line px-5 py-5 sm:flex-row sm:items-center sm:justify-between"><div><p className="eyebrow">Dataset library</p><p className="mt-2 text-sm text-slate-500">Showing the latest 100 persisted generations.</p></div><label className="relative block sm:w-72"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" /><input aria-label="Search datasets" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search datasets…" className="field-input pl-9" /></label></div>{loading ? <div className="p-5"><LoadingState label="Loading datasets" /></div> : error ? <div className="p-5"><ErrorState message={error} onRetry={load} /></div> : <DatasetTable items={filtered} emptyMessage={query ? "No datasets match your search." : "No generated datasets yet."} />}</Panel></Reveal></div>;
}
