import { useQuery } from "@tanstack/react-query";
import { Check, Cpu, X } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { ApprovalTimeline } from "@/components/ApprovalTimeline";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCommonCode } from "@/services/commonCodes";

function fieldsMatch(a?: string | null, b?: string | null) {
  if (!a || !b) return false;
  return a.trim().toLowerCase() === b.trim().toLowerCase();
}

export default function CommonMaterialCodeDetailPage() {
  const { code } = useParams<{ code: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["common-code", code],
    queryFn: () => getCommonCode(code!),
    enabled: !!code,
  });

  if (isLoading || !data) return <p className="text-sm text-slate-400">Loading...</p>;

  const materialsByCpse = data.linked_materials.reduce<Record<string, typeof data.linked_materials>>((acc, m) => {
    const key = m.cpse.code;
    (acc[key] ??= []).push(m);
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="space-y-2 border-b border-slate-300 pb-4">
        <Breadcrumbs items={[{ label: "Governance", to: "/common-material-master" }, { label: data.code }]} />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Common Material Code</p>
            <h1 className="text-2xl font-bold text-brand-600">{data.code}</h1>
          </div>
          <StatusBadge status={data.status} />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Standard Definition</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          <div className="col-span-2 md:col-span-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Standard Description</p>
            <p className="font-medium">{data.standard_description}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Category</p>
            <p className="font-medium">{data.category}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Material Type</p>
            <p className="font-medium">{data.material_type}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Unit of Measure</p>
            <p className="font-medium">{data.uom}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Standardization Status</p>
            <p className="font-medium">{data.status.replace(/_/g, " ")}</p>
          </div>
          <div className="col-span-2 md:col-span-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">Specification</p>
            <p className="font-medium">{data.standard_specification || "—"}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>AI Match Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            {data.confidence_score != null ? (
              <>
                <p className="text-3xl font-bold text-slate-900">{data.confidence_score.toFixed(1)}%</p>
                <div className="mt-2 h-2 w-full rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-success-600"
                    style={{ width: `${Math.min(100, Math.max(0, data.confidence_score))}%` }}
                  />
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-400">Not available for this record.</p>
            )}
            {data.decision_status && (
              <p className="mt-3 text-xs text-slate-500">
                AI Decision: <span className="font-medium text-slate-700">{data.decision_status.replace(/_/g, " ")}</span>
              </p>
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
              Sentence-BERT text embeddings, pgvector similarity retrieval, weighted rule-based scoring and an
              XGBoost ranking model (where trained) combine to produce the final match decision.
            </p>
            <div className="mt-3 flex flex-wrap gap-1">
              {data.linked_cpses.map((c) => (
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
          <CardTitle>Linked CPSE Materials ({data.linked_materials.length})</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {Object.entries(materialsByCpse).map(([cpseCode, materials]) => (
            <div key={cpseCode} className="rounded border border-slate-300">
              <div className="flex items-center justify-between border-b border-slate-300 bg-slate-100 px-3 py-2">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-700">{cpseCode}</p>
                <Badge variant="outline">{materials.length} material{materials.length !== 1 ? "s" : ""}</Badge>
              </div>
              <div className="divide-y divide-slate-200">
                {materials.map((m) => (
                  <Link
                    key={m.id}
                    to={`/materials/${m.id}`}
                    className="block px-3 py-2 hover:bg-slate-50"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-brand-600">{m.material_code}</p>
                      <StatusBadge status={m.status} />
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">{m.description}</p>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {data.linked_materials.length >= 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Source Material Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Field</TableHead>
                  <TableHead>{data.linked_materials[0].cpse.code} — {data.linked_materials[0].material_code}</TableHead>
                  <TableHead>{data.linked_materials[1].cpse.code} — {data.linked_materials[1].material_code}</TableHead>
                  <TableHead className="w-20">Match</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(
                  [
                    ["Description", data.linked_materials[0].description, data.linked_materials[1].description],
                    ["Specification", data.linked_materials[0].specification, data.linked_materials[1].specification],
                    ["Category", data.linked_materials[0].category, data.linked_materials[1].category],
                    ["UOM", data.linked_materials[0].uom, data.linked_materials[1].uom],
                  ] as [string, string | null | undefined, string | null | undefined][]
                ).map(([field, a, b]) => (
                  <TableRow key={field}>
                    <TableCell className="font-medium text-slate-700">{field}</TableCell>
                    <TableCell className="text-slate-600">{a || "—"}</TableCell>
                    <TableCell className="text-slate-600">{b || "—"}</TableCell>
                    <TableCell>
                      {fieldsMatch(a, b) ? (
                        <Check className="h-4 w-4 text-success-600" />
                      ) : (
                        <X className="h-4 w-4 text-warning-600" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Approval Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <ApprovalTimeline autoApproved={data.decision_status === "AUTO_HARMONIZATION" || data.status === "AUTO_GENERATED"} />
        </CardContent>
      </Card>

      <p className="text-xs text-slate-400">
        Audit Information: every AI decision and human action affecting this record is recorded in the{" "}
        <Link to="/audit-log" className="text-brand-600 hover:underline">
          Audit Log
        </Link>
        .
      </p>
    </div>
  );
}
