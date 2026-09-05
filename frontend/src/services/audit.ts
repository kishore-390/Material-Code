import { api } from "@/services/api";
import type { AuditLog } from "@/types";

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogListParams {
  page?: number;
  pageSize?: number;
  entityType?: string;
  action?: string;
}

export async function listAuditLogs({ page = 1, pageSize = 50, entityType, action }: AuditLogListParams = {}) {
  const { data } = await api.get<AuditLogListResponse>("/audit-logs", {
    params: { page, page_size: pageSize, entity_type: entityType || undefined, action: action || undefined },
  });
  return data;
}
