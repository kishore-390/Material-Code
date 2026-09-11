import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Clock,
  Copy,
  FileClock,
  GitCompareArrows,
  Landmark,
  Layers,
  Sparkles,
  Wallet,
} from "lucide-react";
import { Link } from "react-router-dom";

import { KpiCard } from "@/components/KpiCard";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listPendingApprovals } from "@/services/approvals";
import { getStatistics } from "@/services/dashboard";

function timeAgo(iso?: string | null): string {
  if (!iso) return "Never";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ["dashboard", "statistics"], queryFn: getStatistics, refetchInterval: 15000 });
  const { data: pending } = useQuery({ queryKey: ["approvals", "pending", "dashboard-widget"], queryFn: listPendingApprovals });

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Dashboard" }]}
        title="National Material Master Control Center"
        subtitle="Automatically ingested CPSE material data, harmonized by the AI pipeline into a single Common National Material Code."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link to="/synchronization">Data Synchronization</Link>
            </Button>
            <Button asChild>
              <Link to="/common-material-master">Common Materials</Link>
            </Button>
          </>
        }
      />

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">National Coverage</p>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard label="CPSEs Connected" value={stats?.cpses_connected ?? "—"} icon={Landmark} accent="brand" />
          <KpiCard label="Total Materials" value={stats?.total_materials ?? "—"} icon={Layers} accent="brand" />
          <KpiCard label="Common Material Codes" value={stats?.common_material_codes ?? "—"} icon={Layers} accent="success" />
          <KpiCard label="Last Synchronization" value={timeAgo(stats?.last_synchronization)} icon={Clock} accent="slate" />
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Harmonization Quality</p>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Link to="/harmonization/duplicates" className="block rounded transition hover:-translate-y-0.5 hover:shadow-md">
            <KpiCard label="Duplicates Identified" value={stats?.duplicates_identified ?? "—"} icon={Copy} accent="warning" hint="View Duplicates →" />
          </Link>
          <Link to="/harmonization/near-duplicates" className="block rounded transition hover:-translate-y-0.5 hover:shadow-md">
            <KpiCard label="Near Duplicates" value={stats?.near_duplicates ?? "—"} icon={GitCompareArrows} accent="brand" />
          </Link>
          <Link to="/harmonization/technical-conflicts" className="block rounded transition hover:-translate-y-0.5 hover:shadow-md">
            <KpiCard label="Technical Conflicts" value={stats?.technical_conflicts ?? "—"} icon={AlertTriangle} accent="danger" />
          </Link>
          <Link to="/approvals/pending" className="block rounded transition hover:-translate-y-0.5 hover:shadow-md">
            <KpiCard label="Pending Validation" value={stats?.pending_validation ?? "—"} icon={Clock} accent="warning" />
          </Link>
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Governance &amp; Procurement</p>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard label="Legacy Codes Rationalized" value={stats?.legacy_codes_rationalized ?? "—"} icon={FileClock} accent="slate" />
          <KpiCard label="New Materials Today" value={stats?.new_materials_today ?? "—"} icon={Sparkles} accent="brand" />
          <KpiCard
            label="Potential Procurement Aggregation"
            value={stats ? stats.potential_procurement_aggregation_value.toLocaleString() : "—"}
            icon={Wallet}
            accent="success"
            hint="Estimated quantity - not a savings claim"
          />
        </div>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Pending Validation</CardTitle>
          <Link to="/approvals/pending" className="text-xs font-medium text-brand-600 hover:underline">
            View all
          </Link>
        </CardHeader>
        <CardContent className="space-y-3">
          {(pending ?? []).slice(0, 5).map((mapping) => (
            <Link
              key={mapping.id}
              to={`/approvals/${mapping.id}`}
              className="flex items-center justify-between rounded border border-slate-200 p-3 hover:border-brand-100 hover:bg-brand-50/40"
            >
              <div>
                <p className="text-sm font-medium text-slate-800">{mapping.cpse_material.original_material_code}</p>
                <p className="text-xs text-slate-500">vs {mapping.matched_against?.original_material_code ?? "manual review"}</p>
              </div>
              <Badge variant="warning">
                {mapping.confidence_score ? `${mapping.confidence_score.toFixed(1)}%` : "Manual"}
              </Badge>
            </Link>
          ))}
          {(pending ?? []).length === 0 && (
            <p className="py-6 text-center text-sm text-slate-400">No pending validations right now.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
