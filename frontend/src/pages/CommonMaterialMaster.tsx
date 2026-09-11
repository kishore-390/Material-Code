import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, ScanLine } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listCommonMaterials } from "@/services/commonCodes";
import { getScanStatus, scanMaterialMasters } from "@/services/harmonization";

function formatDate(iso: string) {
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

export default function CommonMaterialMaster() {
  const queryClient = useQueryClient();
  const [cpseId, setCpseId] = React.useState("");
  const [scanMaterialIds, setScanMaterialIds] = React.useState<string[] | null>(null);

  const { data: materials, isLoading, isFetching } = useQuery({
    queryKey: ["common-materials", cpseId],
    queryFn: () => listCommonMaterials(cpseId || undefined),
  });

  const scanMutation = useMutation({
    mutationFn: () => scanMaterialMasters(),
    onSuccess: (result) => setScanMaterialIds(result.material_ids),
  });

  const { data: scanStatus } = useQuery({
    queryKey: ["common-material-master", "scan-status", scanMaterialIds],
    queryFn: () => getScanStatus(scanMaterialIds as string[]),
    enabled: !!scanMaterialIds && scanMaterialIds.length > 0,
    refetchInterval: (query) => (query.state.data && query.state.data.completed >= query.state.data.total ? false : 1500),
  });
  const scanDone = !!scanStatus && scanStatus.completed >= scanStatus.total;

  function handleRefresh() {
    queryClient.invalidateQueries({ queryKey: ["common-materials"] });
  }

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Material Master", to: "/common-material-master" }, { label: "Common Materials" }]}
        title="Common Material Master"
        subtitle="The standardized national record for every harmonized material group. Original CPSE codes remain fully traceable via each linked material."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link to="/harmonization/duplicates">View AI-Detected Duplicates</Link>
            </Button>
            <Button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
              <ScanLine className="h-4 w-4" />
              {scanMutation.isPending ? "Starting Scan..." : "Scan Unmapped Materials"}
            </Button>
          </>
        }
      />

      {scanMaterialIds && scanMaterialIds.length > 0 && (
        <Card>
          <CardContent className="flex flex-wrap items-center gap-6 py-4 text-sm">
            <span>
              <span className="font-bold text-slate-900">{scanStatus?.completed ?? 0}</span> /{" "}
              <span className="text-slate-500">{scanStatus?.total ?? scanMaterialIds.length}</span> materials analyzed
            </span>
            <span className={scanDone ? "font-medium text-success-600" : "font-medium text-brand-600"}>
              {scanDone ? "Scan complete" : "Processing..."}
            </span>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <OrganizationSelect includeAllOption value={cpseId} onChange={(e) => setCpseId(e.target.value)} className="h-9 max-w-[220px]" />
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isFetching}>
          <RefreshCw className={"h-4 w-4" + (isFetching ? " animate-spin" : "")} />
          Refresh
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Common Code</TableHead>
            <TableHead>Standardized Description</TableHead>
            <TableHead>Classification</TableHead>
            <TableHead>UOM</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-slate-400">
                Loading...
              </TableCell>
            </TableRow>
          )}
          {!isLoading && (materials?.length ?? 0) === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-slate-400">
                No common materials generated yet.
              </TableCell>
            </TableRow>
          )}
          {materials?.map((code) => (
            <TableRow key={code.id}>
              <TableCell>
                <Link to={`/common-material-master/${code.common_code}`} className="font-semibold text-brand-600 hover:underline">
                  {code.common_code}
                </Link>
              </TableCell>
              <TableCell className="max-w-xs truncate">{code.standardized_description}</TableCell>
              <TableCell>{code.classification}</TableCell>
              <TableCell>{code.standardized_uom}</TableCell>
              <TableCell>{code.confidence != null ? `${code.confidence.toFixed(1)}%` : "—"}</TableCell>
              <TableCell>
                <StatusBadge status={code.status} />
              </TableCell>
              <TableCell className="text-xs text-slate-500">{formatDate(code.created_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
