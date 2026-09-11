import { AlertTriangle, CheckCircle2, HelpCircle, ShieldAlert, XCircle } from "lucide-react";

import type { MatchDecision } from "@/types";

export interface DecisionMeta {
  label: string;
  icon: typeof CheckCircle2;
  tone: string;
  badgeVariant: "success" | "warning" | "danger" | "brand" | "outline";
  description: string;
}

export const DECISION_META: Record<MatchDecision, DecisionMeta> = {
  IDENTICAL: {
    label: "IDENTICAL",
    icon: CheckCircle2,
    tone: "text-success-600",
    badgeVariant: "success",
    description: "Every key technical attribute matches exactly - these are the same material.",
  },
  DUPLICATE: {
    label: "DUPLICATE",
    icon: CheckCircle2,
    tone: "text-success-600",
    badgeVariant: "success",
    description: "AI confidence meets the auto-harmonization threshold.",
  },
  NEAR_DUPLICATE: {
    label: "NEAR DUPLICATE",
    icon: HelpCircle,
    tone: "text-brand-600",
    badgeVariant: "brand",
    description: "A strong candidate match - human confirmation is required before harmonization.",
  },
  FUNCTIONALLY_EQUIVALENT: {
    label: "FUNCTIONALLY EQUIVALENT",
    icon: HelpCircle,
    tone: "text-brand-600",
    badgeVariant: "brand",
    description: "These materials serve the same function and classification despite differing wording.",
  },
  MANUAL_REVIEW: {
    label: "MANUAL REVIEW",
    icon: AlertTriangle,
    tone: "text-warning-600",
    badgeVariant: "warning",
    description: "AI confidence is insufficient for automatic classification - manual review is required.",
  },
  TECHNICAL_CONFLICT: {
    label: "TECHNICAL CONFLICT",
    icon: ShieldAlert,
    tone: "text-danger-600",
    badgeVariant: "danger",
    description: "A technical conflict was detected between key specifications - never auto-harmonized.",
  },
  NOT_EQUIVALENT: {
    label: "NOT EQUIVALENT",
    icon: XCircle,
    tone: "text-slate-500",
    badgeVariant: "outline",
    description: "No sufficiently similar material found - not considered equivalent.",
  },
};
