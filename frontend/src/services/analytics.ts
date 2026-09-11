import { api } from "@/services/api";
import type { ChartPoint } from "@/types";

export async function getClassificationDistribution() {
  const { data } = await api.get<ChartPoint[]>("/analytics/classification-distribution");
  return data;
}

export async function getCpseComparison() {
  const { data } = await api.get<ChartPoint[]>("/analytics/cpse-comparison");
  return data;
}

export async function getCommonCodeAdoption() {
  const { data } = await api.get<ChartPoint[]>("/analytics/common-code-adoption");
  return data;
}

export async function getMaterialQuality() {
  const { data } = await api.get<ChartPoint[]>("/analytics/material-quality");
  return data;
}

export async function getHarmonizationTrends() {
  const { data } = await api.get<ChartPoint[]>("/analytics/harmonization-trends");
  return data;
}
