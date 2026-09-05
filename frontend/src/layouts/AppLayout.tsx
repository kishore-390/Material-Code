import { Menu } from "lucide-react";
import * as React from "react";
import { Outlet } from "react-router-dom";

import { GovernmentFooter } from "@/components/GovernmentFooter";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = React.useState(false);

  return (
    <div className="flex h-screen bg-slate-100">
      <Sidebar mobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex items-stretch">
          <button
            onClick={() => setMobileOpen(true)}
            className="flex shrink-0 items-center border-b border-r border-slate-300 bg-white px-3 text-slate-500 hover:bg-slate-100 md:hidden"
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex-1">
            <Topbar />
          </div>
        </div>
        <main id="main-content" className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
        <GovernmentFooter />
      </div>
    </div>
  );
}
