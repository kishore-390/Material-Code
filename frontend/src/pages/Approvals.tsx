import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link } from "react-router-dom";

import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listApprovals } from "@/services/approvals";

const STATUSES = ["PENDING", "APPROVED", "REJECTED", "MORE_INFO_REQUESTED", "MERGED", "NOT_SAME_MATERIAL"];

export default function Approvals() {
  const [status, setStatus] = React.useState("PENDING");
  const [cpseId, setCpseId] = React.useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["approvals", status, cpseId],
    queryFn: () => listApprovals(status || undefined, cpseId || undefined),
  });

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Governance", to: "/approvals" }, { label: "Approval Center" }]}
        title="Approval Center"
        subtitle="Human-in-the-loop review for AI recommendations between 85% and 95% confidence, and manual requests."
        actions={
          <>
            <OrganizationSelect includeAllOption value={cpseId} onChange={(e) => setCpseId(e.target.value)} className="max-w-[200px]" />
            <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-[220px]">
              <option value="">All Statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </>
        }
      />

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">Sl.No.</TableHead>
            <TableHead>Request ID</TableHead>
            <TableHead>CPSE</TableHead>
            <TableHead>Material Code</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>AI Confidence</TableHead>
            <TableHead>Recommendation / Reason</TableHead>
            <TableHead>Submitted Date</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={10} className="text-center text-slate-400">Loading...</TableCell>
            </TableRow>
          )}
          {!isLoading && (data ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={10} className="text-center text-slate-400">No approval requests found.</TableCell>
            </TableRow>
          )}
          {data?.map((approval, idx) => (
            <TableRow key={approval.id}>
              <TableCell className="text-slate-400">{idx + 1}</TableCell>
              <TableCell className="font-mono text-xs text-slate-500">{approval.id.slice(0, 8)}</TableCell>
              <TableCell>{approval.material.cpse.code}</TableCell>
              <TableCell>
                <Link to={`/approvals/${approval.id}`} className="font-medium text-brand-600 hover:underline">
                  {approval.material.material_code}
                </Link>
              </TableCell>
              <TableCell className="max-w-[200px] truncate">{approval.material.description}</TableCell>
              <TableCell>{approval.ai_score ? `${approval.ai_score.toFixed(1)}%` : "Manual"}</TableCell>
              <TableCell className="max-w-xs truncate text-xs text-slate-500">{approval.reason}</TableCell>
              <TableCell className="text-xs text-slate-500">{new Date(approval.created_at).toLocaleString()}</TableCell>
              <TableCell>
                <StatusBadge status={approval.status} />
              </TableCell>
              <TableCell className="text-right">
                <Link to={`/approvals/${approval.id}`} className="text-xs font-medium text-brand-600 hover:underline">
                  Review
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
