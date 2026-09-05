import { ChevronRight, Home } from "lucide-react";
import { Link } from "react-router-dom";

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-slate-500">
      <Link to="/dashboard" className="flex items-center gap-1 text-brand-600 hover:underline">
        <Home className="h-3 w-3" />
        Home
      </Link>
      {items.map((item, idx) => {
        const isLast = idx === items.length - 1;
        return (
          <span key={item.label} className="flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3 text-slate-400" />
            {item.to && !isLast ? (
              <Link to={item.to} className="text-brand-600 hover:underline">
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? "font-medium text-slate-600" : "text-brand-600"}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
