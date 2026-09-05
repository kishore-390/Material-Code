import { api } from "@/services/api";
import type { CPSE, CPSEStats, UploadBatchListResponse } from "@/types";

export async function listCPSE() {
  const { data } = await api.get<CPSEStats[]>("/cpse");
  return data;
}

export async function getCPSE(id: string) {
  const { data } = await api.get<CPSEStats>(`/cpse/${id}`);
  return data;
}

export interface CPSEFormPayload {
  code?: string;
  name?: string;
  sector?: string;
  description?: string;
  logo?: File | null;
}

function toFormData(payload: CPSEFormPayload) {
  const form = new FormData();
  if (payload.code) form.append("code", payload.code);
  if (payload.name) form.append("name", payload.name);
  if (payload.sector) form.append("sector", payload.sector);
  if (payload.description) form.append("description", payload.description);
  if (payload.logo) form.append("logo", payload.logo);
  return form;
}

export async function createCPSE(payload: CPSEFormPayload) {
  const { data } = await api.post<CPSE>("/cpse", toFormData(payload), {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function updateCPSE(id: string, payload: CPSEFormPayload) {
  const { data } = await api.put<CPSE>(`/cpse/${id}`, toFormData(payload), {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function setCPSEStatus(id: string, is_active: boolean) {
  const { data } = await api.patch<CPSE>(`/cpse/${id}/status`, { is_active });
  return data;
}

export async function listCPSEUploads(id: string, page = 1, page_size = 20) {
  const { data } = await api.get<UploadBatchListResponse>(`/cpse/${id}/uploads`, {
    params: { page, page_size },
  });
  return data;
}
