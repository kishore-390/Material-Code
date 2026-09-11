import { api } from "@/services/api";
import type { AIAnalysis, CandidateScore } from "@/types";

export async function triggerAnalysis(materialId: string) {
  const { data } = await api.post<{ material_id: string; task_id?: string; status: string }>(
    `/ai/analyze/${materialId}`
  );
  return data;
}

export async function getAnalysis(materialId: string) {
  const { data } = await api.get<AIAnalysis>(`/ai/analysis/${materialId}`);
  return data;
}

export async function getAnalysisCandidates(materialId: string) {
  const { data } = await api.get<CandidateScore[]>(`/ai/analysis/${materialId}/candidates`);
  return data;
}
