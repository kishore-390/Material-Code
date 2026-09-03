import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { useParams } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  approveHarmonization,
  getHarmonizationRequest,
  rejectHarmonization,
} from "@/services/harmonization";

export default function HarmonizationDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [remarks, setRemarks] = React.useState("");

  const { data: h, isLoading } = useQuery({
    queryKey: ["harmonization", id],
    queryFn: () => getHarmonizationRequest(id!),
    enabled: !!id,
  });

  const approveMutation = useMutation({
    mutationFn: () => approveHarmonization(id!, remarks),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["harmonization", id] }),
  });
  const rejectMutation = useMutation({
    mutationFn: () => rejectHarmonization(id!, remarks),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["harmonization", id] }),
  });

  if (isLoading || !h) return <p className="text-sm text-slate-400">Loading...</p>;

  const canDecide =
    (user?.role.name === "ADMIN" || user?.role.name === "MATERIAL_EXPERT") &&
    h.status !== "APPROVED" &&
    h.status !== "AUTO_APPROVED" &&
    h.status !== "REJECTED";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Harmonization Request</h1>
          <p className="text-sm text-slate-500">{h.request_type} request</p>
        </div>
        <StatusBadge status={h.status} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Material</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p className="font-semibold">{h.material.material_code}</p>
            <p>{h.material.description}</p>
            <p className="text-slate-500">{h.material.specification}</p>
            <p className="text-slate-500">{h.material.cpse.code}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Candidate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {h.candidate ? (
              <>
                <p className="font-semibold">{h.candidate.material_code}</p>
                <p>{h.candidate.description}</p>
                <p className="text-slate-500">{h.candidate.specification}</p>
                <p className="text-slate-500">{h.candidate.cpse.code}</p>
              </>
            ) : (
              <p className="text-slate-400">No candidate selected (manual grouping)</p>
            )}
          </CardContent>
        </Card>
      </div>

      {h.notes && (
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-600">{h.notes}</CardContent>
        </Card>
      )}

      {h.common_code && (
        <Card className="border-success-200 bg-success-50/40">
          <CardContent className="py-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">Common Material Code</p>
            <p className="text-xl font-bold text-success-700">{h.common_code.code}</p>
          </CardContent>
        </Card>
      )}

      {canDecide && (
        <Card>
          <CardHeader>
            <CardTitle>Expert Decision</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              placeholder="Optional remarks (e.g. specification and dimensions verified)"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
            <div className="flex gap-2">
              <Button variant="success" onClick={() => approveMutation.mutate()} disabled={approveMutation.isPending}>
                Approve
              </Button>
              <Button variant="destructive" onClick={() => rejectMutation.mutate()} disabled={rejectMutation.isPending}>
                Reject
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
