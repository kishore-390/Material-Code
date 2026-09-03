import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listHarmonizationRequests } from "@/services/harmonization";

const STATUSES = ["PENDING", "APPROVED", "AUTO_APPROVED", "REJECTED", "MORE_INFO_REQUESTED"];

export default function Harmonization() {
  const [status, setStatus] = React.useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["harmonization", status],
    queryFn: () => listHarmonizationRequests(status || undefined),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Harmonization Requests</h1>
          <p className="text-sm text-slate-500">
            Every AI recommendation and manual request that could lead to a Common Material Code.
          </p>
        </div>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-[200px]">
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
              <TableCell colSpan={6} className="text-center text-slate-400">Loading...</TableCell>
            </TableRow>
          )}
          {!isLoading && (data ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-slate-400">No harmonization requests found.</TableCell>
            </TableRow>
          )}
          {data?.map((h) => (
            <TableRow key={h.id}>
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
    </div>
  );
}
