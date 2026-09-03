import { Badge, type BadgeProps } from "@/components/ui/badge";

const STATUS_VARIANTS: Record<string, NonNullable<BadgeProps["variant"]>> = {
  PENDING: "warning",
  PROCESSING: "brand",
  ANALYZED: "brand",
  HARMONIZED: "success",
  REJECTED: "danger",
  FAILED: "danger",
  APPROVED: "success",
  AUTO_APPROVED: "success",
  MORE_INFO_REQUESTED: "warning",
  MERGED: "success",
  NOT_SAME_MATERIAL: "danger",
  AUTO_HARMONIZATION: "success",
  HUMAN_REVIEW_REQUIRED: "warning",
  LOW_CONFIDENCE: "warning",
  NO_COMMON_CODE: "danger",
  AUTO_GENERATED: "brand",
};

function label(status: string) {
  return status.replace(/_/g, " ");
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge variant={STATUS_VARIANTS[status] ?? "default"}>{label(status)}</Badge>;
}
