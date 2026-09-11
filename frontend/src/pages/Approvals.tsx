import { useQuery } from "@tanstack/react-query";
import { Link, useLocation } from "react-router-dom";

import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listApprovedMappings, listPendingApprovals, listRejectedMappings } from "@/services/approvals";

type ApprovalView = "pending" | "approved" | "rejected";

const VIEW_META: Record<ApprovalView, { title: string; subtitle: string }> = {
  pending: {
    title: "Pending Validation",
    subtitle: "AI recommendations and manual mappings awaiting Material Expert review.",
  },
  approved: {
    title: "Approved",
    subtitle: "Mappings confirmed as official Common Material Master entries.",
  },
  rejected: {
    title: "Rejected",
    subtitle: "Mappings a Material Expert determined were not the same material.",
  },
};

function viewFromPath(pathname: string): ApprovalView {
  const segment = pathname.split("/").pop() as ApprovalView;
  return VIEW_META[segment] ? segment : "pending";
}

export default function Approvals() {
  const location = useLocation();
  const view = viewFromPath(location.pathname);
  const meta = VIEW_META[view];

  const queryFn = view === "pending" ? listPendingApprovals : view === "approved" ? listApprovedMappings : listRejectedMappings;
  const { data, isLoading } = useQuery({ queryKey: ["approvals", view], queryFn });

  return (
    <div className="space-y-4">
      <PageHeader breadcrumbs={[{ label: "Approvals" }, { label: meta.title }]} title={meta.title} subtitle={meta.subtitle} />

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>CPSE</TableHead>
            <TableHead>Material Code</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Matched Against</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Mapping Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-slate-400">
                Loading...
              </TableCell>
            </TableRow>
          )}
          {!isLoading && (data ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-slate-400">
                Nothing here right now.
              </TableCell>
            </TableRow>
          )}
          {data?.map((mapping) => (
            <TableRow key={mapping.id}>
              <TableCell>{mapping.cpse_material.cpse.code}</TableCell>
              <TableCell>
                <Link to={`/approvals/${mapping.id}`} className="font-medium text-brand-600 hover:underline">
                  {mapping.cpse_material.original_material_code}
                </Link>
              </TableCell>
              <TableCell className="max-w-[200px] truncate">{mapping.cpse_material.original_description}</TableCell>
              <TableCell>{mapping.matched_against?.original_material_code ?? "—"}</TableCell>
              <TableCell>{mapping.confidence_score ? `${mapping.confidence_score.toFixed(1)}%` : "Manual"}</TableCell>
              <TableCell>
                <StatusBadge status={mapping.mapping_type} />
              </TableCell>
              <TableCell>
                <StatusBadge status={mapping.decision_status} />
              </TableCell>
              <TableCell className="text-right">
                <Link to={`/approvals/${mapping.id}`} className="text-xs font-medium text-brand-600 hover:underline">
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
