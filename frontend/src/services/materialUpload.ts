import { api } from "@/services/api";
import type { CsvImportHistoryResponse, CsvImportResponse, CsvValidationResponse } from "@/types";

// Company self-service material upload - the REAL (non-demo) counterpart to
// services/demoImport.ts. Production ingestion is still connector-first
// (see services/synchronization.ts); this lets an authorized company user
// also upload their own real material master, strictly scoped to their own
// CPSE, through the exact same governed AI pipeline.

function buildForm(file: File, cpseId?: string) {
  const form = new FormData();
  form.append("file", file);
  if (cpseId) form.append("cpse_id", cpseId);
  return form;
}

export async function validateMaterialUpload(file: File, cpseId?: string) {
  const { data } = await api.post<CsvValidationResponse>("/materials/upload/validate", buildForm(file, cpseId), {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function confirmMaterialUpload(file: File, cpseId?: string) {
  const { data } = await api.post<CsvImportResponse>("/materials/upload/confirm", buildForm(file, cpseId), {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getMaterialUploadHistory() {
  const { data } = await api.get<CsvImportHistoryResponse>("/materials/upload/history");
  return data;
}

export async function downloadUploadTemplate(): Promise<void> {
  const response = await api.get("/materials/upload/template", { responseType: "blob" });
  const url = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "material_upload_template.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
