import { api } from "@/services/api";
import type { SourceConnection, SyncHistoryListResponse, SyncTriggerResponse, TestConnectionResult } from "@/types";

export async function listSourceConnections() {
  const { data } = await api.get<SourceConnection[]>("/synchronization");
  return data;
}

export interface SourceConnectionCreatePayload {
  cpse_id: string;
  connection_name: string;
  database_type: string;
  host: string;
  port: number;
  database_name: string;
  username_reference: string;
  secret_reference: string;
  ssl_enabled?: boolean;
  table_name: string;
  column_mapping: Record<string, string>;
  cursor_column?: string;
  sync_interval_seconds?: number;
  enabled?: boolean;
}

export async function createSourceConnection(payload: SourceConnectionCreatePayload) {
  const { data } = await api.post<SourceConnection>("/synchronization", payload);
  return data;
}

export async function updateSourceConnection(id: string, payload: Partial<SourceConnectionCreatePayload>) {
  const { data } = await api.patch<SourceConnection>(`/synchronization/${id}`, payload);
  return data;
}

export async function deleteSourceConnection(id: string) {
  await api.delete(`/synchronization/${id}`);
}

export async function testSourceConnection(id: string) {
  const { data } = await api.post<TestConnectionResult>(`/synchronization/${id}/test-connection`);
  return data;
}

export async function syncNow(id: string) {
  const { data } = await api.post<SyncTriggerResponse>(`/synchronization/${id}/sync`);
  return data;
}

export async function fullSync(id: string) {
  const { data } = await api.post<SyncTriggerResponse>(`/synchronization/${id}/full-sync`);
  return data;
}

export async function getSyncHistory(id: string, limit = 20) {
  const { data } = await api.get<SyncHistoryListResponse>(`/synchronization/${id}/sync-history`, { params: { limit } });
  return data;
}
