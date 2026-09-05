import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw, ScanLine } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { CommonMaterialGroupCard } from "@/components/CommonMaterialGroupCard";
import { HarmonizationFlowDiagram } from "@/components/HarmonizationFlowDiagram";
import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listCPSE } from "@/services/cpse";
import {
  getScanStatus,
  listHarmonizationRequests,
  scanMaterialMasters,
} from "@/services/harmonization";
import type { ScanStatusItem } from "@/types";

const PIPELINE_STAGES = [
  "Data Ingestion",
  "Data Normalization",
  "Specification Extraction",
  "SBERT Embedding",
  "pgvector Candidate Search",
  "XGBoost Matching",
  "Equivalence Detection",
  "Conflict Detection",
  "Common Code Generation",
];

const STATUSES = ["PENDING", "APPROVED", "AUTO_APPROVED", "REJECTED", "MORE_INFO_REQUESTED"];

export default function Harmonization() {
  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "AI Harmonization", to: "/harmonization" }, { label: "AI National Material Harmonization" }]}
        title="AI National Material Harmonization"
        subtitle="AI-powered harmonization of CPSE material masters into a unified Common Material Code."
      />

      <HarmonizationFlowDiagram />

      <NationalHarmonizationPanel />

      <RecentHarmonizationActivity />
    </div>
  );
}

