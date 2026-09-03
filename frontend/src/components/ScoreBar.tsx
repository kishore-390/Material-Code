import { Progress } from "@/components/ui/progress";
import { cn } from "@/utils/cn";

interface ScoreBarProps {
  label: string;
  value: number;
  weight?: number;
}

function colorFor(value: number) {
  if (value >= 95) return "bg-success-600";
  if (value >= 85) return "bg-brand-600";
  if (value >= 60) return "bg-warning-500";
  return "bg-danger-600";
}

export function ScoreBar({ label, value, weight }: ScoreBarProps) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">
          {label}
          {weight !== undefined && <span className="ml-1 text-xs text-slate-400">({Math.round(weight * 100)}% weight)</span>}
        </span>
        <span className="font-semibold text-slate-900">{value.toFixed(1)}%</span>
      </div>
      <Progress value={value} indicatorClassName={cn(colorFor(value))} />
    </div>
  );
}
