import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "@/components/PageHeader";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getLegacyCodeCompare } from "@/services/duplicateCodes";
import type { DuplicateCodeClassification } from "@/types";

const CLASSIFICATION_META: Record<
  DuplicateCodeClassification,
  { label: string; variant: NonNullable<BadgeProps["variant"]>; icon: typeof CheckCircle2; note: string }
> = {
  AI_TECHNICAL_EQUIVALENCE: {
    label: "AI Technical Equivalence",
    variant: "success",
    icon: CheckCircle2,
    note: "The AI harmonization pipeline has already linked these two materials to the same common material.",
  },
  TECHNICAL_CONFLICT: {
    label: "Technical Conflict",
    variant: "danger",
    icon: AlertTriangle,
    note: "A genuine technical mismatch (grade, dimension, or standard) was detected - these are not interchangeable despite sharing a source code.",
  },
  SAME_SOURCE_CODE: {
    label: "Same Source Code",
    variant: "outline",
    icon: HelpCircle,
    note: "Identical source code string only - no AI equivalence or conflict has been established for this pair yet.",
  },
};

export default function LegacyCodeDetail() {
  const { code } = useParams<{ code: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["legacy-code-compare", code],
    queryFn: () => getLegacyCodeCompare(code!),
    enabled: !!code,
    retry: false,
  });

  if (isLoading) return <p className="text-sm text-slate-400">Loading...</p>;

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <PageHeader breadcrumbs={[{ label: "Legacy Codes", to: "/legacy-codes" }, { label: "Not Found" }]} title="Legacy Code Not Found" />
        <p className="text-sm text-slate-500">No legacy code group was found for this material code. It may only exist for one CPSE.</p>
      </div>
    );
  }

  const materialById = new Map(data.materials.map((m) => [m.id, m]));

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Legacy Codes", to: "/legacy-codes" }, { label: data.original_material_code }]}
        title={`Legacy Material Code: ${data.original_material_code}`}
        subtitle={`Supplied by ${data.materials.length} CPSEs - compare their descriptions and specifications side by side.`}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.materials.map((material) => (
          <Card key={material.id}>
            <CardHeader>
              <CardTitle>{material.cpse.code}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Field label="Material Code">
                <Link to={`/materials/${material.id}`} className="font-mono text-brand-600 hover:underline">
                  {material.original_material_code}
                </Link>
              </Field>
              <Field label="Description">{material.original_description}</Field>
              <Field label="Material Type">{material.material_type}</Field>
              <Field label="Classification">{material.classification}</Field>
              <Field label="Technical Specification">{material.technical_specification}</Field>
              <Field label="UOM">{material.uom}</Field>
              <Field label="Manufacturer">{material.manufacturer}</Field>
              <Field label="Last Updated">{new Date(material.updated_at).toLocaleString()}</Field>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Relationship Between Each Pair</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.pairs.map((pair) => {
            const a = materialById.get(pair.material_a_id);
            const b = materialById.get(pair.material_b_id);
            const meta = CLASSIFICATION_META[pair.classification];
            if (!a || !b) return null;
            return (
              <div key={`${pair.material_a_id}-${pair.material_b_id}`} className="rounded border border-slate-200 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-700">
                    {a.cpse.code} ({a.original_material_code}) &harr; {b.cpse.code} ({b.original_material_code})
                  </p>
                  <Badge variant={meta.variant}>
                    <meta.icon className="h-3 w-3" /> {meta.label}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-slate-500">{meta.note}</p>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-medium text-slate-800">{children || "Missing attribute"}</p>
    </div>
  );
}
