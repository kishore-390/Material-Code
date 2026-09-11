import { useQuery } from "@tanstack/react-query";
import { Bell, Landmark, LogOut, Minus, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { useAccessibilitySettings } from "@/hooks/useAccessibilitySettings";
import { listNotifications } from "@/services/notifications";

const SITEMAP_LINKS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/materials", label: "All Materials" },
  { to: "/cpse", label: "Participating CPSEs" },
  { to: "/synchronization", label: "Data Synchronization" },
  { to: "/common-material-master", label: "Common Materials" },
  { to: "/approvals/pending", label: "Pending Validation" },
  { to: "/legacy-codes", label: "Legacy Codes" },
  { to: "/audit-log", label: "Audit Trail" },
  { to: "/settings", label: "Settings" },
];

export function Topbar() {
  const { user, logout } = useAuth();
  const { decreaseFont, resetFont, increaseFont, language, setLanguage } = useAccessibilitySettings();
  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: listNotifications,
    refetchInterval: 20000,
  });
  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <header className="shrink-0 border-b border-slate-300 bg-white">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-navy-900 focus:px-3 focus:py-2 focus:text-xs focus:font-medium focus:text-white"
      >
        Skip to Main Content
      </a>

      <div className="hidden items-center justify-between bg-navy-900 px-6 py-1 text-[11px] text-slate-300 sm:flex">
        <span className="font-semibold uppercase tracking-wide">Government of India</span>
        <div className="flex items-center gap-4">
          <a href="#main-content" className="hover:text-white hover:underline">
            Skip to Main Content
          </a>
          <a href="#accessibility-controls" className="hover:text-white hover:underline">
            Accessibility
          </a>
          <details className="relative">
            <summary className="cursor-pointer list-none hover:text-white hover:underline">Sitemap</summary>
            <div className="absolute right-0 z-40 mt-2 w-52 rounded border border-slate-300 bg-white p-2 text-slate-700 shadow-card">
              {SITEMAP_LINKS.map((link) => (
                <Link key={link.to} to={link.to} className="block rounded px-2 py-1 text-xs hover:bg-slate-100 hover:text-brand-600">
                  {link.label}
                </Link>
              ))}
            </div>
          </details>
          <span className="flex items-center gap-1">
            <button
              onClick={() => setLanguage("EN")}
              className={language === "EN" ? "font-semibold text-white" : "hover:text-white hover:underline"}
            >
              English
            </button>
            <span aria-hidden>|</span>
            <button
              onClick={() => setLanguage("HI")}
              className={language === "HI" ? "font-semibold text-white" : "hover:text-white hover:underline"}
            >
              हिंदी
            </button>
          </span>
        </div>
      </div>

      <div className="gov-stripe h-[3px] w-full" />

      <div className="flex h-16 items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-brand-100 bg-brand-50">
            <Landmark className="h-5 w-5 text-brand-600" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase leading-tight tracking-wider text-slate-500">
              Government of India
            </p>
            <p className="text-sm font-bold uppercase leading-tight tracking-wide text-navy-900">
              National Unified Material Master
            </p>
            <p className="text-[11px] leading-tight text-slate-400">
              AI-Powered National Unified Material Master Platform
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div
            id="accessibility-controls"
            className="flex items-center rounded border border-slate-300 text-slate-600"
            role="group"
            aria-label="Text size"
          >
            <button
              onClick={decreaseFont}
              className="flex h-7 w-7 items-center justify-center border-r border-slate-300 text-xs hover:bg-slate-100"
              title="Decrease text size"
              aria-label="Decrease text size"
            >
              <Minus className="h-3 w-3" />
            </button>
            <button
              onClick={resetFont}
              className="flex h-7 items-center px-1.5 text-xs font-semibold hover:bg-slate-100"
              title="Reset text size"
              aria-label="Reset text size"
            >
              A
            </button>
            <button
              onClick={increaseFont}
              className="flex h-7 w-7 items-center justify-center border-l border-slate-300 text-xs hover:bg-slate-100"
              title="Increase text size"
              aria-label="Increase text size"
            >
              <Plus className="h-3 w-3" />
            </button>
          </div>

          <Link to="/notifications" className="relative rounded p-2 text-slate-500 hover:bg-slate-100" title="Notifications">
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger-600 text-[10px] font-bold text-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </Link>

          <div className="flex items-center gap-2 border-l border-slate-300 pl-3">
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-800">{user?.full_name}</p>
              <Badge variant="brand">{user?.role.name.replace("_", " ")}</Badge>
            </div>
            <button
              onClick={logout}
              className="rounded p-2 text-slate-500 hover:bg-slate-100 hover:text-danger-600"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
