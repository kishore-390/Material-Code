import {
  BarChart3,
  Bell,
  Boxes,
  CheckCircle2,
  CheckSquare,
  Clock,
  Copy,
  Database,
  FileClock,
  FileUp,
  GitCompareArrows,
  Landmark,
  Layers,
  LayoutDashboard,
  ListTree,
  Network,
  ScrollText,
  Settings as SettingsIcon,
  ShieldAlert,
  Sparkles,
  Tags,
  TrendingUp,
  Upload,
  Wallet,
  XCircle,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { cn } from "@/utils/cn";
import type { RoleName } from "@/types";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: RoleName[];
  end?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

// Spec section 17 - National Material Master navigation tree.
const NAV_GROUPS: NavGroup[] = [
  {
    label: "Home",
    items: [{ to: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Material Master",
    items: [
      { to: "/materials", label: "All Materials", icon: Boxes },
      { to: "/common-material-master", label: "Common Materials", icon: Layers },
      { to: "/materials/cpse", label: "CPSE Materials", icon: Database },
      { to: "/legacy-codes", label: "Legacy Codes", icon: FileClock },
      { to: "/material-upload", label: "Upload Materials", icon: Upload, roles: ["ADMIN", "MATERIAL_EXPERT", "REVIEWER"] },
    ],
  },
  {
    label: "Harmonization",
    items: [
      { to: "/harmonization/recommendations", label: "AI Recommendations", icon: Sparkles },
      { to: "/harmonization/duplicates", label: "Duplicate Materials", icon: Copy },
      { to: "/harmonization/near-duplicates", label: "Near Duplicates", icon: GitCompareArrows },
      { to: "/harmonization/functional-equivalence", label: "Functional Equivalence", icon: CheckCircle2 },
      { to: "/harmonization/technical-conflicts", label: "Technical Conflicts", icon: ShieldAlert },
    ],
  },
  {
    label: "CPSE Network",
    items: [
      { to: "/cpse", label: "Participating CPSEs", icon: Landmark },
      { to: "/synchronization", label: "Data Synchronization", icon: Network, roles: ["ADMIN", "MATERIAL_EXPERT"] },
      { to: "/demo-import", label: "Demo Data Import", icon: FileUp, roles: ["ADMIN", "MATERIAL_EXPERT"] },
    ],
  },
  {
    label: "Approvals",
    items: [
      { to: "/approvals/pending", label: "Pending Validation", icon: Clock, roles: ["ADMIN", "MATERIAL_EXPERT", "REVIEWER", "VIEWER"] },
      { to: "/approvals/approved", label: "Approved", icon: CheckSquare, roles: ["ADMIN", "MATERIAL_EXPERT", "REVIEWER", "VIEWER"] },
      { to: "/approvals/rejected", label: "Rejected", icon: XCircle, roles: ["ADMIN", "MATERIAL_EXPERT", "REVIEWER", "VIEWER"] },
    ],
  },
  {
    label: "Analytics",
    items: [
      { to: "/analytics", label: "Material Master Analytics", icon: BarChart3, end: true },
      { to: "/analytics/procurement", label: "Procurement Analytics", icon: Wallet },
      { to: "/analytics/classification", label: "Classification Distribution", icon: Tags },
      { to: "/analytics/trends", label: "Harmonization Trends", icon: TrendingUp },
    ],
  },
  {
    label: "Governance",
    items: [
      { to: "/audit-log", label: "Audit Trail", icon: ScrollText, roles: ["ADMIN", "MATERIAL_EXPERT", "REVIEWER", "VIEWER"] },
      { to: "/governance/rules", label: "Rules & Policies", icon: ListTree, roles: ["ADMIN"] },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/notifications", label: "Notifications", icon: Bell },
      { to: "/settings", label: "Settings", icon: SettingsIcon, roles: ["ADMIN"] },
    ],
  },
];

interface SidebarProps {
  /** Mobile drawer state - only applies below the md breakpoint. */
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  const { user } = useAuth();
  const visibleGroups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.roles || (user && item.roles.includes(user.role.name))),
  })).filter((group) => group.items.length > 0);

  const content = (
    <>
      <div className="flex items-center gap-2.5 border-b border-slate-200 px-5 py-5 md:px-3 lg:px-5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-brand-100 bg-brand-50">
          <Landmark className="h-5 w-5 text-brand-600" />
        </div>
        <div className="md:hidden lg:block">
          <p className="text-[10px] font-semibold uppercase leading-tight tracking-wider text-slate-500">Government of India</p>
          <p className="text-[12px] font-bold uppercase leading-tight tracking-wider text-navy-900">National Material Master</p>
        </div>
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4 scrollbar-thin">
        {visibleGroups.map((group) => (
          <div key={group.label}>
            <p className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400 md:hidden lg:block">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavLink
                  key={`${group.label}-${item.to}`}
                  to={item.to}
                  end={item.end}
                  onClick={onCloseMobile}
                  title={item.label}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded border-l-[3px] px-2.5 py-2 text-[13px] font-medium transition-colors",
                      isActive
                        ? "border-saffron-500 bg-brand-600 text-white"
                        : "border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    )
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span className="md:hidden lg:inline">{item.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-200 px-4 py-3 text-[11px] leading-tight text-slate-400 md:hidden lg:block">
        AI-Powered National Unified
        <br />
        Material Master Platform
      </div>
    </>
  );

  return (
    <>
      {/* Desktop / tablet: static, icon-rail on md, full on lg+ */}
      <aside className="hidden shrink-0 flex-col border-r border-slate-300 bg-white text-slate-700 md:flex md:w-16 lg:w-64">
        {content}
      </aside>

      {/* Mobile: overlay drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-slate-900/40" onClick={onCloseMobile} />
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-slate-300 bg-white text-slate-700">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
