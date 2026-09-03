import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CHART_INK, CHART_SEQUENTIAL_BLUE } from "@/utils/chartColors";
import type { ChartPoint } from "@/types";

export function ConfidenceDistributionChart({ data }: { data: ChartPoint[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  if (!total) {
    return <p className="py-10 text-center text-sm text-slate-400">No AI analyses completed yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={CHART_INK.grid} />
        <XAxis dataKey="label" tick={{ fontSize: 12, fill: CHART_INK.muted }} axisLine={{ stroke: CHART_INK.grid }} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: CHART_INK.muted }} axisLine={false} tickLine={false} width={40} allowDecimals={false} />
        <Tooltip
          formatter={(value: number) => [`${value} analyses`, "Count"]}
          contentStyle={{ borderRadius: 8, borderColor: CHART_INK.grid, fontSize: 12 }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48}>
          {data.map((entry, index) => (
            <Cell key={entry.label} fill={CHART_SEQUENTIAL_BLUE[index % CHART_SEQUENTIAL_BLUE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
