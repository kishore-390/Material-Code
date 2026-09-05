import { Check } from "lucide-react";

interface TimelineStep {
  label: string;
  note?: string;
}

const STEPS: TimelineStep[] = [
  { label: "Material Submitted" },
  { label: "AI Similarity Analysis" },
  { label: "Duplicate Detection" },
  { label: "Standard Description Generated" },
  { label: "Technical Review" },
  { label: "Approval" },
  { label: "Common Material Code Created" },
];

interface ApprovalTimelineProps {
  autoApproved: boolean;
}

export function ApprovalTimeline({ autoApproved }: ApprovalTimelineProps) {
  return (
    <ol className="space-y-0">
      {STEPS.map((step, idx) => {
        const isLast = idx === STEPS.length - 1;
        const isAutoStage = autoApproved && (step.label === "Technical Review" || step.label === "Approval");
        return (
          <li key={step.label} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 border-success-600 bg-success-50 text-success-600">
                <Check className="h-3.5 w-3.5" />
              </span>
              {!isLast && <span className="w-px flex-1 bg-slate-300" />}
            </div>
            <div className="pb-5">
              <p className="text-sm font-medium text-slate-800">{step.label}</p>
              {isAutoStage && (
                <p className="text-xs text-slate-400">Auto-completed by AI decision engine (no manual step required)</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
