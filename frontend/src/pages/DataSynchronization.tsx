import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plug, RefreshCw } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/PageHeader";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  fullSync,
  getSyncHistory,
  listSourceConnections,
  syncNow,
  testSourceConnection,
} from "@/services/synchronization";
import type { SourceConnection, TestConnectionResult } from "@/types";

function timeAgo(iso?: string | null): string {
  if (!iso) return "Never";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/** Derives the single state label the UI shows - never fabricated, always
 * read from the connection's own last_sync_status/enabled. */
function deriveState(connection: SourceConnection): { label: string; variant: NonNullable<BadgeProps["variant"]> } {
  if (!connection.enabled) return { label: "DISABLED", variant: "outline" };
  if (connection.last_sync_status === "RUNNING") return { label: "SYNCING", variant: "brand" };
  if (connection.last_sync_status === "FAILED") return { label: "FAILED", variant: "danger" };
  if (connection.last_sync_status === "SUCCESS" || connection.last_sync_status === "PARTIAL") {
    return { label: "UP TO DATE", variant: "success" };
  }
  return { label: "NEVER SYNCED", variant: "outline" };
}

export default function DataSynchronization() {
  const queryClient = useQueryClient();
  const [historyFor, setHistoryFor] = React.useState<SourceConnection | null>(null);

  const { data: connections, isLoading } = useQuery({
    queryKey: ["source-connections"],
    queryFn: listSourceConnections,
    refetchInterval: 10000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["source-connections"] });

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "CPSE Network" }, { label: "Data Synchronization" }]}
        title="Data Synchronization"
        subtitle="Secure, read-only database connectors pull each CPSE's material master automatically into the national pipeline. Credentials live only as backend environment variables and are never shown here."
      />

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>CPSE</TableHead>
            <TableHead>Database Type</TableHead>
            <TableHead>Source Table</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last Sync</TableHead>
            <TableHead>Last Successful Sync</TableHead>
            <TableHead className="text-right">Actions</TableHead>
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
          {!isLoading && (connections ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-slate-400">
                No source connections configured yet.
              </TableCell>
            </TableRow>
          )}
          {connections?.map((connection) => (
            <ConnectionRow key={connection.id} connection={connection} onChanged={invalidate} onViewHistory={() => setHistoryFor(connection)} />
          ))}
        </TableBody>
      </Table>

      <SyncHistoryDialog connection={historyFor} onOpenChange={(open) => !open && setHistoryFor(null)} />
    </div>
  );
}

function ConnectionRow({
  connection,
  onChanged,
  onViewHistory,
}: {
  connection: SourceConnection;
  onChanged: () => void;
  onViewHistory: () => void;
}) {
  const [testResult, setTestResult] = React.useState<TestConnectionResult | null>(null);

  const testMutation = useMutation({ mutationFn: () => testSourceConnection(connection.id), onSuccess: setTestResult });
  const syncMutation = useMutation({ mutationFn: () => syncNow(connection.id), onSuccess: onChanged });
  const fullSyncMutation = useMutation({ mutationFn: () => fullSync(connection.id), onSuccess: onChanged });

  const state = deriveState(connection);

  return (
    <TableRow>
      <TableCell>
        <p className="font-semibold text-slate-800">{connection.cpse.code}</p>
        <p className="text-xs text-slate-400">{connection.connection_name}</p>
        {connection.is_demo && <Badge variant="warning">DEMO</Badge>}
      </TableCell>
      <TableCell>{connection.database_type}</TableCell>
      <TableCell className="font-mono text-xs text-slate-500">{connection.table_name}</TableCell>
      <TableCell>
        <Badge variant={state.variant}>{state.label}</Badge>
        {testResult && (
          <p className={`mt-1 text-[11px] ${testResult.connected ? "text-success-600" : "text-danger-600"}`}>
            {testResult.connected ? `Connected · ${testResult.latency_ms}ms` : testResult.error}
          </p>
        )}
      </TableCell>
      <TableCell className="text-xs">
        {timeAgo(connection.last_sync_started_at)}
        {connection.last_error && <p className="text-danger-600">{connection.last_error}</p>}
      </TableCell>
      <TableCell className="text-xs">{timeAgo(connection.last_successful_sync)}</TableCell>
      <TableCell className="text-right">
        <div className="flex flex-wrap justify-end gap-1.5">
          <Button variant="outline" size="sm" onClick={() => testMutation.mutate()} disabled={testMutation.isPending}>
            <Plug className="h-3.5 w-3.5" /> Test
          </Button>
          <Button variant="outline" size="sm" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
            <RefreshCw className="h-3.5 w-3.5" /> {syncMutation.isPending ? "Syncing..." : "Sync Now"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => fullSyncMutation.mutate()} disabled={fullSyncMutation.isPending}>
            {fullSyncMutation.isPending ? "Syncing..." : "Full Sync"}
          </Button>
          <Button variant="outline" size="sm" onClick={onViewHistory}>
            History
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

function SyncHistoryDialog({ connection, onOpenChange }: { connection: SourceConnection | null; onOpenChange: (open: boolean) => void }) {
  const { data } = useQuery({
    queryKey: ["source-connection-history", connection?.id],
    queryFn: () => getSyncHistory(connection!.id),
    enabled: !!connection,
  });

  return (
    <Dialog open={!!connection} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Sync History &middot; {connection?.cpse.code}</DialogTitle>
        </DialogHeader>
        <Card className="max-h-[60vh] overflow-y-auto">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Discovered</TableHead>
                  <TableHead>Inserted</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Skipped</TableHead>
                  <TableHead>Failed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((batch) => (
                  <TableRow key={batch.id}>
                    <TableCell>{batch.sync_type}</TableCell>
                    <TableCell className="text-xs">{new Date(batch.started_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant={batch.status === "SUCCESS" ? "success" : batch.status === "FAILED" ? "danger" : "warning"}>{batch.status}</Badge>
                    </TableCell>
                    <TableCell className="tabular-nums">{batch.records_discovered}</TableCell>
                    <TableCell className="tabular-nums text-success-600">{batch.records_inserted}</TableCell>
                    <TableCell className="tabular-nums text-brand-600">{batch.records_updated}</TableCell>
                    <TableCell className="tabular-nums text-slate-400">{batch.records_skipped}</TableCell>
                    <TableCell className="tabular-nums text-danger-600">{batch.records_failed}</TableCell>
                  </TableRow>
                ))}
                {(data?.items.length ?? 0) === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-slate-400">
                      No sync runs yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </DialogContent>
    </Dialog>
  );
}
