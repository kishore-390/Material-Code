import { useQuery } from "@tanstack/react-query";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { listAuditLogs } from "@/services/audit";

export default function AuditLogPage() {
  const [page, setPage] = React.useState(1);
  const pageSize = 30;
  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", page],
    queryFn: () => listAuditLogs(page, pageSize),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Audit Log</h1>
        <p className="text-sm text-slate-500">Complete, immutable history of every AI decision and human action.</p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp</TableHead>
            <TableHead>Actor</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Entity</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-slate-400">Loading...</TableCell>
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
