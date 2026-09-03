import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { CHART_STATUS } from "@/utils/chartColors";
import type { ChartPoint } from "@/types";

const COLOR_BY_LABEL: Record<string, string> = {
  Harmonized: CHART_STATUS.good,
  "Pending Review": CHART_STATUS.warning,
  "Not Harmonized": CHART_STATUS.neutral,
};

export function HarmonizationProgressChart({ data }: { data: ChartPoint[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  if (!total) {
    return <p className="py-10 text-center text-sm text-slate-400">No materials uploaded yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="label"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={2}
          strokeWidth={2}
          stroke="#fff"
        >
          {data.map((entry) => (
            <Cell key={entry.label} fill={COLOR_BY_LABEL[entry.label] ?? CHART_STATUS.neutral} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string) => [`${value} materials`, name]}
          contentStyle={{ borderRadius: 8, fontSize: 12 }}
        />
        <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
