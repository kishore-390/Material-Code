import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/utils/cn";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
  {
    variants: {
      variant: {
        default: "border-slate-300 bg-slate-100 text-slate-700",
        brand: "border-brand-100 bg-brand-50 text-brand-700",
        success: "border-success-600/20 bg-success-50 text-success-600",
        warning: "border-warning-600/20 bg-warning-50 text-warning-600",
        danger: "border-danger-600/20 bg-danger-50 text-danger-600",
        outline: "border-slate-300 text-slate-600",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
