import { useQuery } from "@tanstack/react-query";

import { ConfidenceDistributionChart } from "@/charts/ConfidenceDistributionChart";
import { MonthlyTrendChart } from "@/charts/MonthlyTrendChart";
import { SimpleBarChart } from "@/charts/SimpleBarChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getTrends } from "@/services/dashboard";

export default function Analytics() {
  const { data: trends } = useQuery({ queryKey: ["dashboard", "trends"], queryFn: getTrends });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Analytics</h1>
        <p className="text-sm text-slate-500">Deeper insight into harmonization performance and savings.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>AI Confidence Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ConfidenceDistributionChart data={trends?.confidence_distribution ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Monthly Harmonization Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <MonthlyTrendChart data={trends?.monthly_trend ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Materials by CPSE</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={trends?.materials_by_cpse ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Harmonized Materials by CPSE</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={trends?.harmonized_by_cpse ?? []} color="#0ca30c" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Duplicate Material Reduction (by category)</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={trends?.duplicate_reduction ?? []} color="#4a3aa7" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Estimated Procurement Savings (₹, by category)</CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart
              data={trends?.estimated_savings ?? []}
              color="#eb6834"
              valueFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
