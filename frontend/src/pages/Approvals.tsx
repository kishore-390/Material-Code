import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listApprovals } from "@/services/approvals";

const STATUSES = ["PENDING", "APPROVED", "REJECTED", "MORE_INFO_REQUESTED", "MERGED", "NOT_SAME_MATERIAL"];

export default function Approvals() {
  const [status, setStatus] = React.useState("PENDING");
  const { data, isLoading } = useQuery({
    queryKey: ["approvals", status],
    queryFn: () => listApprovals(status || undefined),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Approval Center</h1>
          <p className="text-sm text-slate-500">
            Human-in-the-loop review for AI recommendations between 85% and 95% confidence, and manual requests.
          </p>
        </div>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-[220px]">
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </Select>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Material</TableHead>
            <TableHead>CPSE</TableHead>
            <TableHead>Candidate</TableHead>
            <TableHead>AI Score</TableHead>
            <TableHead>Reason</TableHead>
            <TableHead>Submitted At</TableHead>
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
              <TableCell colSpan={7} className="text-center text-slate-400">No approval requests found.</TableCell>
            </TableRow>
          )}
          {data?.map((approval) => (
            <TableRow key={approval.id}>
              <TableCell>
                <Link to={`/approvals/${approval.id}`} className="font-medium text-brand-600 hover:underline">
                  {approval.material.material_code}
                </Link>
              </TableCell>
              <TableCell>{approval.material.cpse.code}</TableCell>
              <TableCell>{approval.candidate?.material_code ?? "—"}</TableCell>
              <TableCell>{approval.ai_score ? `${approval.ai_score.toFixed(1)}%` : "Manual"}</TableCell>
              <TableCell className="max-w-xs truncate text-xs text-slate-500">{approval.reason}</TableCell>
              <TableCell className="text-xs text-slate-500">{new Date(approval.created_at).toLocaleString()}</TableCell>
              <TableCell>
                <StatusBadge status={approval.status} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
