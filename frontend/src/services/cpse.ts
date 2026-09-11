import { api } from "@/services/api";
import type { CPSE, CPSEStats } from "@/types";

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
}

export async function createCPSE(payload: CPSEFormPayload) {
  const { data } = await api.post<CPSE>("/cpse", payload);
  return data;
}

export async function updateCPSE(id: string, payload: CPSEFormPayload) {
  const { data } = await api.put<CPSE>(`/cpse/${id}`, payload);
  return data;
}

export async function setCPSEStatus(id: string, is_active: boolean) {
  const { data } = await api.patch<CPSE>(`/cpse/${id}/status`, { is_active });
  return data;
}