function NationalHarmonizationPanel() {
  const [cpseId, setCpseId] = React.useState("");
  const [materialIds, setMaterialIds] = React.useState<string[] | null>(null);

  const { data: orgs } = useQuery({ queryKey: ["cpse"], queryFn: listCPSE });

  const scanMutation = useMutation({
    mutationFn: () => scanMaterialMasters(cpseId || undefined),
    onSuccess: (result) => setMaterialIds(result.material_ids),
  });

  const { data: status } = useQuery({
    queryKey: ["harmonization", "scan-status", materialIds],
    queryFn: () => getScanStatus(materialIds as string[]),
    enabled: !!materialIds && materialIds.length > 0,
    refetchInterval: (query) => (query.state.data && query.state.data.completed >= query.state.data.total ? false : 1500),
  });

  const isDone = !!status && status.completed >= status.total;
  const groups = React.useMemo(() => groupByCommonCode(status?.items ?? []), [status]);
  const ungrouped = (status?.items ?? []).filter((i) => !i.common_code);

  return (
    <Card>
      <CardHeader>
        <CardTitle>CPSE Data Sources</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {(orgs ?? []).map((org) => (
            <div key={org.id} className="flex items-center justify-between rounded border border-slate-200 px-3 py-2">
              <span className="flex items-center gap-1.5 text-sm font-medium text-slate-700">
                <span className={`h-2 w-2 rounded-full ${org.total_materials > 0 ? "bg-success-500" : "bg-slate-300"}`} />
                {org.code}
              </span>
              <span className="text-xs text-slate-500">Materials: {org.total_materials}</span>
            </div>
          ))}
          {(orgs ?? []).length === 0 && <p className="text-sm text-slate-400">No organizations onboarded yet.</p>}
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3">
          <OrganizationSelect includeAllOption value={cpseId} onChange={(e) => setCpseId(e.target.value)} className="max-w-[220px]" />
          <Button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
            <ScanLine className="h-4 w-4" />
            {scanMutation.isPending ? "Starting Scan..." : "Scan Material Masters"}
          </Button>
          {materialIds && (
            <Button variant="outline" size="sm" onClick={() => setMaterialIds(null)}>
              Clear Results
            </Button>
          )}
        </div>

        {scanMutation.isSuccess && scanMutation.data.queued === 0 && (
          <p className="text-sm text-slate-400">No un-harmonized materials available to scan right now.</p>
        )}

        {materialIds && materialIds.length > 0 && (
          <div className="space-y-4 border-t border-slate-200 pt-4">
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-700">AI Processing Status</p>
              <div className="flex flex-wrap gap-2">
                {PIPELINE_STAGES.map((stage) => (
                  <span
                    key={stage}
                    className="flex items-center gap-1.5 rounded border border-slate-300 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700"
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${isDone ? "bg-success-500" : "bg-brand-600"}`} />
                    {stage}
                  </span>
                ))}
                <span className="flex items-center gap-1.5 rounded border border-slate-300 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
                  <span className={`h-1.5 w-1.5 rounded-full ${isDone ? "bg-success-500" : "bg-warning-500 animate-pulse"}`} />
                  Validation
                </span>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {status ? `${status.completed} / ${status.total} materials processed` : "Starting..."}
                {isDone ? " — scan complete." : " — this reflects real, database-derived progress, not a simulated percentage."}
              </p>
            </div>

            {groups.length > 0 && (
              <div className="space-y-3">
                <p className="text-sm font-semibold text-slate-700">AI Identified Common Material Groups</p>
                {groups.map((g) => (
                  <CommonMaterialGroupCard key={g.code} code={g.code} standardDescription={g.description} items={g.items} />
                ))}
              </div>
            )}

            {isDone && ungrouped.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-semibold text-slate-700">Not Yet Grouped</p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>CPSE</TableHead>
                      <TableHead>Material Code</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>AI Decision</TableHead>
                      <TableHead>Conflict</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ungrouped.map((item) => (
                      <TableRow key={item.material_id}>
                        <TableCell>{item.cpse_code}</TableCell>
                        <TableCell>
                          <Link to={`/materials/${item.material_id}`} className="font-medium text-brand-600 hover:underline">
                            {item.material_code}
                          </Link>
                        </TableCell>
                        <TableCell className="max-w-xs truncate">{item.description}</TableCell>
                        <TableCell>
                          {item.latest_decision ? <StatusBadge status={item.latest_decision} /> : <Badge variant="outline">Pending</Badge>}
                        </TableCell>
                        <TableCell>
                          {item.technical_conflict ? <Badge variant="warning">Conflict</Badge> : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function groupByCommonCode(items: ScanStatusItem[]) {
  const map = new Map<string, { code: string; description: string; items: ScanStatusItem[] }>();
  for (const item of items) {
    if (!item.common_code) continue;
    const existing = map.get(item.common_code.code);
    if (existing) {
      existing.items.push(item);
    } else {
      map.set(item.common_code.code, {
        code: item.common_code.code,
        description: item.common_code.standard_description,
        items: [item],
      });
    }
  }
  return Array.from(map.values());
}

function RecentHarmonizationActivity() {
  const [status, setStatus] = React.useState("");
  const [cpseId, setCpseId] = React.useState("");
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["harmonization", status, cpseId],
    queryFn: () => listHarmonizationRequests(status || undefined, cpseId || undefined),
  });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Recent Harmonization Activity</CardTitle>
          <p className="mt-0.5 text-xs text-slate-500">
            Every AI recommendation and manual request that could lead to a Common Material Code.
          </p>
        </div>
        <div className="flex gap-2">
          <OrganizationSelect includeAllOption value={cpseId} onChange={(e) => setCpseId(e.target.value)} className="max-w-[180px]" />
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-[180px]">
            <option value="">All Statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
          <Button variant="outline" size="sm" onClick={() => queryClient.invalidateQueries({ queryKey: ["harmonization"] })}>
            <RefreshCcw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">Sl.No.</TableHead>
              <TableHead>Material</TableHead>
              <TableHead>Candidate</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>AI Score</TableHead>
              <TableHead>Common Code</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-slate-400">Loading...</TableCell>
              </TableRow>
            )}
            {!isLoading && (data ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-slate-400">No harmonization requests found.</TableCell>
              </TableRow>
            )}
            {data?.map((h, idx) => (
              <TableRow key={h.id}>
                <TableCell className="text-slate-400">{idx + 1}</TableCell>
                <TableCell>
                  <Link to={`/harmonization/${h.id}`} className="font-medium text-brand-600 hover:underline">
                    {h.material.material_code}
                  </Link>
                </TableCell>
                <TableCell>{h.candidate?.material_code ?? "—"}</TableCell>
                <TableCell>{h.request_type}</TableCell>
                <TableCell>{h.ai_score ? `${h.ai_score.toFixed(1)}%` : "—"}</TableCell>
                <TableCell>{h.common_code?.code ?? "—"}</TableCell>
                <TableCell>
                  <StatusBadge status={h.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
