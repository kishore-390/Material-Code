import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCommonCode } from "@/services/commonCodes";

export default function CommonMaterialCodeDetailPage() {
  const { code } = useParams<{ code: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["common-code", code],
    queryFn: () => getCommonCode(code!),
    enabled: !!code,
  });

  if (isLoading || !data) return <p className="text-sm text-slate-400">Loading...</p>;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-brand-600">{data.code}</h1>
          <p className="text-sm text-slate-600">{data.standard_description}</p>
        </div>
        <StatusBadge status={data.status} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Standard Definition</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Category</p>
            <p className="font-medium">{data.category}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Material Type</p>
            <p className="font-medium">{data.material_type}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">UOM</p>
            <p className="font-medium">{data.uom}</p>
          </div>
          <div className="col-span-2 md:col-span-3">
            <p className="text-xs uppercase tracking-wide text-slate-400">Specification</p>
            <p className="font-medium">{data.standard_specification || "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Linked CPSEs</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {data.linked_cpses.map((c) => (
                <Badge key={c} variant="brand">
                  {c}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Original Material Codes ({data.linked_materials.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material Code</TableHead>
                <TableHead>CPSE</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.linked_materials.map((m) => (
                <TableRow key={m.id}>
                  <TableCell>
                    <Link to={`/materials/${m.id}`} className="font-medium text-brand-600 hover:underline">
                      {m.material_code}
                    </Link>
                  </TableCell>
                  <TableCell>{m.cpse.code}</TableCell>
                  <TableCell>{m.description}</TableCell>
                  <TableCell>
                    <StatusBadge status={m.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
