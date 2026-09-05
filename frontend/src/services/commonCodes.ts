import { api } from "@/services/api";
import type { CommonMaterialCode, CommonMaterialCodeDetail } from "@/types";

export async function listCommonCodes(cpseId?: string) {
  const { data } = await api.get<CommonMaterialCode[]>("/common-codes", {
    params: { cpse_id: cpseId || undefined },
  });
  return data;
}

export async function getCommonCode(code: string) {
  const { data } = await api.get<CommonMaterialCodeDetail>(`/common-codes/${code}`);
  return data;
}
