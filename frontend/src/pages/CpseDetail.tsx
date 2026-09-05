import { useQuery } from "@tanstack/react-query";
import { Boxes, CheckCircle2, Clock, Layers } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Breadcrumbs } from "@/components/Breadcrumbs";
import { KpiCard } from "@/components/KpiCard";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCPSE, listCPSEUploads } from "@/services/cpse";
import { listMaterials } from "@/services/materials";
import type { UploadBatchStatus } from "@/types";

export default function CpseDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: cpse } = useQuery({ queryKey: ["cpse", id], queryFn: () => getCPSE(id!), enabled: !!id });
  const { data: materials } = useQuery({
    queryKey: ["materials", "by-cpse", id],
    queryFn: () => listMaterials({ cpse_id: id, page_size: 20 }),
    enabled: !!id,
  });
  const { data: uploads } = useQuery({
    queryKey: ["cpse", id, "uploads"],
    queryFn: () => listCPSEUploads(id!),
    enabled: !!id,
  });

  if (!cpse) return <p className="text-sm text-slate-400">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-slate-300 pb-4">
        <div className="space-y-2">
          <Breadcrumbs items={[{ label: "Governance", to: "/cpse" }, { label: cpse.name }]} />
          <h1 className="text-xl font-bold text-slate-900">{cpse.name}</h1>
          <p className="text-sm text-slate-500">
            {cpse.code} &middot; {cpse.sector}{" "}
            <Badge variant={cpse.is_active ? "success" : "outline"} className="ml-1">
              {cpse.is_active ? "Active" : "Inactive"}
            </Badge>
          </p>
          {cpse.description && <p className="mt-1 text-sm text-slate-500">{cpse.description}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Total Materials" value={cpse.total_materials} icon={Boxes} accent="brand" />
        <KpiCard label="Harmonized Materials" value={cpse.harmonized_materials} icon={CheckCircle2} accent="success" />
        <KpiCard label="Pending Approvals" value={cpse.pending_approvals} icon={Clock} accent="warning" />
        <KpiCard label="Common Codes" value={cpse.common_codes} icon={Layers} accent="slate" />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Recent Materials</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Material Code</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {materials?.items.map((m) => (
              <TableRow key={m.id}>
                <TableCell>
                  <Link to={`/materials/${m.id}`} className="font-medium text-brand-600 hover:underline">
                    {m.material_code}
                  </Link>
                </TableCell>
                <TableCell>{m.description}</TableCell>
                <TableCell>{m.category}</TableCell>
                <TableCell>
                  <StatusBadge status={m.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Upload History</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Uploaded By</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>Valid</TableHead>
              <TableHead>Invalid</TableHead>
              <TableHead>Duplicate</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Uploaded At</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(uploads?.items.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-slate-400">
                  No uploads yet for this organization.
                </TableCell>
              </TableRow>
            )}
            {uploads?.items.map((u) => (
              <TableRow key={u.id}>
                <TableCell>{u.filename}</TableCell>
                <TableCell>{u.uploader?.full_name ?? "—"}</TableCell>
                <TableCell>{u.total_records}</TableCell>
                <TableCell>{u.valid_records}</TableCell>
                <TableCell>{u.invalid_records}</TableCell>
                <TableCell>{u.duplicate_records}</TableCell>
                <TableCell>
                  <UploadStatusBadge status={u.status} />
                </TableCell>
                <TableCell className="text-xs text-slate-500">{new Date(u.created_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function UploadStatusBadge({ status }: { status: UploadBatchStatus }) {
  const tone: Record<UploadBatchStatus, "outline" | "success" | "danger" | "warning"> = {
    VALIDATING: "outline",
    QUEUED: "warning",
    PROCESSING: "warning",
    COMPLETED: "success",
    PARTIAL: "warning",
    FAILED: "danger",
  };
  return <Badge variant={tone[status]}>{status}</Badge>;
}
