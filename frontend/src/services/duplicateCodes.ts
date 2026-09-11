import { api } from "@/services/api";
import type { DuplicateCodeCompare, DuplicateCodeListResponse } from "@/types";

export async function listLegacyCodes(params: { q?: string; page?: number; page_size?: number } = {}) {
  const { data } = await api.get<DuplicateCodeListResponse>("/legacy-codes", { params });
  return data;
}

export async function getLegacyCodeCompare(originalMaterialCode: string) {
  const { data } = await api.get<DuplicateCodeCompare>(`/legacy-codes/${encodeURIComponent(originalMaterialCode)}`);
  return data;
}
