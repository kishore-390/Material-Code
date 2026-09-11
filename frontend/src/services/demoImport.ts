import { api } from "@/services/api";
import type { CsvImportHistoryResponse, CsvImportResponse, CsvValidationResponse } from "@/types";

// DEMO ONLY - production material data is synchronized automatically
// through secure read-only database connectors (see services/synchronization.ts).
// This service exists purely to support the SIH26099 demonstration.

export async function validateDemoCsv(file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<CsvValidationResponse>("/demo-import/validate", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function confirmDemoCsvImport(file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<CsvImportResponse>("/demo-import/confirm", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getDemoImportHistory() {
  const { data } = await api.get<CsvImportHistoryResponse>("/demo-import/history");
  return data;
}

export async function downloadSampleCsv(): Promise<void> {
  const response = await api.get("/demo-import/sample-csv", { responseType: "blob" });
  const url = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "demo_material_import_sample.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
