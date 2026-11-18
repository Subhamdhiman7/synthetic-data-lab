import { Table2 } from "lucide-react";
import type { PreviewResponse } from "../types/api";
import { formatNumber } from "../lib/format";
import { EmptyState, Panel } from "./ui";

export function DatasetPreviewTable({ preview }: { preview: PreviewResponse | null }) {
  if (!preview || preview.records.length === 0) {
    return <EmptyState title="No preview available" description="This dataset did not return preview rows from the backend." />;
  }
  return (
    <Panel className="overflow-hidden p-0">
      <div className="flex flex-col gap-2 border-b border-line px-5 py-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><span className="rounded-full bg-cyan/10 p-2 text-cyan"><Table2 size={17} /></span><div><p className="eyebrow">Preview / first rows</p><h3 className="mt-2 font-display font-semibold text-white">Dataset preview</h3><p className="text-xs text-slate-500">First {Math.min(preview.records.length, 20)} rows · {preview.columns.length} columns</p></div></div><span className="font-mono text-xs text-slate-500">{formatNumber(preview.row_count)} total rows</span></div>
      <div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="bg-panelSoft/40 text-[10px] uppercase tracking-[.15em] text-slate-500"><tr><th className="sticky left-0 bg-panel px-5 py-3 font-semibold">#</th>{preview.columns.map((column) => <th key={column} className="whitespace-nowrap px-5 py-3 font-semibold">{column}<span className="ml-2 normal-case tracking-normal text-slate-600">{preview.data_types[column]}</span></th>)}</tr></thead><tbody>{preview.records.map((record, index) => <tr key={`${preview.generation_id}-${index}`} className="table-row"><td className="sticky left-0 bg-panel px-5 py-3 font-mono text-xs text-slate-600">{index + 1}</td>{preview.columns.map((column) => <td key={column} className="max-w-64 whitespace-nowrap px-5 py-3 font-mono text-xs text-slate-300">{formatCell(record[column])}</td>)}</tr>)}</tbody></table></div>
    </Panel>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === "") return "null";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
