import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function ActivityChart({ data }: { data: Array<{ date: string; generations: number }> }) {
  return <ResponsiveContainer width="100%" height="100%"><LineChart data={data}><CartesianGrid stroke="var(--chart-grid)" strokeDasharray="2 5" vertical={false} /><XAxis dataKey="date" stroke="var(--chart-muted)" tickLine={false} axisLine={false} fontSize={11} /><YAxis allowDecimals={false} stroke="var(--chart-muted)" tickLine={false} axisLine={false} fontSize={11} /><Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--hairline)", borderRadius: 16, color: "var(--copy)" }} /><Line type="monotone" dataKey="generations" stroke="var(--signal)" strokeWidth={2} dot={{ fill: "var(--signal)", strokeWidth: 0, r: 4 }} activeDot={{ r: 6 }} /></LineChart></ResponsiveContainer>;
}
