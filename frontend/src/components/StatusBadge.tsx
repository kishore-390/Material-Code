import { Badge, type BadgeProps } from "@/components/ui/badge";

const STATUS_VARIANTS: Record<string, NonNullable<BadgeProps["variant"]>> = {
  // Material status
  PENDING: "warning",
  PROCESSING: "brand",
  ANALYZED: "brand",
  HARMONIZED: "success",
  FAILED: "danger",
  // Match decision (spec section 8)
  IDENTICAL: "success",
  DUPLICATE: "success",
  NEAR_DUPLICATE: "brand",
  FUNCTIONALLY_EQUIVALENT: "brand",
  MANUAL_REVIEW: "warning",
  TECHNICAL_CONFLICT: "danger",
  NOT_EQUIVALENT: "outline",
  // Mapping decision status (spec section 5.4)
  AI_RECOMMENDED: "brand",
  PENDING_VALIDATION: "warning",
  APPROVED: "success",
  EDITED_AND_APPROVED: "success",
  REJECTED: "danger",
  // Common material status (spec section 13)
  ACTIVE: "brand",
  MAPPED: "success",
  RATIONALIZED: "success",
  RETIRED: "outline",
  REPLACED: "outline",
  // Sync status
  RUNNING: "brand",
  SUCCESS: "success",
  PARTIAL: "warning",
  NEVER_SYNCED: "outline",
};

function label(status: string) {
  return status.replace(/_/g, " ");
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge variant={STATUS_VARIANTS[status] ?? "default"}>{label(status)}</Badge>;
}
