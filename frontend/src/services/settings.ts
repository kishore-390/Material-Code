import { api } from "@/services/api";
import type { SystemSettings } from "@/types";

export async function getSettings() {
  const { data } = await api.get<SystemSettings>("/settings");
  return data;
}

export async function updateSettings(payload: Partial<SystemSettings>) {
  const { data } = await api.put<SystemSettings>("/settings", payload);
  return data;
}
