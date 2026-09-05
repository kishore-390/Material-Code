import { Check, X } from "lucide-react";

const PASS_THRESHOLD = 70;

interface EvidenceItem {
  label: string;
  score?: number | null;
}

export function EvidenceChecklist({ items }: { items: EvidenceItem[] }) {
  const scored = items.filter((i) => i.score != null);

  return (
    <div className="space-y-1.5">
      {scored.map((item) => {
        const pass = (item.score as number) >= PASS_THRESHOLD;
        return (
          <div key={item.label} className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2">
              {pass ? (
                <Check className="h-4 w-4 shrink-0 text-success-600" />
              ) : (
                <X className="h-4 w-4 shrink-0 text-danger-600" />
              )}
              <span className="text-slate-700">{item.label}</span>
            </span>
            <span className="tabular-nums text-xs font-medium text-slate-500">{(item.score as number).toFixed(1)}%</span>
          </div>
        );
      })}
      {scored.length === 0 && <p className="text-sm text-slate-400">No evidence data available.</p>}
    </div>
  );
}
