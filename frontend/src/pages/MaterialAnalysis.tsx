import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { EvidenceChecklist } from "@/components/EvidenceChecklist";
import { PageHeader } from "@/components/PageHeader";
import { ScoreBar } from "@/components/ScoreBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysis, getAnalysisCandidates, triggerAnalysis } from "@/services/ai";
import { getMaterial } from "@/services/materials";
import { DECISION_META } from "@/utils/decision";

export default function MaterialAnalysis() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: material } = useQuery({ queryKey: ["material", id], queryFn: () => getMaterial(id!), enabled: !!id });

  const { data: analysis, isError, isLoading } = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => getAnalysis(id!),
    enabled: !!id,
    retry: false,
    refetchInterval: (query) => (query.state.data ? false : 3000),
  });

  const { data: candidates } = useQuery({
    queryKey: ["analysis", id, "candidates"],
    queryFn: () => getAnalysisCandidates(id!),
    enabled: !!id && !!analysis,
  });

  const retryMutation = useMutation({
    mutationFn: () => triggerAnalysis(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["analysis", id] }),
  });

  if (!material) return <p className="text-sm text-slate-400">Loading...</p>;

  const meta = analysis ? DECISION_META[analysis.decision] : null;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Material Master", to: "/materials" }, { label: "AI Analysis" }]}
        title="AI Material Analysis"
        subtitle="Explainable AI recommendation for Common National Material Code harmonization"
      />

      <Card>
        <CardHeader>
          <CardTitle>Original CPSE Material</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
          <Info label="Material Code" value={material.original_material_code} />
          <Info label="CPSE" value={material.cpse.code} />
          <Info label="Classification" value={material.classification} />
          <Info label="Description" value={material.original_description} span />
          <Info label="Specification" value={material.technical_specification} span />
          <Info label="UOM" value={material.uom} />
        </CardContent>
      </Card>

      {isLoading && !analysis && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-slate-500">
            <RefreshCcw className="h-6 w-6 animate-spin text-brand-500" />
            <p className="text-sm">AI is analyzing this material (embeddings, pgvector search, scoring)...</p>
          </CardContent>
        </Card>
      )}

      {isError && !isLoading && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <AlertTriangle className="h-6 w-6 text-warning-500" />
            <p className="text-sm text-slate-600">AI analysis has not run for this material yet.</p>
            <Button onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
              {retryMutation.isPending ? "Queuing..." : "Run AI Analysis"}
            </Button>
          </CardContent>
        </Card>
      )}

      {analysis && analysis.status === "FAILED" && (
        <Card className="border-danger-200">
          <CardContent className="space-y-3 py-6">
            <p className="font-semibold text-danger-600">AI analysis could not determine a reliable match.</p>
            <p className="text-sm text-slate-600">Reason: {analysis.failure_reason || "Insufficient description or specification data."}</p>
            <Button onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
              Retry AI Analysis
            </Button>
          </CardContent>
        </Card>
      )}

      {analysis && analysis.status !== "FAILED" && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>AI Candidate Matches</CardTitle>
            </CardHeader>
            <CardContent>
              {(candidates ?? []).length === 0 && (
                <p className="text-sm text-slate-400">No candidate materials were found for comparison.</p>
              )}
              <div className="space-y-2">
                {(candidates ?? []).map((candidate, index) => (
                  <Link
                    key={candidate.material.id}
                    to={`/materials/${candidate.material.id}`}
                    className="flex items-center justify-between rounded-lg border border-slate-100 p-3 hover:border-brand-200 hover:bg-brand-50/40"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-800">
                        Candidate {index + 1}: {candidate.material.original_material_code}
                      </p>
                      <p className="text-xs text-slate-500">
                        {candidate.material.original_description} &middot; {candidate.material.cpse.code}
                      </p>
                    </div>
                    <Badge variant="brand">Similarity: {candidate.final_score.toFixed(1)}%</Badge>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Why did AI match these materials?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ScoreBar label="Description Match" value={analysis.description_score} />
              <ScoreBar label="Specification Match" value={analysis.specification_score} />
              <ScoreBar label="Classification Match" value={analysis.classification_score} />
              <ScoreBar label="Grade Match" value={analysis.grade_score} />
              <ScoreBar label="Dimension Match" value={analysis.dimension_score} />
              <ScoreBar label="Standard Match" value={analysis.standard_score} />
              <ScoreBar label="UOM Match" value={analysis.uom_score} />
              <ScoreBar label="Function Match" value={analysis.function_score} />

              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400">Final Confidence</p>
                <p className="text-3xl font-bold text-slate-900">{analysis.final_score.toFixed(1)}%</p>
                {analysis.ml_status === "TRAINED" && analysis.ml_probability != null && (
                  <p className="mt-1 text-xs text-slate-400">XGBoost probability: {analysis.ml_probability.toFixed(1)}%</p>
                )}
              </div>

              {analysis.reason_text && (
                <div className="rounded-lg border border-brand-100 bg-brand-50/50 p-3 text-sm text-slate-700">
                  <span className="font-semibold">Reason: </span>
                  {analysis.reason_text}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Evidence Checklist</CardTitle>
            </CardHeader>
            <CardContent>
              <EvidenceChecklist
                items={[
                  { label: "Description similarity", score: analysis.description_score },
                  { label: "Specification compatibility", score: analysis.specification_score },
                  { label: "Classification compatibility", score: analysis.classification_score },
                  { label: "Grade compatibility", score: analysis.grade_score },
                  { label: "Dimension compatibility", score: analysis.dimension_score },
                  { label: "UOM compatibility", score: analysis.uom_score },
                  { label: "Function compatibility", score: analysis.function_score },
                ]}
              />
            </CardContent>
          </Card>

          {analysis.technical_conflict && (
            <Card className="border-danger-600/30 bg-danger-50/40">
              <CardContent className="flex items-start gap-3 py-4">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-danger-600" />
                <div>
                  <p className="text-sm font-bold text-danger-700">Technical Conflict Detected</p>
                  <p className="text-xs text-slate-600">Reason: {analysis.conflict_reason}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    This pair is routed for mandatory human validation and will never be auto-harmonized, regardless
                    of similarity score.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-6 text-center">
              {meta && (
                <div className={`flex items-center gap-2 text-lg font-bold ${meta.tone}`}>
                  <meta.icon className="h-6 w-6" />
                  {meta.label}
                </div>
              )}
              {meta && <p className="max-w-md text-sm text-slate-600">{meta.description}</p>}

              {analysis.recommended_common_code && (
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">Common National Material Code</p>
                  <p className="text-2xl font-bold text-brand-600">{analysis.recommended_common_code}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    A Material Expert must validate this mapping in the Approval queue before it becomes official.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Info({ label, value, span }: { label: string; value?: string | null; span?: boolean }) {
  return (
    <div className={span ? "col-span-2 md:col-span-3" : undefined}>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-medium text-slate-800">{value || "Missing attribute"}</p>
    </div>
  );
}
