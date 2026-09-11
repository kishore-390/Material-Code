import { useQuery } from "@tanstack/react-query";
import { Boxes, CheckCircle2, Clock, Layers } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Breadcrumbs } from "@/components/Breadcrumbs";
import { KpiCard } from "@/components/KpiCard";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCPSE } from "@/services/cpse";
import { listMaterials } from "@/services/materials";

export default function CpseDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: cpse } = useQuery({ queryKey: ["cpse", id], queryFn: () => getCPSE(id!), enabled: !!id });
  const { data: materials } = useQuery({
    queryKey: ["materials", "by-cpse", id],
    queryFn: () => listMaterials({ cpse_id: id, page_size: 20 }),
    enabled: !!id,
  });

  if (!cpse) return <p className="text-sm text-slate-400">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-slate-300 pb-4">
        <div className="space-y-2">
          <Breadcrumbs items={[{ label: "CPSE Network", to: "/cpse" }, { label: cpse.name }]} />
          <h1 className="text-xl font-bold text-slate-900">{cpse.name}</h1>
          <p className="text-sm text-slate-500">
            {cpse.code} &middot; {cpse.sector}{" "}
            <Badge variant={cpse.is_active ? "success" : "outline"} className="ml-1">
              {cpse.is_active ? "Active" : "Inactive"}
            </Badge>
          </p>
        </div>
        <StatusBadge status={cpse.synchronization_status} />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Total Materials" value={cpse.total_materials} icon={Boxes} accent="brand" />
        <KpiCard label="Common Materials" value={cpse.common_materials} icon={CheckCircle2} accent="success" />
        <KpiCard label="Pending Mappings" value={cpse.pending_mappings} icon={Clock} accent="warning" />
        <KpiCard label="Legacy Codes" value={cpse.legacy_codes} icon={Layers} accent="slate" />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Recent Materials</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Material Code</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Classification</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {materials?.items.map((m) => (
              <TableRow key={m.id}>
                <TableCell>
                  <Link to={`/materials/${m.id}`} className="font-medium text-brand-600 hover:underline">
                    {m.original_material_code}
                  </Link>
                </TableCell>
                <TableCell>{m.original_description}</TableCell>
                <TableCell>{m.classification}</TableCell>
                <TableCell>
                  <StatusBadge status={m.status} />
                </TableCell>
              </TableRow>
            ))}
            {(materials?.items.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-slate-400">
                  No materials synchronized yet for this CPSE.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-slate-400">
        See{" "}
        <Link to="/synchronization" className="text-brand-600 hover:underline">
          Data Synchronization
        </Link>{" "}
        for this CPSE's source connection status and sync history.
      </p>
    </div>
  );
}
