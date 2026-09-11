import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import type { ReactNode } from "react";

import { EvidenceChecklist } from "@/components/EvidenceChecklist";
import { PageHeader } from "@/components/PageHeader";
import { ScoreBar } from "@/components/ScoreBar";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getPair } from "@/services/harmonization";
import type { CPSEMaterial } from "@/types";

export default function HarmonizationPairDetail() {
  const { mappingId } = useParams<{ mappingId: string }>();

  const { data: pair, isLoading, isError } = useQuery({
    queryKey: ["harmonization-pair", mappingId],
    queryFn: () => getPair(mappingId!),
    enabled: !!mappingId,
    retry: false,
  });

  if (isLoading) return <p className="text-sm text-slate-400">Loading pair...</p>;

  if (isError || !pair) {
    return (
      <div className="space-y-4">
        <PageHeader breadcrumbs={[{ label: "Harmonization" }, { label: "Not Found" }]} title="Mapping Not Found" />
        <p className="text-sm text-slate-500">This mapping could not be found.</p>
      </div>
    );
  }

  const breakdown = pair.breakdown ?? {};
  const evidenceItems = [
    { label: "Description similarity", score: breakdown.description_score },
    { label: "Specification match", score: breakdown.specification_score },
    { label: "Classification match", score: breakdown.classification_score },
    { label: "Grade match", score: breakdown.grade_score },
    { label: "Dimension match", score: breakdown.dimension_score },
    { label: "UOM match", score: breakdown.uom_score },
    { label: "Function match", score: breakdown.function_score },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Harmonization" }, { label: "Pair Details" }]}
        title="Harmonization Pair Details"
        subtitle="Full AI evidence behind this detected material relationship"
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MaterialSideCard heading="Source" material={pair.source_material} />
        <MaterialSideCard heading="Matched" material={pair.matched_material} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>AI Match Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {Object.entries(breakdown).map(([key, value]) => (
            <ScoreBar key={key} label={key.replace(/_score$/, "").replace(/_/g, " ")} value={value} />
          ))}
          {pair.sbert_similarity != null && <ScoreBar label="SBERT similarity" value={pair.sbert_similarity} />}
          {pair.ml_probability != null && <ScoreBar label={`XGBoost probability (${pair.ml_status})`} value={pair.ml_probability} />}

          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Confidence</p>
            <p className="text-3xl font-bold text-slate-900">
              {pair.confidence_score != null ? `${pair.confidence_score.toFixed(1)}%` : "Not available"}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Decision</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-2">
            <StatusBadge status={pair.mapping_type} />
            <StatusBadge status={pair.decision_status} />
          </div>
          <div className="text-right">
            <p className="text-xs uppercase tracking-wide text-slate-400">Common Material Code</p>
            <Link to={`/common-material-master/${pair.common_material.common_code}`} className="text-lg font-bold text-brand-600 hover:underline">
              {pair.common_material.common_code}
            </Link>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Evidence Checklist</CardTitle>
        </CardHeader>
        <CardContent>
          <EvidenceChecklist items={evidenceItems} />
        </CardContent>
      </Card>
    </div>
  );
}

function MaterialSideCard({ heading, material }: { heading: string; material: CPSEMaterial }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {heading} &middot; {material.cpse.code}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Field label="Material Code" value={material.original_material_code} />
        <Field label="Description" value={material.original_description} />
        <Field label="Specification" value={material.technical_specification} />
        <Field label="Classification" value={material.classification} />
        <Field label="UOM" value={material.uom} />
        <Field label="Manufacturer" value={material.manufacturer} />
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value?: string | ReactNode | null }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-medium text-slate-800">{value || "Missing attribute"}</p>
    </div>
  );
}
