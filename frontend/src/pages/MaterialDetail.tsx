import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Breadcrumbs } from "@/components/Breadcrumbs";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { triggerAnalysis } from "@/services/ai";
import { findSimilarMaterials, getMaterial } from "@/services/materials";

export default function MaterialDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: material, isLoading } = useQuery({
    queryKey: ["material", id],
    queryFn: () => getMaterial(id!),
    enabled: !!id,
  });

  const { data: similar } = useQuery({
    queryKey: ["material", id, "similar"],
    queryFn: () => findSimilarMaterials(id!),
    enabled: !!id,
  });

  const analyzeMutation = useMutation({
    mutationFn: () => triggerAnalysis(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["material", id] });
      navigate(`/materials/${id}/analysis`);
    },
  });

  if (isLoading || !material) {
    return <p className="text-sm text-slate-400">Loading material...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between border-b border-slate-300 pb-4">
        <div className="space-y-2">
          <Breadcrumbs items={[{ label: "Material Master", to: "/materials" }, { label: material.original_material_code }]} />
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">{material.original_material_code}</h1>
            <StatusBadge status={material.status} />
          </div>
          <p className="text-sm text-slate-500">{material.original_description}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => analyzeMutation.mutate()} disabled={analyzeMutation.isPending}>
            <Sparkles className="h-4 w-4" />
            {analyzeMutation.isPending ? "Queuing..." : "Re-run AI Analysis"}
          </Button>
          <Button asChild>
            <Link to={`/materials/${id}/analysis`}>View AI Analysis</Link>
          </Button>
        </div>
      </div>

      {material.active_common_material && (
        <Card className="border-success-600/30 bg-success-50/40">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-success-700">Common Material Status</p>
              <p className="mt-1 text-lg font-bold text-success-700">{material.active_common_material.common_code}</p>
              <p className="text-sm text-slate-600">{material.active_common_material.standardized_description}</p>
            </div>
            <Button asChild variant="outline">
              <Link to={`/common-material-master/${material.active_common_material.common_code}`}>View Common Material</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Original CPSE Data</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 text-sm">
            <Field label="Technical Specification" value={material.technical_specification} span />
            <Field label="Classification" value={material.classification} />
            <Field label="Material Type" value={material.material_type} />
            <Field label="Grade" value={material.material_grade} />
            <Field label="Dimensions" value={material.dimensions} />
            <Field label="Standard" value={material.standard} />
            <Field label="UOM" value={material.uom} />
            <Field label="CPSE" value={`${material.cpse.name} (${material.cpse.code})`} />
            <Field label="Manufacturer" value={material.manufacturer} />
            <Field label="Function" value={material.function} />
            <Field label="Packaging" value={material.packaging} />
            <Field label="Criticality" value={material.criticality} />
            {material.last_synced_at && (
              <Field label="Last Synchronized" value={new Date(material.last_synced_at).toLocaleString()} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>AI Harmonization</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {material.active_common_material ? (
              <>
                <p className="text-xs uppercase tracking-wide text-slate-400">Common Code</p>
                <Link to={`/common-material-master/${material.active_common_material.common_code}`} className="text-lg font-bold text-brand-600 hover:underline">
                  {material.active_common_material.common_code}
                </Link>
                <StatusBadge status={material.active_common_material.status} />
              </>
            ) : (
              <p className="text-slate-400">Not yet mapped to a common material.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {material.attributes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Additional Attributes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {material.attributes.map((attr) => (
                <Badge key={attr.id} variant="outline">
                  {attr.attr_key}: {attr.attr_value}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Similar Materials (pgvector search)</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Material</TableHead>
                <TableHead>CPSE</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(similar ?? []).map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    <Link to={`/materials/${item.id}`} className="text-brand-600 hover:underline">
                      {item.original_material_code}
                    </Link>
                    <p className="text-xs text-slate-400">{item.original_description}</p>
                  </TableCell>
                  <TableCell>{item.cpse.code}</TableCell>
                  <TableCell>
                    <StatusBadge status={item.status} />
                  </TableCell>
                </TableRow>
              ))}
              {(similar ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-slate-400">
                    No similar materials found yet. Run AI analysis first.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  value,
  span,
}: {
  label: string;
  value?: string | ReactNode | null;
  span?: boolean;
}) {
  return (
    <div className={span ? "col-span-2" : undefined}>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-medium text-slate-800">{value || "Missing attribute"}</p>
    </div>
  );
}
