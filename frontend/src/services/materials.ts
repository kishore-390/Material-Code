import { api } from "@/services/api";
import type {
  BulkImportResponse,
  BulkValidationResponse,
  MaterialDetail,
  MaterialListResponse,
  SimilarMaterialItem,
} from "@/types";

export interface MaterialListParams {
  cpse_id?: string;
  category?: string;
  status?: string;
  common_code?: string;
  q?: string;
  page?: number;
  page_size?: number;
}

export async function listMaterials(params: MaterialListParams = {}) {
  const { data } = await api.get<MaterialListResponse>("/materials", { params });
  return data;
}

export async function getMaterial(id: string) {
  const { data } = await api.get<MaterialDetail>(`/materials/${id}`);
  return data;
}

export interface CreateMaterialPayload {
  material_code: string;
  description: string;
  specification?: string;
  category: string;
  uom: string;
  cpse_code: string;
  manufacturer?: string;
  brand?: string;
  material_type?: string;
  attributes?: Record<string, string>;
  image?: File | null;
}

export async function createMaterial(payload: CreateMaterialPayload) {
  const form = new FormData();
  form.append("material_code", payload.material_code);
  form.append("description", payload.description);
  if (payload.specification) form.append("specification", payload.specification);
  form.append("category", payload.category);
  form.append("uom", payload.uom);
  form.append("cpse_code", payload.cpse_code);
  if (payload.manufacturer) form.append("manufacturer", payload.manufacturer);
  if (payload.brand) form.append("brand", payload.brand);
  if (payload.material_type) form.append("material_type", payload.material_type);
  if (payload.attributes && Object.keys(payload.attributes).length > 0) {
    form.append("attributes_json", JSON.stringify(payload.attributes));
  }
  if (payload.image) form.append("image", payload.image);

  const { data } = await api.post<MaterialDetail>("/materials", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function searchMaterials(q: string) {
  const { data } = await api.get<SimilarMaterialItem[]>("/materials/search", { params: { q } });
  return data;
}

export async function findSimilarMaterials(materialId: string) {
  const { data } = await api.get<SimilarMaterialItem[]>(`/materials/${materialId}/similar`);
  return data;
}

export async function validateBulkUpload(file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<BulkValidationResponse>("/materials/bulk/validate", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function importBulkUpload(batchToken: string) {
  const form = new FormData();
  form.append("batch_token", batchToken);
  const { data } = await api.post<BulkImportResponse>("/materials/bulk/import", form);
  return data;
}
