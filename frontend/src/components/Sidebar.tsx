import {
  BarChart3,
  Bell,
  Boxes,
  Building2,
  CheckSquare,
  GitMerge,
  Layers,
  LayoutDashboard,
  ScrollText,
  Search,
  Settings as SettingsIcon,
  Shield,
  UploadCloud,
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
}

const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/materials", label: "Materials", icon: Boxes },
  { to: "/materials/upload", label: "Upload Material", icon: UploadCloud, roles: ["ADMIN", "CPSE_USER"] },
  { to: "/materials/search", label: "Search", icon: Search },
  { to: "/harmonization", label: "Harmonization", icon: GitMerge },
  { to: "/approvals", label: "Approval Center", icon: CheckSquare, roles: ["ADMIN", "MATERIAL_EXPERT", "VIEWER"] },
  { to: "/common-material-master", label: "Common Material Master", icon: Layers },
  { to: "/cpse", label: "CPSE Directory", icon: Building2 },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/audit-log", label: "Audit Log", icon: ScrollText, roles: ["ADMIN", "MATERIAL_EXPERT", "VIEWER"] },
  { to: "/notifications", label: "Notifications", icon: Bell },
  { to: "/settings", label: "Settings", icon: SettingsIcon, roles: ["ADMIN"] },
];

export function Sidebar() {
  const { user } = useAuth();
  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role.name)));

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col bg-navy-950 text-slate-200">
      <div className="flex items-center gap-2 border-b border-white/10 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600">
          <Shield className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-[13px] font-bold leading-tight text-white">ONE NATION</p>
          <p className="text-[13px] font-bold leading-tight text-white">ONE COMMON</p>
          <p className="text-[13px] font-bold leading-tight text-white">MATERIAL CODE</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4 scrollbar-thin">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/materials"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-600 text-white"
                  : "text-slate-300 hover:bg-white/5 hover:text-white"
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 px-4 py-3 text-[11px] text-slate-400">
        AI-Powered CPSE Material
        <br />
        Harmonization Platform
      </div>
    </aside>
  );
}
