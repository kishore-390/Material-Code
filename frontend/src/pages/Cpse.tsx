import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/services/api";
import { createCPSE, listCPSE, setCPSEStatus, updateCPSE, type CPSEFormPayload } from "@/services/cpse";
import type { CPSEStats } from "@/types";

export default function Cpse() {
  const { user } = useAuth();
  const isAdmin = user?.role.name === "ADMIN";
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["cpse"], queryFn: listCPSE });

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<CPSEStats | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["cpse"] });

  const statusMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => setCPSEStatus(id, is_active),
    onSuccess: invalidate,
  });

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Governance", to: "/cpse" }, { label: "Organizations" }]}
        title="Organizations"
        subtitle="Every CPSE onboarded to the platform. Add one and it's usable everywhere immediately."
        actions={
          isAdmin ? (
            <Button
              onClick={() => {
                setEditing(null);
                setDialogOpen(true);
              }}
            >
              <Plus className="h-4 w-4" /> Add Organization
            </Button>
          ) : undefined
        }
      />

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Organization</TableHead>
            <TableHead>Material Records</TableHead>
            <TableHead>Harmonized Records</TableHead>
            <TableHead>Pending Reviews</TableHead>
            <TableHead>Status</TableHead>
            {isAdmin && <TableHead>Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={isAdmin ? 6 : 5} className="text-center text-slate-400">
                Loading...
              </TableCell>
            </TableRow>
          )}
          {!isLoading && (data ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={isAdmin ? 6 : 5} className="text-center text-slate-400">
                No organizations onboarded yet.
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
              <TableCell>{cpse.harmonized_materials} ({cpse.harmonization_percentage}%)</TableCell>
              <TableCell>{cpse.pending_approvals}</TableCell>
              <TableCell>
                <Badge variant={cpse.is_active ? "success" : "outline"}>{cpse.is_active ? "Active" : "Inactive"}</Badge>
              </TableCell>
              {isAdmin && (
                <TableCell>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditing(cpse);
                        setDialogOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={statusMutation.isPending}
                      onClick={() => statusMutation.mutate({ id: cpse.id, is_active: !cpse.is_active })}
                    >
                      {cpse.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  </div>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <OrganizationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        editing={editing}
        onSaved={invalidate}
      />
    </div>
  );
}

function OrganizationDialog({
  open,
  onOpenChange,
  editing,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editing: CPSEStats | null;
  onSaved: () => void;
}) {
  const [form, setForm] = React.useState<CPSEFormPayload>({});
  const [logo, setLogo] = React.useState<File | null>(null);

  React.useEffect(() => {
    if (open) {
      setForm(
        editing
          ? { code: editing.code, name: editing.name, sector: editing.sector ?? "", description: editing.description ?? "" }
          : {}
      );
      setLogo(null);
    }
  }, [open, editing]);

  const mutation = useMutation({
    mutationFn: () => {
      const payload = { ...form, logo };
      return editing ? updateCPSE(editing.id, payload) : createCPSE(payload);
    },
    onSuccess: () => {
      onSaved();
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? `Edit ${editing.code}` : "Add Organization"}</DialogTitle>
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
              <Label>Organization Code *</Label>
              <Input
                required
                disabled={!!editing}
                value={form.code ?? ""}
                onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                placeholder="e.g. GAIL"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Sector</Label>
              <Input
                value={form.sector ?? ""}
                onChange={(e) => setForm({ ...form, sector: e.target.value })}
                placeholder="e.g. Oil & Gas"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Organization Name *</Label>
            <Input
              required
              value={form.name ?? ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. GAIL (India) Limited"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Logo (optional)</Label>
            <Input type="file" accept="image/*" onChange={(e) => setLogo(e.target.files?.[0] ?? null)} />
          </div>

          {mutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(mutation.error)}</p>}

          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : editing ? "Save Changes" : "Create Organization"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
