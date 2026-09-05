import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ScanLine } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { HarmonizationFlowDiagram } from "@/components/HarmonizationFlowDiagram";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listCPSE } from "@/services/cpse";
import { fullDatabaseScan, getScanStatus } from "@/services/harmonization";
import type { ScanStatusItem } from "@/types";

const SCOPE_CPSES = ["IOCL", "ONGC"];

const PIPELINE_STAGES = [
  "Data Cleaning & Normalization",
  "Technical Attribute Extraction",
  "SBERT Embeddings",
  "Global Vector Candidate Retrieval",
  "XGBoost / AI Ranking",
  "Technical Conflict Detection",
  "Equivalence Decision",
  "Group Reconciliation",
  "Common Code Recommendation",
];

function groupByCommonCode(items: ScanStatusItem[]) {
  const map = new Map<string, { code: string; description: string; status: string; items: ScanStatusItem[] }>();
  for (const item of items) {
    if (!item.common_code) continue;
    const existing = map.get(item.common_code.code);
    if (existing) {
      existing.items.push(item);
    } else {
      map.set(item.common_code.code, {
        code: item.common_code.code,
        description: item.common_code.standard_description,
        status: item.common_code.status,
        items: [item],
      });
    }
  }
  return Array.from(map.values());
}

export default function FullDatabaseAnalysis() {
  const [materialIds, setMaterialIds] = React.useState<string[] | null>(null);

  const { data: orgs } = useQuery({ queryKey: ["cpse"], queryFn: listCPSE });
  const scopedOrgs = (orgs ?? []).filter((o) => SCOPE_CPSES.includes(o.code));

  const scanMutation = useMutation({
    mutationFn: () => fullDatabaseScan(),
    onSuccess: (result) => setMaterialIds(result.material_ids),
  });

  const { data: status } = useQuery({
    queryKey: ["harmonization", "full-database-scan-status", materialIds],
    queryFn: () => getScanStatus(materialIds as string[]),
    enabled: !!materialIds && materialIds.length > 0,
    refetchInterval: (query) => (query.state.data && query.state.data.completed >= query.state.data.total ? false : 1500),
  });

  const isDone = !!status && status.completed >= status.total;
  const items = status?.items ?? [];
  const groups = React.useMemo(() => groupByCommonCode(items), [items]);
  const conflicts = items.filter((i) => i.technical_conflict);
  const pendingValidation = items.filter((i) => !i.common_code && i.latest_decision === "HUMAN_REVIEW_REQUIRED");
  const unmatched = items.filter(
    (i) => !i.common_code && (i.latest_decision === "LOW_CONFIDENCE" || i.latest_decision === "NO_COMMON_CODE")
  );
  const completedPct = status && status.total > 0 ? Math.round((status.completed / status.total) * 100) : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "AI Harmonization", to: "/harmonization" }, { label: "AI Full Database Analysis" }]}
        title="AI Full Database Analysis"
        subtitle="AI-powered analysis of complete CPSE material masters for national material harmonization. Prototype scope: IOCL and ONGC."
      />

      <HarmonizationFlowDiagram cpseCodes={SCOPE_CPSES} />

      <Card>
        <CardHeader>
          <CardTitle>CPSE Databases</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {scopedOrgs.map((org) => (
              <div key={org.id} className="rounded border border-slate-300 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-800">{org.code}</span>
                  <Badge variant={org.is_active ? "success" : "outline"}>{org.is_active ? "Active" : "Inactive"}</Badge>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-500">
                  <div>
                    <p className="text-lg font-bold text-slate-900">{org.total_materials}</p>
                    <p>Total Materials</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-slate-900">{org.harmonized_materials}</p>
                    <p>Harmonized</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-slate-900">{org.pending_approvals}</p>
                    <p>Pending Review</p>
                  </div>
                </div>
              </div>
            ))}
            {scopedOrgs.length === 0 && (
              <p className="text-sm text-slate-400">IOCL / ONGC organizations are not onboarded yet.</p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3">
            <Button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
              <ScanLine className="h-4 w-4" />
              {scanMutation.isPending ? "Starting Scan..." : "Scan Entire Database"}
            </Button>
            {materialIds && (
              <Button variant="outline" size="sm" onClick={() => setMaterialIds(null)}>
                Clear Results
              </Button>
            )}
          </div>

          {scanMutation.isSuccess && scanMutation.data.queued === 0 && (
            <p className="text-sm text-slate-400">
              No IOCL/ONGC materials require (re-)analysis right now - every material is either already approved or
              currently processing.
            </p>
          )}
        </CardContent>
      </Card>

      {materialIds && materialIds.length > 0 && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Live Processing Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
                <Stat label="Total Materials" value={status?.total} />
                <Stat label="Materials Analyzed" value={status?.completed} />
                <Stat label="Equivalent Groups" value={groups.length} />
                <Stat label="Common Codes" value={groups.length} />
                <Stat label="Technical Conflicts" value={conflicts.length} accent="text-warning-600" />
                <Stat label="Pending Validation" value={pendingValidation.length} accent="text-warning-600" />
                <Stat label="Unmatched" value={unmatched.length} accent="text-slate-500" />
                <Stat label="Completed" value={`${completedPct}%`} accent="text-brand-600" />
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Current Stage: {isDone ? "Complete" : "Processing"}
                </p>
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
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {status?.completed ?? 0} / {status?.total ?? 0} materials analyzed - real, database-derived
                  progress from the scan just triggered, not a simulated percentage.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI Discovered Common Material Groups</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Common Code</TableHead>
                    <TableHead>CPSEs</TableHead>
                    <TableHead>Material Count</TableHead>
                    <TableHead>Material Codes</TableHead>
                    <TableHead>Standardized Description</TableHead>
                    <TableHead>AI Confidence</TableHead>
                    <TableHead>Technical Status</TableHead>
                    <TableHead>Validation Status</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groups.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-slate-400">
                        No harmonized material groups discovered yet in this scan.
                      </TableCell>
                    </TableRow>
                  )}
                  {groups.map((g) => {
                    const cpses = Array.from(new Set(g.items.map((i) => i.cpse_code))).sort();
                    const confidence = g.items.find((i) => i.ai_confidence != null)?.ai_confidence;
                    const hasConflict = g.items.some((i) => i.technical_conflict);
                    return (
                      <TableRow key={g.code}>
                        <TableCell>
                          <Link to={`/common-material-master/${g.code}`} className="font-semibold text-brand-600 hover:underline">
                            {g.code}
                          </Link>
                        </TableCell>
                        <TableCell>{cpses.join(" + ")}</TableCell>
                        <TableCell>{g.items.length}</TableCell>
                        <TableCell className="text-xs">{g.items.map((i) => i.material_code).join(" / ")}</TableCell>
                        <TableCell className="max-w-xs truncate">{g.description}</TableCell>
                        <TableCell>{confidence != null ? `${confidence.toFixed(1)}%` : "—"}</TableCell>
                        <TableCell>
                          {hasConflict ? <Badge variant="warning">Conflict</Badge> : <Badge variant="success">No Conflict</Badge>}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={g.status} />
                        </TableCell>
                        <TableCell className="text-right">
                          <Link to={`/common-material-master/${g.code}`} className="text-xs font-medium text-brand-600 hover:underline">
                            View
                          </Link>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-warning-600" />
                Technical Conflicts Requiring Review
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>IOCL Code</TableHead>
                    <TableHead>ONGC Code</TableHead>
                    <TableHead>Material Type</TableHead>
                    <TableHead>Conflict Reason</TableHead>
                    <TableHead>AI Confidence</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Review</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {conflicts.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-slate-400">
                        No technical conflicts detected in this scan.
                      </TableCell>
                    </TableRow>
                  )}
                  {conflicts.map((item) => {
                    const ioclCode = item.cpse_code === "IOCL" ? item.material_code : item.best_candidate_material_code;
                    const ongcCode = item.cpse_code === "ONGC" ? item.material_code : item.best_candidate_material_code;
                    return (
                      <TableRow key={item.material_id}>
                        <TableCell className="font-mono text-xs">{ioclCode ?? "—"}</TableCell>
                        <TableCell className="font-mono text-xs">{ongcCode ?? "—"}</TableCell>
                        <TableCell>{item.category}</TableCell>
                        <TableCell className="max-w-sm text-xs text-slate-600">{item.conflict_reason ?? "—"}</TableCell>
                        <TableCell>{item.ai_confidence != null ? `${item.ai_confidence.toFixed(1)}%` : "—"}</TableCell>
                        <TableCell>
                          <Badge variant="warning">Human Review</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Link to={`/materials/${item.material_id}/analysis`} className="text-xs font-medium text-brand-600 hover:underline">
                            Review
                          </Link>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value?: number | string; accent?: string }) {
  return (
    <div className="rounded border border-slate-200 p-2.5 text-center">
      <p className={`text-xl font-bold ${accent ?? "text-slate-900"}`}>{value ?? "—"}</p>
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
    </div>
  );
}
