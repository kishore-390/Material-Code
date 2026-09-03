import { api } from "@/services/api";
import type { ApprovalDetail, ApprovalRequest } from "@/types";

export async function listApprovals(status?: string) {
  const { data } = await api.get<ApprovalRequest[]>("/approvals", { params: { status } });
  return data;
}

export async function getApproval(id: string) {
  const { data } = await api.get<ApprovalDetail>(`/approvals/${id}`);
  return data;
}

export type ApprovalActionType = "APPROVE" | "REJECT" | "REQUEST_MORE_INFO" | "MERGE" | "NOT_SAME_MATERIAL";

export async function takeApprovalAction(id: string, action: ApprovalActionType, remarks?: string) {
  const { data } = await api.post<ApprovalDetail>(`/approvals/${id}/action`, { action, remarks });
  return data;
}
