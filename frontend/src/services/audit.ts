import { api } from "@/services/api";
import type { AuditLog } from "@/types";

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export async function listAuditLogs(page = 1, pageSize = 50) {
  const { data } = await api.get<AuditLogListResponse>("/audit-logs", {
    params: { page, page_size: pageSize },
  });
  return data;
}
