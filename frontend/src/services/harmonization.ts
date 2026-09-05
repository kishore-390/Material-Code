import { api } from "@/services/api";
import type { HarmonizationRequest, ScanStatusResponse, ScanTriggerResponse } from "@/types";

export async function listHarmonizationRequests(status?: string, cpseId?: string) {
  const { data } = await api.get<HarmonizationRequest[]>("/harmonization", {
    params: { status, cpse_id: cpseId || undefined },
  });
  return data;
}

export async function getHarmonizationRequest(id: string) {
  const { data } = await api.get<HarmonizationRequest>(`/harmonization/${id}`);
  return data;
}

export async function createHarmonizationRequest(payload: {
  material_id: string;
  candidate_material_id?: string;
  notes?: string;
}) {
  const { data } = await api.post<HarmonizationRequest>("/harmonization/request", payload);
  return data;
}

export async function approveHarmonization(id: string, remarks?: string) {
  const { data } = await api.post<HarmonizationRequest>(`/harmonization/${id}/approve`, { remarks });
  return data;
}

export async function rejectHarmonization(id: string, remarks?: string) {
  const { data } = await api.post<HarmonizationRequest>(`/harmonization/${id}/reject`, { remarks });
  return data;
}

export async function scanMaterialMasters(cpseId?: string) {
  const { data } = await api.post<ScanTriggerResponse>("/harmonization/scan", null, {
    params: { cpse_id: cpseId || undefined },
  });
  return data;
}

export async function getScanStatus(materialIds: string[]) {
  const { data } = await api.post<ScanStatusResponse>("/harmonization/scan-status", {
    material_ids: materialIds,
  });
  return data;
}

export async function fullDatabaseScan() {
  const { data } = await api.post<ScanTriggerResponse>("/harmonization/full-database-scan");
  return data;
}
