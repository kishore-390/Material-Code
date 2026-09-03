import { api } from "@/services/api";
import type { DashboardStatistics, DashboardTrends } from "@/types";

export async function getStatistics() {
  const { data } = await api.get<DashboardStatistics>("/dashboard/statistics");
  return data;
}

export async function getTrends() {
  const { data } = await api.get<DashboardTrends>("/dashboard/trends");
  return data;
}
