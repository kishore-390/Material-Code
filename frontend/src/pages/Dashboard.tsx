import { useQueries, useQuery } from "@tanstack/react-query";
import {
  Boxes,
  Building2,
  CheckCircle2,
  Clock,
  IndianRupee,
  Layers,
  Sparkles,
  TrendingDown,
} from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { AIPipelineStrip } from "@/components/AIPipelineStrip";
import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
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

function bucketValue(points: { label: string; value: number }[] | undefined, label: string) {
  return points?.find((p) => p.label === label)?.value ?? 0;
}

const APPROVAL_STATUS_BREAKDOWN = [
  { status: "PENDING", label: "Pending", accent: "bg-warning-500" },
  { status: "APPROVED", label: "Approved", accent: "bg-success-500" },
  { status: "REJECTED", label: "Rejected", accent: "bg-danger-500" },
  { status: "MORE_INFO_REQUESTED", label: "More Info Requested", accent: "bg-slate-400" },
] as const;

export default function Dashboard() {
  const [cpseId, setCpseId] = React.useState("");
  const { data: stats } = useQuery({ queryKey: ["dashboard", "statistics", cpseId], queryFn: () => getStatistics(cpseId) });
  const { data: trends } = useQuery({ queryKey: ["dashboard", "trends", cpseId], queryFn: () => getTrends(cpseId) });
  const { data: pendingApprovals } = useQuery({
    queryKey: ["approvals", "PENDING", "dashboard-widget", cpseId],
    queryFn: () => listApprovals("PENDING", cpseId),
  });
  const potentialCostSavings = (trends?.estimated_savings ?? []).reduce((sum, p) => sum + p.value, 0);

  const approvalStatusQueries = useQueries({
    queries: APPROVAL_STATUS_BREAKDOWN.map(({ status }) => ({
      queryKey: ["approvals", status, "dashboard-breakdown", cpseId],
      queryFn: () => listApprovals(status, cpseId),
    })),
  });
  const approvalStatusCounts = APPROVAL_STATUS_BREAKDOWN.map((s, idx) => ({
    ...s,
    count: approvalStatusQueries[idx]?.data?.length ?? 0,
  }));
  const approvalStatusTotal = approvalStatusCounts.reduce((sum, s) => sum + s.count, 0);

  const highConfidence = bucketValue(trends?.confidence_distribution, "95-100%");
  const mediumConfidence = bucketValue(trends?.confidence_distribution, "85-95%");
  const lowConfidence =
    bucketValue(trends?.confidence_distribution, "60-85%") + bucketValue(trends?.confidence_distribution, "Below 60%");
  const confidenceTotal = highConfidence + mediumConfidence + lowConfidence;

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Dashboard" }]}
        title="CPSE Material Harmonization Control Center"
        subtitle="Centralized overview of AI-assisted material harmonization across participating CPSEs."
        actions={
          <>
            <OrganizationSelect includeAllOption value={cpseId} onChange={(e) => setCpseId(e.target.value)} className="max-w-[220px]" />
            <Button asChild>
              <Link to="/approvals">Review Approvals</Link>
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard label="Total Materials" value={stats?.total_materials ?? "—"} icon={Boxes} accent="brand" />
        <KpiCard
          label="Materials Harmonized"
          value={stats?.harmonized_materials ?? "—"}
          icon={CheckCircle2}
          accent="success"
        />
        <KpiCard
          label="Duplicate Materials Detected"
          value={stats?.duplicate_codes_reduced ?? "—"}
          icon={TrendingDown}
          accent="danger"
        />
        <KpiCard
          label="Pending Approvals"
          value={stats?.pending_human_approvals ?? "—"}
          icon={Clock}
          accent="warning"
        />
        <KpiCard label="CPSEs Connected" value={stats?.cpses_onboarded ?? "—"} icon={Building2} accent="slate" />
        <KpiCard
          label="Potential Cost Savings"
          value={`₹${(potentialCostSavings / 1000).toFixed(0)}k`}
          icon={IndianRupee}
          accent="brand"
        />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <KpiCard label="AI Recommendations" value={stats?.ai_recommendations ?? "—"} icon={Sparkles} accent="brand" />
        <KpiCard label="Common Codes Generated" value={stats?.common_codes_generated ?? "—"} icon={Layers} accent="success" />
        <KpiCard label="Approved Common Codes" value={stats?.approved_common_codes ?? "—"} icon={CheckCircle2} accent="success" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>National Harmonization Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-2 sm:flex-row sm:justify-center sm:gap-4">
            <FunnelStage label="CPSE Materials" value={stats?.total_materials} />
            <span className="text-slate-300">→</span>
            <FunnelStage label="Equivalent Material Groups" value={stats?.common_codes_generated} />
            <span className="text-slate-300">→</span>
            <FunnelStage label="Approved Common Codes" value={stats?.approved_common_codes} accent="text-success-700" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Processing Status</CardTitle>
        </CardHeader>
        <CardContent>
          <AIPipelineStrip />
          <p className="mt-2 text-xs text-slate-400">
            AI-first automated pipeline with human-in-the-loop validation before a common material code is finalized.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Harmonization Overview</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <ConfidenceTile label="High Confidence Matches" value={highConfidence} total={confidenceTotal} accent="bg-success-500" />
          <ConfidenceTile label="Medium Confidence Matches" value={mediumConfidence} total={confidenceTotal} accent="bg-warning-500" />
          <ConfidenceTile label="Low Confidence Matches" value={lowConfidence} total={confidenceTotal} accent="bg-danger-500" />
        </CardContent>
      </Card>

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
            <CardTitle>Material Harmonization Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <MonthlyTrendChart data={trends?.monthly_trend ?? []} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
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
            <CardTitle>Duplicate Detection Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <MonthlyTrendChart data={trends?.duplicate_reduction ?? []} />
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
                className="flex items-center justify-between rounded border border-slate-200 p-3 hover:border-brand-100 hover:bg-brand-50/40"
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
            <CardTitle>Approval Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {approvalStatusCounts.map((s) => {
              const pct = approvalStatusTotal > 0 ? (s.count / approvalStatusTotal) * 100 : 0;
              return (
                <div key={s.status}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-600">{s.label}</span>
                    <span className="tabular-nums text-slate-500">{s.count}</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100">
                    <div className={`h-2 rounded-full ${s.accent}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
            {approvalStatusTotal === 0 && (
              <p className="py-4 text-center text-sm text-slate-400">No approval activity recorded yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Estimated Procurement Savings (by category, ₹)</CardTitle>
        </CardHeader>
        <CardContent>
          <SimpleBarChart
            data={trends?.estimated_savings ?? []}
            color="#ff9933"
            valueFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function FunnelStage({ label, value, accent }: { label: string; value?: number; accent?: string }) {
  return (
    <div className="rounded border border-slate-300 bg-slate-50 px-5 py-3 text-center">
      <p className={`text-2xl font-bold ${accent ?? "text-slate-900"}`}>{value ?? "—"}</p>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
    </div>
  );
}

function ConfidenceTile({
  label,
  value,
  total,
  accent,
}: {
  label: string;
  value: number;
  total: number;
  accent: string;
}) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
        <span className="text-lg font-bold text-slate-900">{value}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${accent}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
