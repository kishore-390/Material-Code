import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { KpiCard } from "@/components/KpiCard";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCPSE } from "@/services/cpse";
import { listMaterials } from "@/services/materials";
import { Boxes, CheckCircle2, Clock, Layers } from "lucide-react";

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
      <div>
        <h1 className="text-xl font-bold text-slate-900">{cpse.name}</h1>
        <p className="text-sm text-slate-500">{cpse.code} &middot; {cpse.sector}</p>
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
    </div>
  );
}
