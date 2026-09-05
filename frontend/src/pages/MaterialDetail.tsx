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
import { resolveImageUrl } from "@/services/api";
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
          <Breadcrumbs items={[{ label: "Material Management", to: "/materials" }, { label: material.material_code }]} />
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900">{material.material_code}</h1>
            <StatusBadge status={material.status} />
          </div>
          <p className="text-sm text-slate-500">{material.description}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => analyzeMutation.mutate()} disabled={analyzeMutation.isPending}>
            <Sparkles className="h-4 w-4" />
            {analyzeMutation.isPending ? "Queuing..." : "Run AI Analysis"}
          </Button>
          <Button asChild>
            <Link to={`/materials/${id}/analysis`}>View AI Analysis</Link>
          </Button>
        </div>
      </div>

      {material.common_code && (
        <Card className="border-success-600/30 bg-success-50/40">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-success-700">AI Status: Harmonized</p>
              <p className="mt-1 text-lg font-bold text-success-700">{material.common_code.code}</p>
              <p className="text-sm text-slate-600">{material.common_code.standard_description}</p>
            </div>
            <Button asChild variant="outline">
              <Link to={`/common-material-master/${material.common_code.code}`}>View Common Material</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Material Details</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 text-sm">
            <Field label="Specification" value={material.specification} span />
            <Field label="Normalized Specification" value={material.normalized_specification} span muted />
            <Field label="Category" value={material.category} />
            <Field label="Normalized Category" value={material.normalized_category} muted />
            <Field label="UOM" value={material.uom} />
            <Field label="Normalized UOM" value={material.normalized_uom} muted />
            <Field label="CPSE" value={`${material.cpse.name} (${material.cpse.code})`} />
            <Field label="Manufacturer" value={material.manufacturer} />
            <Field label="Brand" value={material.brand} />
            <Field label="Material Type" value={material.material_type} />
            {material.source_database && (
              <>
                <Field label="Source Database" value={material.source_database} />
                <Field
                  label="Last Synchronized"
                  value={material.last_synced_at ? new Date(material.last_synced_at).toLocaleString() : undefined}
                />
              </>
            )}
            <Field
              label="Common Material Code"
              value={
                material.common_code ? (
                  <Link to={`/common-material-master/${material.common_code.code}`} className="text-brand-600 hover:underline">
                    {material.common_code.code}
                  </Link>
                ) : (
                  "Not harmonized yet"
                )
              }
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Image</CardTitle>
          </CardHeader>
          <CardContent>
            {material.image_url ? (
              <img
                src={resolveImageUrl(material.image_url)}
                alt={material.description}
                className="aspect-square w-full rounded-lg border border-slate-100 object-cover"
              />
            ) : (
              <div className="flex aspect-square w-full items-center justify-center rounded-lg border border-dashed border-slate-200 text-xs text-slate-400">
                No image uploaded
              </div>
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
                <TableHead>Similarity</TableHead>
                <TableHead>Common Code</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(similar ?? []).map((item) => (
                <TableRow key={item.material.id}>
                  <TableCell>
                    <Link to={`/materials/${item.material.id}`} className="text-brand-600 hover:underline">
                      {item.material.material_code}
                    </Link>
                    <p className="text-xs text-slate-400">{item.material.description}</p>
                  </TableCell>
                  <TableCell>{item.material.cpse.code}</TableCell>
                  <TableCell className="font-semibold">{item.similarity.toFixed(1)}%</TableCell>
                  <TableCell>{item.material.common_code?.code ?? "—"}</TableCell>
                  <TableCell>
                    <StatusBadge status={item.material.status} />
                  </TableCell>
                </TableRow>
              ))}
              {(similar ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-slate-400">
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
  muted,
}: {
  label: string;
  value?: string | ReactNode | null;
  span?: boolean;
  muted?: boolean;
}) {
  return (
    <div className={span ? "col-span-2" : undefined}>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className={muted ? "text-slate-400" : "font-medium text-slate-800"}>{value || "—"}</p>
    </div>
  );
}
