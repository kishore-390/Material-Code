import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CHART_BRAND_BLUE, CHART_INK } from "@/utils/chartColors";
import type { ChartPoint } from "@/types";

export function MonthlyTrendChart({ data }: { data: ChartPoint[] }) {
  if (!data.length) {
    return <p className="py-10 text-center text-sm text-slate-400">No harmonizations recorded yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={CHART_INK.grid} />
        <XAxis dataKey="label" tick={{ fontSize: 12, fill: CHART_INK.muted }} axisLine={{ stroke: CHART_INK.grid }} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: CHART_INK.muted }} axisLine={false} tickLine={false} width={40} allowDecimals={false} />
        <Tooltip contentStyle={{ borderRadius: 8, borderColor: CHART_INK.grid, fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="value"
          stroke={CHART_BRAND_BLUE}
          strokeWidth={2}
          dot={{ r: 4, fill: CHART_BRAND_BLUE }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
