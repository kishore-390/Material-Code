export type RoleName = "ADMIN" | "MATERIAL_EXPERT" | "CPSE_USER" | "VIEWER";

export interface Role {
  id: string;
  name: RoleName;
  description?: string | null;
}

export interface CPSEBrief {
  id: string;
  code: string;
  name: string;
}

export interface CPSE extends CPSEBrief {
  sector?: string | null;
  description?: string | null;
  logo_url?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CPSEStats extends CPSE {
  total_materials: number;
  harmonized_materials: number;
  pending_approvals: number;
  common_codes: number;
  duplicate_materials: number;
  harmonization_percentage: number;
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role: Role;
  cpse?: CPSEBrief | null;
  created_at: string;
}

export interface CommonCodeBrief {
  id: string;
  code: string;
  standard_description: string;
  status: string;
}

export interface Material {
  id: string;
  material_code: string;
  description: string;
  normalized_description?: string | null;
  specification?: string | null;
  normalized_specification?: string | null;
  category: string;
  normalized_category?: string | null;
  uom: string;
  normalized_uom?: string | null;
  manufacturer?: string | null;
  brand?: string | null;
  material_type?: string | null;
  status: string;
  image_url?: string | null;
  cpse: CPSEBrief;
  common_code?: CommonCodeBrief | null;
  source_system?: string | null;
  source_database?: string | null;
  source_material_code?: string | null;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MaterialAttribute {
  id: string;
  attr_key: string;
  attr_value: string;
}

export interface MaterialDetail extends Material {
  attributes: MaterialAttribute[];
  has_embedding: boolean;
}

export interface MaterialListResponse {
  items: Material[];
  total: number;
  page: number;
  page_size: number;
}

export interface SimilarMaterialItem {
  material: Material;
  similarity: number;
}

export interface CandidateScore {
  material: Material;
  final_score: number;
  description_score: number;
  specification_score: number;
  category_score: number;
  uom_score: number;
  image_score: number;
  attribute_score: number;
}

export type Decision = "AUTO_HARMONIZATION" | "HUMAN_REVIEW_REQUIRED" | "LOW_CONFIDENCE" | "NO_COMMON_CODE";

export interface AIAnalysis {
  id: string;
  material_id: string;
  final_score: number;
  description_score: number;
  specification_score: number;
  category_score: number;
  uom_score: number;
  image_score: number;
  attribute_score: number;
  decision: Decision;
  reason_text?: string | null;
  recommended_common_code?: string | null;
  status: string;
  failure_reason?: string | null;
  technical_conflict: boolean;
  conflict_reason?: string | null;
  best_candidate?: Material | null;
  candidates: CandidateScore[];
  created_at: string;
}

export interface CommonMaterialCode {
  id: string;
  code: string;
  material_type: string;
  category: string;
  standard_description: string;
  standard_specification?: string | null;
  uom: string;
  status: string;
  confidence_score?: number | null;
  decision_status?: string | null;
  created_at: string;
}

export interface CommonMaterialCodeDetail extends CommonMaterialCode {
  linked_materials: Material[];
  linked_cpses: string[];
}

export interface HarmonizationRequest {
  id: string;
  material: Material;
  candidate?: Material | null;
  request_type: string;
  status: string;
  ai_score?: number | null;
  common_code?: CommonMaterialCode | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FieldComparison {
  field: string;
  original_value?: string | null;
  candidate_value?: string | null;
  match: "SAME" | "SIMILAR" | "DIFFERENT";
}

export interface ApprovalAction {
  id: string;
  action: string;
  actor_name: string;
  remarks?: string | null;
  created_at: string;
}

export interface ApprovalRequest {
  id: string;
  harmonization_request_id: string;
  material: Material;
  candidate?: Material | null;
  ai_score?: number | null;
  status: string;
  reason?: string | null;
  created_at: string;
  actions: ApprovalAction[];
}

export interface ApprovalDetail extends ApprovalRequest {
  comparison: FieldComparison[];
}

export interface AuditLog {
  id: string;
  actor_type: string;
  actor_name: string;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  details?: Record<string, unknown> | null;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
  created_at: string;
}

export interface DashboardStatistics {
  total_materials: number;
  harmonized_materials: number;
  pending_human_approvals: number;
  cpses_onboarded: number;
  duplicate_codes_reduced: number;
  ai_recommendations: number;
  common_codes_generated: number;
  approved_common_codes: number;
}

export interface ChartPoint {
  label: string;
  value: number;
}

export interface DashboardTrends {
  harmonization_progress: ChartPoint[];
  confidence_distribution: ChartPoint[];
  materials_by_cpse: ChartPoint[];
  harmonized_by_cpse: ChartPoint[];
  monthly_trend: ChartPoint[];
  duplicate_reduction: ChartPoint[];
  estimated_savings: ChartPoint[];
}

export type UploadBatchStatus = "VALIDATING" | "QUEUED" | "PROCESSING" | "COMPLETED" | "PARTIAL" | "FAILED";

export interface UploadBatch {
  id: string;
  cpse: CPSEBrief;
  filename: string;
  uploader?: { id: string; username: string; full_name: string } | null;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  status: UploadBatchStatus;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface UploadBatchListResponse {
  items: UploadBatch[];
  total: number;
  page: number;
  page_size: number;
}

export interface ScanTriggerResponse {
  queued: number;
  material_ids: string[];
  mode: "QUEUED" | "PROCESSED_INLINE";
}

export interface ScanStatusItem {
  material_id: string;
  material_code: string;
  cpse_code: string;
  description: string;
  category: string;
  material_status: string;
  conflict_reason?: string | null;
  best_candidate_material_code?: string | null;
  best_candidate_cpse_code?: string | null;
  latest_decision?: Decision | null;
  ai_confidence?: number | null;
  technical_conflict: boolean;
  common_code?: CommonCodeBrief | null;
}

export interface ScanStatusResponse {
  total: number;
  completed: number;
  items: ScanStatusItem[];
}

export interface SystemSettings {
  threshold_auto: number;
  threshold_review: number;
  threshold_low: number;
  weight_description: number;
  weight_specification: number;
  weight_category: number;
  weight_uom: number;
  weight_image: number;
  weight_attributes: number;
}
