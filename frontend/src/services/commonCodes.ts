import { api } from "@/services/api";
import type { CommonMaterial, CommonMaterialDetail } from "@/types";

export async function listCommonMaterials(cpseId?: string) {
  const { data } = await api.get<CommonMaterial[]>("/common-materials", {
    params: { cpse_id: cpseId || undefined },
  });
  return data;
}

export async function getCommonMaterial(code: string) {
  const { data } = await api.get<CommonMaterialDetail>(`/common-materials/${code}`);
  return data;
}
