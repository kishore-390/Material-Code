import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ScanStatusItem } from "@/types";

interface CommonMaterialGroupCardProps {
  code: string;
  standardDescription: string;
  items: ScanStatusItem[];
}

export function CommonMaterialGroupCard({ code, standardDescription, items }: CommonMaterialGroupCardProps) {
  const confidence = items.find((i) => i.ai_confidence != null)?.ai_confidence;
  const conflicted = items.some((i) => i.technical_conflict);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Common Material Group — {code}</CardTitle>
          <p className="mt-0.5 text-xs text-slate-500">{standardDescription}</p>
        </div>
        <Link to={`/common-material-master/${code}`} className="text-xs font-medium text-brand-600 hover:underline">
          View Common Material
        </Link>
      </CardHeader>
      <CardContent className="space-y-3">
        {conflicted && (
          <div className="flex items-center gap-2 rounded border border-warning-600/30 bg-warning-50 px-3 py-2 text-xs text-warning-700">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Technical conflict detected within this group — routed for mandatory human validation.
          </div>
        )}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {items.map((item) => (
            <div key={item.material_id} className="rounded border border-slate-200 p-2.5">
              <div className="flex items-center justify-between">
                <Badge variant="outline">{item.cpse_code}</Badge>
                <Link to={`/materials/${item.material_id}`} className="font-mono text-xs font-semibold text-brand-600 hover:underline">
                  {item.material_code}
                </Link>
              </div>
              <p className="mt-1 text-xs text-slate-600">{item.description}</p>
            </div>
          ))}
        </div>
        {confidence != null && (
          <p className="text-xs text-slate-500">
            AI Confidence: <span className="font-semibold text-slate-700">{confidence.toFixed(1)}%</span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
