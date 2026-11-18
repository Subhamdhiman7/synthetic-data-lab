import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function AnalysisDistributionChart({ data }: { data: Array<{ label: string; count: number }> }) {
  return <ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ left: 0, right: 12, bottom: 25 }}><CartesianGrid stroke="var(--chart-grid)" strokeDasharray="2 5" vertical={false} /><XAxis dataKey="label" stroke="var(--chart-muted)" tickLine={false} axisLine={false} fontSize={10} angle={-25} textAnchor="end" height={50} /><YAxis allowDecimals={false} stroke="var(--chart-muted)" tickLine={false} axisLine={false} fontSize={11} /><Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--hairline)", borderRadius: 16, color: "var(--copy)" }} /><Bar dataKey="count" fill="var(--signal)" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer>;
}
