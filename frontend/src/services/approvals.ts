import { api } from "@/services/api";
import type { ApprovalDetail, Mapping } from "@/types";

export async function listPendingApprovals() {
  const { data } = await api.get<Mapping[]>("/approvals/pending");
  return data;
}

export async function listApprovedMappings() {
  const { data } = await api.get<Mapping[]>("/approvals/approved");
  return data;
}

export async function listRejectedMappings() {
  const { data } = await api.get<Mapping[]>("/approvals/rejected");
  return data;
}

export async function getMappingDetail(id: string) {
  const { data } = await api.get<ApprovalDetail>(`/approvals/${id}`);
  return data;
}

export async function approveMapping(id: string, remarks?: string) {
  const { data } = await api.post<Mapping>(`/approvals/${id}/approve`, { remarks });
  return data;
}

export async function rejectMapping(id: string, remarks?: string) {
  const { data } = await api.post<Mapping>(`/approvals/${id}/reject`, { remarks });
  return data;
}

export async function sendToManualReview(id: string, remarks?: string) {
  const { data } = await api.post<Mapping>(`/approvals/${id}/manual-review`, { remarks });
  return data;
}

export async function requestMoreInfo(id: string, remarks?: string) {
  const { data } = await api.post<Mapping>(`/approvals/${id}/request-more-info`, { remarks });
  return data;
}

export interface EditAndApprovePayload {
  remarks?: string;
  standardized_description?: string;
  standardized_specification?: string;
  material_type?: string;
  material_grade?: string;
  dimensions?: string;
  standardized_uom?: string;
  standard?: string;
  function?: string;
  criticality?: string;
  classification?: string;
}

export async function editAndApprove(id: string, payload: EditAndApprovePayload) {
  const { data } = await api.post<Mapping>(`/approvals/${id}/edit-and-approve`, payload);
  return data;
}
