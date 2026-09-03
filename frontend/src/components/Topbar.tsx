import { useQuery } from "@tanstack/react-query";
import { Bell, LogOut } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/badge";
import { listNotifications } from "@/services/notifications";

export function Topbar() {
  const { user, logout } = useAuth();
  const { data: notifications } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: listNotifications,
    refetchInterval: 20000,
  });
  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
          Government of India &middot; CPSE Material Harmonization
        </p>
        <p className="text-sm font-semibold text-slate-800">
          AI-Powered CPSE Material Harmonization Platform
        </p>
      </div>

      <div className="flex items-center gap-4">
        <Link to="/notifications" className="relative rounded-full p-2 hover:bg-slate-100">
          <Bell className="h-5 w-5 text-slate-600" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger-600 text-[10px] font-bold text-white">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Link>

        <div className="flex items-center gap-2 border-l border-slate-200 pl-4">
          <div className="text-right">
            <p className="text-sm font-medium text-slate-800">{user?.full_name}</p>
            <Badge variant="brand">{user?.role.name.replace("_", " ")}</Badge>
          </div>
          <button
            onClick={logout}
            className="rounded-full p-2 text-slate-500 hover:bg-slate-100 hover:text-danger-600"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
