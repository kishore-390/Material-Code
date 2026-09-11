import { useQuery } from "@tanstack/react-query";
import { Cpu } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Breadcrumbs } from "@/components/Breadcrumbs";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getCommonMaterial } from "@/services/commonCodes";

export default function CommonMaterialCodeDetailPage() {
  const { code } = useParams<{ code: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["common-material", code],
    queryFn: () => getCommonMaterial(code!),
    enabled: !!code,
  });

  if (isLoading || !data) return <p className="text-sm text-slate-400">Loading...</p>;

  const materialsByCpse = data.mapped_materials.reduce<Record<string, typeof data.mapped_materials>>((acc, m) => {
    (acc[m.cpse.code] ??= []).push(m);
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="space-y-2 border-b border-slate-300 pb-4">
        <Breadcrumbs items={[{ label: "Material Master", to: "/common-material-master" }, { label: data.common_code }]} />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Common National Material Code</p>
            <h1 className="text-2xl font-bold text-brand-600">{data.common_code}</h1>
          </div>
          <StatusBadge status={data.status} />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Standardized Definition</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <div className="col-span-2 md:col-span-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Standardized Description</p>
            <p className="font-medium">{data.standardized_description}</p>
          </div>
          <Field label="Classification" value={data.classification} />
          <Field label="Material Type" value={data.material_type} />
          <Field label="Grade" value={data.material_grade} />
          <Field label="Dimensions" value={data.dimensions} />
          <Field label="Standard" value={data.standard} />
          <Field label="UOM" value={data.standardized_uom} />
          <Field label="Function" value={data.function} />
          <Field label="Criticality" value={data.criticality} />
          <div className="col-span-2 md:col-span-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Standardized Specification</p>
            <p className="font-medium">{data.standardized_specification || "Missing attribute"}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Aggregate AI Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            {data.confidence != null ? (
              <>
                <p className="text-3xl font-bold text-slate-900">{data.confidence.toFixed(1)}%</p>
                <div className="mt-2 h-2 w-full rounded-full bg-slate-100">
                  <div className="h-2 rounded-full bg-success-600" style={{ width: `${Math.min(100, Math.max(0, data.confidence))}%` }} />
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-400">Not available for this record.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Matching Method</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-brand-600" />
              <p className="text-sm font-semibold text-slate-800">SBERT + pgvector + XGBoost</p>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Sentence-BERT text embeddings, pgvector similarity retrieval, weighted rule-based scoring across
              material identity attributes, and an XGBoost ranking model (where trained) combine to produce the
              final match decision.
            </p>
            <div className="mt-3 flex flex-wrap gap-1">
              {data.mapped_cpses.map((c) => (
                <Badge key={c} variant="brand">
                  {c}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mapped CPSE Materials ({data.mapped_materials.length})</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Object.entries(materialsByCpse).map(([cpseCode, materials]) => (
            <div key={cpseCode} className="rounded border border-slate-300">
              <div className="flex items-center justify-between border-b border-slate-300 bg-slate-100 px-3 py-2">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-700">{cpseCode}</p>
                <Badge variant="outline">
                  {materials.length} material{materials.length !== 1 ? "s" : ""}
                </Badge>
              </div>
              <div className="divide-y divide-slate-200">
                {materials.map((m) => (
                  <Link key={m.id} to={`/materials/${m.id}`} className="block px-3 py-2 hover:bg-slate-50">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-brand-600">{m.original_material_code}</p>
                      <StatusBadge status={m.status} />
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">{m.original_description}</p>
                  </Link>
                ))}
              </div>
            </div>
          ))}
          {data.mapped_materials.length === 0 && <p className="text-sm text-slate-400">No materials mapped yet.</p>}
        </CardContent>
      </Card>

      <p className="text-xs text-slate-400">
        Every change to this record is captured in the{" "}
        <Link to="/audit-log" className="text-brand-600 hover:underline">
          Audit Trail
        </Link>
        .
      </p>
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-medium">{value || "Missing attribute"}</p>
    </div>
  );
}
