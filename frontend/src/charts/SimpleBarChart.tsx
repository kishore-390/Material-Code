import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART_BRAND_BLUE, CHART_INK } from "@/utils/chartColors";
import type { ChartPoint } from "@/types";

interface SimpleBarChartProps {
  data: ChartPoint[];
  color?: string;
  valueFormatter?: (value: number) => string;
  height?: number;
}

export function SimpleBarChart({ data, color = CHART_BRAND_BLUE, valueFormatter, height = 260 }: SimpleBarChartProps) {
  if (!data.length) {
    return <p className="py-10 text-center text-sm text-slate-400">No data available yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={CHART_INK.grid} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 12, fill: CHART_INK.muted }}
          axisLine={{ stroke: CHART_INK.grid }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 12, fill: CHART_INK.muted }}
          axisLine={false}
          tickLine={false}
          width={40}
          tickFormatter={valueFormatter}
        />
        <Tooltip
          cursor={{ fill: "rgba(42,120,214,0.06)" }}
          formatter={(value: number) => (valueFormatter ? valueFormatter(value) : value)}
          contentStyle={{ borderRadius: 8, borderColor: CHART_INK.grid, fontSize: 12 }}
        />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}
