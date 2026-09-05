import { useQuery } from "@tanstack/react-query";
import * as React from "react";

import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listAuditLogs } from "@/services/audit";

const ENTITY_TYPES = ["material", "harmonization_request", "approval_request", "common_material_code"];

export default function AuditLogPage() {
  const [page, setPage] = React.useState(1);
  const [entityType, setEntityType] = React.useState("");
  const [action, setAction] = React.useState("");
  const pageSize = 30;
  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", page, entityType, action],
    queryFn: () => listAuditLogs({ page, pageSize, entityType: entityType || undefined, action: action || undefined }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Reports & Monitoring", to: "/audit-log" }, { label: "Audit Log" }]}
        title="Audit Log"
        subtitle="Complete, immutable register of every AI decision and human action."
        actions={
          <>
            <Select
              value={entityType}
              onChange={(e) => {
                setEntityType(e.target.value);
                setPage(1);
              }}
              className="max-w-[200px]"
            >
              <option value="">All Entities</option>
              {ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
            <Input
              placeholder="Filter by action (e.g. MATERIAL_UPLOADED)"
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setPage(1);
              }}
              className="max-w-[240px]"
            />
          </>
        }
      />

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date &amp; Time</TableHead>
            <TableHead>User</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Entity</TableHead>
            <TableHead>Material Code</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-slate-400">Loading...</TableCell>
            </TableRow>
          )}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-slate-400">No audit records match the current filters.</TableCell>
            </TableRow>
          )}
          {data?.items.map((log) => (
            <TableRow key={log.id}>
              <TableCell className="whitespace-nowrap text-xs text-slate-500">
                {new Date(log.created_at).toLocaleString()}
              </TableCell>
              <TableCell>
                <Badge variant={log.actor_type === "AI_ENGINE" ? "brand" : "outline"}>{log.actor_name}</Badge>
              </TableCell>
              <TableCell className="font-medium">{log.action.replace(/_/g, " ")}</TableCell>
              <TableCell className="text-xs text-slate-500">{log.entity_type}</TableCell>
              <TableCell className="text-xs text-slate-500">
                {(log.details as Record<string, unknown> | null)?.material_code as string | undefined ?? "—"}
              </TableCell>
              <TableCell className="max-w-sm truncate text-xs text-slate-500">
                {log.details ? JSON.stringify(log.details) : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>Page {page} of {totalPages}</span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
