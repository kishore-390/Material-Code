import { api } from "@/services/api";
import type { CPSEStats } from "@/types";

export async function listCPSE() {
  const { data } = await api.get<CPSEStats[]>("/cpse");
  return data;
}

export async function getCPSE(id: string) {
  const { data } = await api.get<CPSEStats>(`/cpse/${id}`);
  return data;
}

export async function createCPSE(payload: { code: string; name: string; sector?: string }) {
  const { data } = await api.post("/cpse", payload);
  return data;
}
