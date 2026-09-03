import { useQuery } from "@tanstack/react-query";
import {
  Boxes,
  Building2,
  CheckCircle2,
  Clock,
  Layers,
  Sparkles,
  TrendingDown,
} from "lucide-react";
import { Link } from "react-router-dom";

import { KpiCard } from "@/components/KpiCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceDistributionChart } from "@/charts/ConfidenceDistributionChart";
import { HarmonizationProgressChart } from "@/charts/HarmonizationProgressChart";
import { MonthlyTrendChart } from "@/charts/MonthlyTrendChart";
import { SimpleBarChart } from "@/charts/SimpleBarChart";
import { listApprovals } from "@/services/approvals";
import { getStatistics, getTrends } from "@/services/dashboard";

export default function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ["dashboard", "statistics"], queryFn: getStatistics });
  const { data: trends } = useQuery({ queryKey: ["dashboard", "trends"], queryFn: getTrends });
  const { data: pendingApprovals } = useQuery({
    queryKey: ["approvals", "PENDING", "dashboard-widget"],
    queryFn: () => listApprovals("PENDING"),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">Real-time harmonization overview across all CPSEs</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/materials/upload">Upload Material</Link>
          </Button>
          <Button asChild>
            <Link to="/approvals">Review Approvals</Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Total Materials" value={stats?.total_materials ?? "—"} icon={Boxes} accent="brand" />
        <KpiCard
          label="Harmonized Materials"
          value={stats?.harmonized_materials ?? "—"}
          icon={CheckCircle2}
          accent="success"
        />
        <KpiCard
          label="Pending Human Approvals"
          value={stats?.pending_human_approvals ?? "—"}
          icon={Clock}
          accent="warning"
        />
        <KpiCard label="CPSEs Onboarded" value={stats?.cpses_onboarded ?? "—"} icon={Building2} accent="slate" />
        <KpiCard
          label="Duplicate Codes Reduced"
          value={stats?.duplicate_codes_reduced ?? "—"}
          icon={TrendingDown}
          accent="danger"
        />
        <KpiCard label="AI Recommendations" value={stats?.ai_recommendations ?? "—"} icon={Sparkles} accent="brand" />
        <KpiCard label="Common Codes Generated" value={stats?.common_codes_generated ?? "—"} icon={Layers} accent="success" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Harmonization Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <HarmonizationProgressChart data={trends?.harmonization_progress ?? []} />
          </CardContent>
        </Card>
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
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
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
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle>Pending Approvals</CardTitle>
            <Link to="/approvals" className="text-xs font-medium text-brand-600 hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {(pendingApprovals ?? []).slice(0, 5).map((approval) => (
              <Link
                key={approval.id}
                to={`/approvals/${approval.id}`}
                className="flex items-center justify-between rounded-lg border border-slate-100 p-3 hover:border-brand-200 hover:bg-brand-50/40"
              >
                <div>
                  <p className="text-sm font-medium text-slate-800">{approval.material.material_code}</p>
                  <p className="text-xs text-slate-500">vs {approval.candidate?.material_code ?? "manual review"}</p>
                </div>
                <Badge variant="warning">{approval.ai_score ? `${approval.ai_score.toFixed(1)}%` : "Manual"}</Badge>
              </Link>
            ))}
            {(pendingApprovals ?? []).length === 0 && (
              <p className="py-6 text-center text-sm text-slate-400">No pending approvals right now.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Estimated Procurement Savings (by category, ₹)</CardTitle>
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
