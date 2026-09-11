import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listCollaborativeOpportunities } from "@/services/procurement";

export default function ProcurementAnalytics() {
  const { data, isLoading } = useQuery({
    queryKey: ["procurement", "opportunities"],
    queryFn: () => listCollaborativeOpportunities(20),
  });

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Analytics" }, { label: "Procurement Analytics" }]}
        title="Collaborative Procurement Opportunities"
        subtitle="Potential demand aggregation across CPSEs sharing the same Common Material Code - estimated opportunity only, never a claim of realized savings."
      />

      {isLoading && <p className="text-sm text-slate-400">Loading...</p>}
      {!isLoading && (data ?? []).length === 0 && (
        <div className="rounded border border-slate-200 bg-slate-50 p-10 text-center">
          <p className="text-sm font-medium text-slate-600">
            No procurement history is available yet to compute aggregation opportunities.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {data?.map((opp) => (
          <Card key={opp.common_code}>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle>{opp.common_code}</CardTitle>
              {opp.includes_demo_data && <Badge variant="warning">Includes Demo Data</Badge>}
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-slate-600">{opp.standardized_description}</p>
              <div className="space-y-1.5">
                {opp.cpse_demand.map((d) => (
                  <div key={d.cpse_code} className="flex items-center justify-between text-sm">
                    <span className="text-slate-700">{d.cpse_name} ({d.cpse_code})</span>
                    <span className="font-semibold tabular-nums">
                      {d.total_quantity.toLocaleString()} {d.uom}
                    </span>
                  </div>
                ))}
              </div>
              <div className="rounded bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">Total Potential Aggregated Demand</p>
                <p className="text-xl font-bold text-slate-900">
                  {opp.total_potential_aggregated_demand.toLocaleString()} {opp.uom}
                </p>
              </div>
              <p className="text-xs italic text-slate-400">{opp.note}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
