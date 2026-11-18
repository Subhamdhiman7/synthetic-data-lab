import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { getApiError, getHistory } from "../lib/api";
import { formatNumber } from "../lib/format";
import type { GenerationMetadata } from "../types/api";
import { DatasetTable } from "../components/DatasetTable";
import { Button, ErrorState, LoadingState, PageHeader, Panel } from "../components/ui";
import { Reveal } from "../components/motion";

export function HistoryPage() {
  const pageSize = 20; const [items, setItems] = useState<GenerationMetadata[]>([]); const [total, setTotal] = useState(0); const [offset, setOffset] = useState(0); const [query, setQuery] = useState(""); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const load = () => { setLoading(true); setError(""); getHistory(pageSize, offset).then((response) => { setItems(response.items); setTotal(response.total); }).catch((reason) => setError(getApiError(reason))).finally(() => setLoading(false)); }; useEffect(load, [offset]);
  const filtered = useMemo(() => items.filter((item) => `${item.dataset_name} ${item.task} ${item.generation_id}`.toLowerCase().includes(query.toLowerCase())), [items, query]); const page = Math.floor(offset / pageSize) + 1; const pages = Math.max(1, Math.ceil(total / pageSize));
  return <div><Reveal><PageHeader eyebrow="Traceability / 05" title="Generation history" description="A living trail of the local engine: what was generated, when it was created, and where to inspect it." /></Reveal><Reveal delay={.08}><Panel className="p-0"><div className="flex flex-col gap-4 border-b border-line px-5 py-5 sm:flex-row sm:items-center sm:justify-between"><div><p className="eyebrow">All generations</p><p className="mt-2 text-sm text-slate-500">{formatNumber(total)} total records</p></div><label className="relative block sm:w-72"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" /><input aria-label="Search history" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this page…" className="field-input pl-9" /></label></div>{loading ? <div className="p-5"><LoadingState label="Loading history" /></div> : error ? <div className="p-5"><ErrorState message={error} onRetry={load} /></div> : <><DatasetTable items={filtered} emptyMessage={query ? "No history entries match your search." : "No history entries yet."} /><div className="flex items-center justify-between border-t border-line px-5 py-4"><p className="font-mono text-xs text-slate-500">Page {page} of {pages}</p><div className="flex gap-2"><Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}><ChevronLeft size={15} /> Previous</Button><Button variant="ghost" disabled={offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)}>Next <ChevronRight size={15} /></Button></div></div></>}</Panel></Reveal></div>;
}
