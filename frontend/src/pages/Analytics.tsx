import { useQuery } from "@tanstack/react-query";
import * as React from "react";

import { ConfidenceDistributionChart } from "@/charts/ConfidenceDistributionChart";
import { MonthlyTrendChart } from "@/charts/MonthlyTrendChart";
import { SimpleBarChart } from "@/charts/SimpleBarChart";
import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getTrends } from "@/services/dashboard";

export default function Analytics() {
  const [cpseId, setCpseId] = React.useState("");
  const { data: trends } = useQuery({
    queryKey: ["dashboard", "trends", cpseId],
    queryFn: () => getTrends(cpseId),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Reports & Monitoring", to: "/analytics" }, { label: "Analytics" }]}
        title="Analytics"
        subtitle="Deeper insight into harmonization performance and savings."
        actions={<OrganizationSelect includeAllOption value={cpseId} onChange={(e) => setCpseId(e.target.value)} className="max-w-[220px]" />}
      />

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
            <CardTitle>Material Harmonization Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <MonthlyTrendChart data={trends?.monthly_trend ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>CPSE-wise Material Distribution</CardTitle>
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
            <SimpleBarChart data={trends?.harmonized_by_cpse ?? []} color="#138808" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Duplicate Reduction Trend (by category)</CardTitle>
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
