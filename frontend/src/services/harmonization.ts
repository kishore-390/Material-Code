import { api } from "@/services/api";
import type { DuplicateListResponse, DuplicatePairDetail } from "@/types";

export interface HarmonizationListParams {
  q?: string;
  cpse_id?: string;
  page?: number;
  page_size?: number;
}

export type HarmonizationView = "recommendations" | "duplicates" | "near-duplicates" | "functional-equivalence" | "technical-conflicts";

export async function listHarmonizationView(view: HarmonizationView, params: HarmonizationListParams = {}) {
  const { data } = await api.get<DuplicateListResponse>(`/harmonization/${view}`, { params });
  return data;
}

export async function getPair(mappingId: string) {
  const { data } = await api.get<DuplicatePairDetail>(`/harmonization/pairs/${mappingId}`);
  return data;
}

export interface ScanTriggerResponse {
  queued: number;
  material_ids: string[];
  mode: "QUEUED" | "PROCESSED_INLINE";
}

export async function scanMaterialMasters(cpseId?: string) {
  const { data } = await api.post<ScanTriggerResponse>("/harmonization/scan", null, {
    params: { cpse_id: cpseId || undefined },
  });
  return data;
}

export async function getScanStatus(materialIds: string[]) {
  const { data } = await api.post<{ total: number; completed: number }>("/harmonization/scan-status", materialIds);
  return data;
}
