import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Card, CardContent } from "@/components/ui/card";
import { listCPSE } from "@/services/cpse";

export default function Cpse() {
  const { data, isLoading } = useQuery({ queryKey: ["cpse"], queryFn: listCPSE });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">CPSE Directory</h1>
        <p className="text-sm text-slate-500">Central Public Sector Enterprises onboarded to the platform.</p>
      </div>

      {isLoading && <p className="text-sm text-slate-400">Loading...</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((cpse) => (
          <Link key={cpse.id} to={`/cpse/${cpse.id}`}>
            <Card className="h-full transition-shadow hover:shadow-lg">
              <CardContent className="space-y-3 p-5">
                <div>
                  <p className="text-lg font-bold text-slate-900">{cpse.code}</p>
                  <p className="text-xs text-slate-500">{cpse.name}</p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Stat label="Total Materials" value={cpse.total_materials} />
                  <Stat label="Harmonized" value={cpse.harmonized_materials} />
                  <Stat label="Pending Approvals" value={cpse.pending_approvals} />
                  <Stat label="Common Codes" value={cpse.common_codes} />
                </div>
                <div>
                  <div className="mb-1 flex justify-between text-xs text-slate-500">
                    <span>Harmonization %</span>
                    <span className="font-semibold text-slate-800">{cpse.harmonization_percentage}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-slate-100">
                    <div
                      className="h-1.5 rounded-full bg-brand-600"
                      style={{ width: `${Math.min(100, cpse.harmonization_percentage)}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-slate-50 px-2 py-1.5">
      <p className="text-slate-400">{label}</p>
      <p className="text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}
