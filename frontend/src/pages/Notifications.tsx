import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellRing } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { listNotifications, markNotificationRead } from "@/services/notifications";

export default function Notifications() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["notifications"], queryFn: listNotifications });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Notifications</h1>
        <p className="text-sm text-slate-500">Uploads, AI results, approvals and system events.</p>
      </div>

      {isLoading && <p className="text-sm text-slate-400">Loading...</p>}
      {!isLoading && (data ?? []).length === 0 && (
        <p className="py-10 text-center text-sm text-slate-400">You're all caught up.</p>
      )}

      <div className="space-y-2">
        {data?.map((n) => (
          <Card key={n.id} className={n.is_read ? "opacity-70" : "border-brand-200"}>
            <CardContent className="flex items-start gap-3 p-4">
              {n.is_read ? (
                <Bell className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
              ) : (
                <BellRing className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
              )}
              <div className="flex-1">
                <p className="text-sm font-semibold text-slate-800">{n.title}</p>
                <p className="text-sm text-slate-600">{n.message}</p>
                <p className="mt-1 text-xs text-slate-400">{new Date(n.created_at).toLocaleString()}</p>
              </div>
              {!n.is_read && (
                <Button variant="outline" size="sm" onClick={() => markReadMutation.mutate(n.id)}>
                  Mark read
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
