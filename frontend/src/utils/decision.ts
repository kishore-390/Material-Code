import { AlertTriangle, CheckCircle2, HelpCircle, XCircle } from "lucide-react";

import type { Decision } from "@/types";

export interface DecisionMeta {
  confidenceLabel: "HIGH CONFIDENCE" | "MEDIUM CONFIDENCE" | "LOW CONFIDENCE" | "NOT MATCHED";
  recommendation: "Same Material / Functionally Equivalent" | "Possibly Equivalent" | "Different Material";
  statusLabel: string;
  icon: typeof CheckCircle2;
  tone: string;
  badgeVariant: "success" | "warning" | "danger";
  description: string;
}

export const DECISION_META: Record<Decision, DecisionMeta> = {
  AUTO_HARMONIZATION: {
    confidenceLabel: "HIGH CONFIDENCE",
    recommendation: "Same Material / Functionally Equivalent",
    statusLabel: "AUTO-MAPPED",
    icon: CheckCircle2,
    tone: "text-success-600",
    badgeVariant: "success",
    description: "AI confidence meets the auto-harmonization threshold. Mapped automatically; no human action required.",
  },
  HUMAN_REVIEW_REQUIRED: {
    confidenceLabel: "MEDIUM CONFIDENCE",
    recommendation: "Possibly Equivalent",
    statusLabel: "PENDING REVIEW",
    icon: HelpCircle,
    tone: "text-warning-600",
    badgeVariant: "warning",
    description: "AI found a plausible match, but a Material Expert must validate this pairing in the Approval Center before a common code is finalized.",
  },
  LOW_CONFIDENCE: {
    confidenceLabel: "LOW CONFIDENCE",
    recommendation: "Different Material",
    statusLabel: "MANUAL REVIEW REQUIRED",
    icon: AlertTriangle,
    tone: "text-warning-600",
    badgeVariant: "warning",
    description: "AI confidence is below the review threshold. Manual review is required before any harmonization action.",
  },
  NO_COMMON_CODE: {
    confidenceLabel: "NOT MATCHED",
    recommendation: "Different Material",
    statusLabel: "NO COMMON CODE",
    icon: XCircle,
    tone: "text-danger-600",
    badgeVariant: "danger",
    description: "No sufficiently similar material was found. A common material code cannot be recommended.",
  },
};
