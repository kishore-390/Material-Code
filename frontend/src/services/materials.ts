import { api } from "@/services/api";
import type { MaterialDetail, MaterialListResponse, SimilarMaterialItem } from "@/types";

export interface MaterialListParams {
  cpse_id?: string;
  category?: string;
  status?: string;
  common_code?: string;
  q?: string;
  page?: number;
  page_size?: number;
}

export async function listMaterials(params: MaterialListParams = {}) {
  const { data } = await api.get<MaterialListResponse>("/materials", { params });
  return data;
}

export async function getMaterial(id: string) {
  const { data } = await api.get<MaterialDetail>(`/materials/${id}`);
  return data;
}

export async function findSimilarMaterials(materialId: string) {
  const { data } = await api.get<SimilarMaterialItem[]>(`/materials/${materialId}/similar`);
  return data;
}
