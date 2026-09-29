import * as React from "react";
import { useAuth } from "@/auth/AuthContext";
import type { RoleName } from "@/types";

export function RequireAuth({ children, roles }: { children: React.ReactNode; roles?: RoleName[] }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Loading...</div>;
  }
  if (roles && user && !roles.includes(user.role.name)) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-2 text-slate-500">
        <p className="text-lg font-semibold text-slate-700">Access restricted</p>
        <p className="text-sm">Your role ({user.role.name}) cannot view this page.</p>
      </div>
    );
  }
  return <>{children}</>;
}
