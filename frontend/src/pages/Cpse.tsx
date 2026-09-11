import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiErrorMessage } from "@/services/api";
import { createCPSE, listCPSE, setCPSEStatus, type CPSEFormPayload } from "@/services/cpse";

const SECTORS = ["Oil & Gas", "Power", "Steel", "Mining", "Heavy Engineering", "Other"];

export default function Cpse() {
  const { user } = useAuth();
  const isAdmin = user?.role.name === "ADMIN";
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["cpse"], queryFn: listCPSE });

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["cpse"] });

  const statusMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => setCPSEStatus(id, is_active),
    onSuccess: invalidate,
  });

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "CPSE Network", to: "/cpse" }, { label: "Participating CPSEs" }]}
        title="Participating CPSEs"
        subtitle="Every Central Public Sector Enterprise onboarded to the National Material Master. Materials only arrive via automatic synchronization - see Data Synchronization."
        actions={
          isAdmin ? (
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" /> Add CPSE
            </Button>
          ) : undefined
        }
      />

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>CPSE</TableHead>
            <TableHead>Total Materials</TableHead>
            <TableHead>Common Materials</TableHead>
            <TableHead>Pending Mappings</TableHead>
            <TableHead>Sync Status</TableHead>
            <TableHead>Status</TableHead>
            {isAdmin && <TableHead>Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={isAdmin ? 7 : 6} className="text-center text-slate-400">
                Loading...
              </TableCell>
            </TableRow>
          )}
          {!isLoading && (data ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={isAdmin ? 7 : 6} className="text-center text-slate-400">
                No CPSEs onboarded yet.
              </TableCell>
            </TableRow>
          )}
          {data?.map((cpse) => (
            <TableRow key={cpse.id}>
              <TableCell>
                <Link to={`/cpse/${cpse.id}`} className="font-semibold text-brand-600 hover:underline">
                  {cpse.code}
                </Link>
                <p className="text-xs text-slate-500">{cpse.name}</p>
              </TableCell>
              <TableCell>{cpse.total_materials}</TableCell>
              <TableCell>{cpse.common_materials}</TableCell>
              <TableCell>{cpse.pending_mappings}</TableCell>
              <TableCell>
                <StatusBadge status={cpse.synchronization_status} />
              </TableCell>
              <TableCell>
                <Badge variant={cpse.is_active ? "success" : "outline"}>{cpse.is_active ? "Active" : "Inactive"}</Badge>
              </TableCell>
              {isAdmin && (
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate({ id: cpse.id, is_active: !cpse.is_active })}
                  >
                    {cpse.is_active ? "Deactivate" : "Activate"}
                  </Button>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <CPSEDialog open={dialogOpen} onOpenChange={setDialogOpen} onSaved={invalidate} />
    </div>
  );
}

function CPSEDialog({ open, onOpenChange, onSaved }: { open: boolean; onOpenChange: (open: boolean) => void; onSaved: () => void }) {
  const [form, setForm] = React.useState<CPSEFormPayload>({});

  React.useEffect(() => {
    if (open) setForm({});
  }, [open]);

  const mutation = useMutation({
    mutationFn: () => createCPSE(form),
    onSuccess: () => {
      onSaved();
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add CPSE</DialogTitle>
        </DialogHeader>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>CPSE Code *</Label>
              <Input
                required
                value={form.code ?? ""}
                onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                placeholder="e.g. GAIL"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Sector</Label>
              <select
                value={form.sector ?? ""}
                onChange={(e) => setForm({ ...form, sector: e.target.value })}
                className="h-9 w-full rounded border border-slate-300 px-2 text-sm"
              >
                <option value="">Select sector</option>
                {SECTORS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>CPSE Name *</Label>
            <Input required value={form.name ?? ""} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. GAIL (India) Limited" />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>

          {mutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(mutation.error)}</p>}

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Create CPSE"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
