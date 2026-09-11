import { api } from "@/services/api";
import type { CPSEMaterial, CPSEMaterialDetail, MaterialListResponse } from "@/types";

export interface MaterialListParams {
  cpse_id?: string;
  classification?: string;
  status?: string;
  mapped_only?: boolean;
  q?: string;
  page?: number;
  page_size?: number;
}

export async function listMaterials(params: MaterialListParams = {}) {
  const { data } = await api.get<MaterialListResponse>("/cpse-materials", { params });
  return data;
}

export async function getMaterial(id: string) {
  const { data } = await api.get<CPSEMaterialDetail>(`/cpse-materials/${id}`);
  return data;
}

export async function searchMaterials(q: string) {
  const { data } = await api.get<CPSEMaterial[]>("/cpse-materials/search", { params: { q } });
  return data;
}

export async function findSimilarMaterials(materialId: string) {
  const { data } = await api.get<CPSEMaterial[]>(`/cpse-materials/${materialId}/similar`);
  return data;
}
