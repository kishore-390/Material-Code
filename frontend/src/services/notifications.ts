import { api } from "@/services/api";
import type { Notification } from "@/types";

export async function listNotifications() {
  const { data } = await api.get<Notification[]>("/notifications");
  return data;
}

export async function markNotificationRead(id: string) {
  const { data } = await api.put<Notification>(`/notifications/${id}/read`);
  return data;
}
