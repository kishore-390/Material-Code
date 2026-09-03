import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check } from "lucide-react";
import * as React from "react";
import { useParams } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/services/api";
import { getApproval, takeApprovalAction, type ApprovalActionType } from "@/services/approvals";

const MATCH_STYLE: Record<string, string> = {
  SAME: "text-success-600",
  SIMILAR: "text-success-600",
  DIFFERENT: "text-warning-600",
};

const ACTIONS: { type: ApprovalActionType; label: string; variant: "success" | "destructive" | "outline" | "secondary" }[] = [
  { type: "APPROVE", label: "Approve", variant: "success" },
  { type: "MERGE", label: "Merge", variant: "secondary" },
  { type: "REQUEST_MORE_INFO", label: "Request More Information", variant: "outline" },
  { type: "NOT_SAME_MATERIAL", label: "Not Same Material", variant: "outline" },
  { type: "REJECT", label: "Reject", variant: "destructive" },
];

export default function ApprovalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [remarks, setRemarks] = React.useState("");

  const { data: approval, isLoading } = useQuery({
    queryKey: ["approval", id],
    queryFn: () => getApproval(id!),
    enabled: !!id,
  });

  const actionMutation = useMutation({
    mutationFn: (action: ApprovalActionType) => takeApprovalAction(id!, action, remarks || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval", id] });
      setRemarks("");
    },
  });

  if (isLoading || !approval) return <p className="text-sm text-slate-400">Loading...</p>;

  const canAct = (user?.role.name === "ADMIN" || user?.role.name === "MATERIAL_EXPERT") && approval.status === "PENDING";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Approval Review</h1>
          <p className="text-sm text-slate-500">
            AI Score: {approval.ai_score ? `${approval.ai_score.toFixed(1)}%` : "Manual request"}
          </p>
        </div>
        <StatusBadge status={approval.status} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Original Material</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p className="font-semibold">{approval.material.material_code}</p>
            <p>{approval.material.description}</p>
            <p className="text-slate-500">{approval.material.specification}</p>
            <p className="text-slate-500">
              {approval.material.category} &middot; {approval.material.uom} &middot; {approval.material.cpse.code}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Candidate Material</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {approval.candidate ? (
              <>
                <p className="font-semibold">{approval.candidate.material_code}</p>
                <p>{approval.candidate.description}</p>
                <p className="text-slate-500">{approval.candidate.specification}</p>
                <p className="text-slate-500">
                  {approval.candidate.category} &middot; {approval.candidate.uom} &middot; {approval.candidate.cpse.code}
                </p>
              </>
            ) : (
              <p className="text-slate-400">No candidate - manual harmonization request</p>
            )}
          </CardContent>
        </Card>
      </div>

      {approval.comparison.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Field-by-Field Comparison</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {approval.comparison.map((c) => (
              <div key={c.field} className="flex items-center justify-between border-b border-slate-100 py-2 text-sm last:border-0">
                <span className="font-medium text-slate-700">{c.field}</span>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span>{c.original_value || "—"}</span>
                  <span>vs</span>
                  <span>{c.candidate_value || "—"}</span>
                  <span className={`flex items-center gap-1 font-semibold ${MATCH_STYLE[c.match] ?? "text-slate-400"}`}>
                    {c.match === "DIFFERENT" ? <AlertTriangle className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}
                    {c.match === "SAME" ? "Same" : c.match === "SIMILAR" ? "Similar" : "Different"}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {approval.actions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Decision History</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {approval.actions.map((action) => (
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
            <CardTitle>Take Action</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              placeholder="Approval remarks (optional, e.g. Specification and dimensions verified.)"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
            {actionMutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(actionMutation.error)}</p>}
            <div className="flex flex-wrap gap-2">
              {ACTIONS.map((a) => (
                <Button
                  key={a.type}
                  variant={a.variant}
                  disabled={actionMutation.isPending}
                  onClick={() => actionMutation.mutate(a.type)}
                >
                  {a.label}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
