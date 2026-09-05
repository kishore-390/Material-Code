import {
  BarChart3,
  Bell,
  Boxes,
  Building2,
  CheckSquare,
  Database,
  Landmark,
  Layers,
  LayoutDashboard,
  ScrollText,
  Settings as SettingsIcon,
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

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Home",
    items: [{ to: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Material Data",
    items: [{ to: "/materials", label: "Materials", icon: Boxes, end: true }],
  },
  {
    label: "AI Harmonization",
    items: [
      { to: "/harmonization", label: "Match Recommendations", icon: Layers },
      {
        to: "/harmonization/full-database",
        label: "Full Database Analysis",
        icon: Database,
        roles: ["ADMIN", "MATERIAL_EXPERT"],
      },
    ],
  },
  {
    label: "Governance",
    items: [
      { to: "/approvals", label: "Approval Center", icon: CheckSquare, roles: ["ADMIN", "MATERIAL_EXPERT", "VIEWER"] },
      { to: "/common-material-master", label: "Common Material Master", icon: Layers },
      { to: "/cpse", label: "Organizations", icon: Building2 },
    ],
  },
  {
    label: "Reports & Monitoring",
    items: [
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/audit-log", label: "Audit Log", icon: ScrollText, roles: ["ADMIN", "MATERIAL_EXPERT", "VIEWER"] },
      { to: "/notifications", label: "Notifications", icon: Bell },
    ],
  },
  {
    label: "System",
    items: [{ to: "/settings", label: "Settings", icon: SettingsIcon, roles: ["ADMIN"] }],
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
          <p className="text-[12px] font-bold uppercase leading-tight tracking-wider text-navy-900">CPSE Material Harmonization</p>
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
        AI-Powered CPSE Material
        <br />
        Harmonization Platform
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
