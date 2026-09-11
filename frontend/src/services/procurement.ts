import { api } from "@/services/api";
import type { CollaborativeProcurementOpportunity, ProcurementRecord } from "@/types";

export async function listCollaborativeOpportunities(limit = 20) {
  const { data } = await api.get<CollaborativeProcurementOpportunity[]>("/procurement/opportunities", {
    params: { limit },
  });
  return data;
}

export async function getProcurementHistory(cpseMaterialId: string) {
  const { data } = await api.get<ProcurementRecord[]>(`/procurement/history/${cpseMaterialId}`);
  return data;
}
