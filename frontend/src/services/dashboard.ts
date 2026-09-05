import { api } from "@/services/api";
import type { DashboardStatistics, DashboardTrends } from "@/types";

export async function getStatistics(cpseId?: string) {
  const { data } = await api.get<DashboardStatistics>("/dashboard/statistics", {
    params: { cpse_id: cpseId || undefined },
  });
  return data;
}

export async function getTrends(cpseId?: string) {
  const { data } = await api.get<DashboardTrends>("/dashboard/trends", {
    params: { cpse_id: cpseId || undefined },
  });
  return data;
}
