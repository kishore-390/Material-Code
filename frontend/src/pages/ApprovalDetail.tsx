import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { EvidenceChecklist } from "@/components/EvidenceChecklist";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/services/api";
import {
  approveMapping,
  editAndApprove,
  getMappingDetail,
  rejectMapping,
  requestMoreInfo,
  sendToManualReview,
} from "@/services/approvals";

const ACTIVE_STATUSES = new Set(["AI_RECOMMENDED", "PENDING_VALIDATION", "MANUAL_REVIEW", "TECHNICAL_CONFLICT"]);

export default function ApprovalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [remarks, setRemarks] = React.useState("");

  const { data: mapping, isLoading } = useQuery({
    queryKey: ["approval", id],
    queryFn: () => getMappingDetail(id!),
    enabled: !!id,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["approval", id] });
  const approveMut = useMutation({ mutationFn: () => approveMapping(id!, remarks || undefined), onSuccess: invalidate });
  const rejectMut = useMutation({ mutationFn: () => rejectMapping(id!, remarks || undefined), onSuccess: invalidate });
  const manualReviewMut = useMutation({ mutationFn: () => sendToManualReview(id!, remarks || undefined), onSuccess: invalidate });
  const moreInfoMut = useMutation({ mutationFn: () => requestMoreInfo(id!, remarks || undefined), onSuccess: invalidate });
  const editApproveMut = useMutation({
    mutationFn: () => editAndApprove(id!, { remarks: remarks || undefined }),
    onSuccess: invalidate,
  });

  if (isLoading || !mapping) return <p className="text-sm text-slate-400">Loading...</p>;

  const canAct = (user?.role.name === "ADMIN" || user?.role.name === "MATERIAL_EXPERT") && ACTIVE_STATUSES.has(mapping.decision_status);
  const anyPending = approveMut.isPending || rejectMut.isPending || manualReviewMut.isPending || moreInfoMut.isPending || editApproveMut.isPending;
  const anyError = approveMut.error || rejectMut.error || manualReviewMut.error || moreInfoMut.error || editApproveMut.error;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "Approvals", to: "/approvals/pending" }, { label: "Mapping Review" }]}
        title="Mapping Review"
        subtitle="Human validation of an AI-recommended or manually-proposed material mapping."
        actions={<StatusBadge status={mapping.decision_status} />}
      />

      <Card>
        <CardHeader>
          <CardTitle>AI Assessment</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          Confidence: <span className="font-semibold text-slate-900">{mapping.confidence_score ? `${mapping.confidence_score.toFixed(1)}%` : "Manual mapping"}</span>{" "}
          <StatusBadge status={mapping.mapping_type} />
          {mapping.reason && <p className="mt-1 text-slate-500">{mapping.reason}</p>}
        </CardContent>
      </Card>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">Source Materials</p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>CPSE Material</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p className="font-semibold">{mapping.cpse_material.original_material_code}</p>
              <p>{mapping.cpse_material.original_description}</p>
              <p className="text-slate-500">{mapping.cpse_material.technical_specification}</p>
              <p className="text-slate-500">
                {mapping.cpse_material.classification} &middot; {mapping.cpse_material.uom} &middot; {mapping.cpse_material.cpse.code}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Matched Against</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              {mapping.matched_against ? (
                <>
                  <p className="font-semibold">{mapping.matched_against.original_material_code}</p>
                  <p>{mapping.matched_against.original_description}</p>
                  <p className="text-slate-500">{mapping.matched_against.technical_specification}</p>
                  <p className="text-slate-500">
                    {mapping.matched_against.classification} &middot; {mapping.matched_against.uom} &middot; {mapping.matched_against.cpse.code}
                  </p>
                </>
              ) : (
                <p className="text-slate-400">No candidate - manual mapping</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {mapping.evidence && (
        <Card>
          <CardHeader>
            <CardTitle>AI Evidence</CardTitle>
          </CardHeader>
          <CardContent>
            <EvidenceChecklist
              items={Object.entries(mapping.evidence).map(([key, value]) => ({
                label: key.replace(/_/g, " "),
                score: value.score,
              }))}
            />
          </CardContent>
        </Card>
      )}

      {mapping.actions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Approval History</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {mapping.actions.map((action) => (
              <div key={action.id} className="border-b border-slate-100 pb-2 last:border-0">
                <p>
                  <span className="font-semibold">{action.actor_name}</span> &middot; {action.action.replace(/_/g, " ")}
                </p>
                {action.remarks && <p className="text-slate-500">"{action.remarks}"</p>}
                <p className="text-xs text-slate-400">{new Date(action.created_at).toLocaleString()}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {canAct && (
        <Card>
          <CardHeader>
            <CardTitle>Expert Decision</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-slate-500">
              Approving will finalize (or reuse) the Common Material Code shown above as the official mapping.
            </p>
            <Textarea placeholder="Remarks (optional)" value={remarks} onChange={(e) => setRemarks(e.target.value)} />
            {anyError && <p className="text-sm text-danger-600">{apiErrorMessage(anyError)}</p>}
            <div className="flex flex-wrap gap-2">
              <Button variant="success" disabled={anyPending} onClick={() => approveMut.mutate()}>
                Approve
              </Button>
              <Button variant="secondary" disabled={anyPending} onClick={() => editApproveMut.mutate()}>
                Edit &amp; Approve
              </Button>
              <Button variant="outline" disabled={anyPending} onClick={() => manualReviewMut.mutate()}>
                Send to Manual Review
              </Button>
              <Button variant="outline" disabled={anyPending} onClick={() => moreInfoMut.mutate()}>
                Request More Information
              </Button>
              <Button variant="destructive" disabled={anyPending} onClick={() => rejectMut.mutate()}>
                Reject
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-slate-400">
        Every action on this mapping is recorded in the{" "}
        <Link to="/audit-log" className="text-brand-600 hover:underline">
          Audit Trail
        </Link>
        .
      </p>
    </div>
  );
}
