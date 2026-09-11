import { useQuery } from "@tanstack/react-query";
import { Building2, Copy, Layers } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { KpiCard } from "@/components/KpiCard";
import { PageHeader } from "@/components/PageHeader";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDebounce } from "@/hooks/useDebounce";
import { listLegacyCodes } from "@/services/duplicateCodes";

export default function LegacyCodes() {
  const [q, setQ] = React.useState("");
  const debouncedQ = useDebounce(q);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["legacy-codes", debouncedQ],
    queryFn: () => listLegacyCodes({ q: debouncedQ || undefined, page_size: 50 }),
  });

  const hasAny = (data?.total_duplicate_codes ?? 0) > 0;

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Material Master" }, { label: "Legacy Codes" }]}
        title="Legacy Material Codes"
        subtitle="The same original material code supplied by two or more CPSEs. This does not by itself mean the materials are the same physical item - compare each group to see whether the AI pipeline has confirmed technical equivalence, found a technical conflict, or established no relationship yet."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard label="Total Legacy Code Groups" value={data?.total_duplicate_codes ?? "—"} icon={Copy} accent="warning" />
        <KpiCard label="CPSEs Affected" value={data?.cpses_affected ?? "—"} icon={Building2} accent="brand" />
        <KpiCard label="Materials Affected" value={data?.materials_affected ?? "—"} icon={Layers} accent="slate" />
      </div>

      <Input placeholder="Search by original material code..." value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" />

      {isError && (
        <p className="rounded border border-danger-200 bg-danger-50 p-4 text-sm text-danger-700">
          Could not load legacy material codes. Please try again.
        </p>
      )}

      {!isError && !isLoading && !hasAny && !debouncedQ && (
        <div className="rounded border border-slate-200 bg-slate-50 p-10 text-center">
          <p className="text-sm font-medium text-slate-600">No legacy code groups detected yet.</p>
        </div>
      )}

      {!isError && (isLoading || hasAny || !!debouncedQ) && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Original Material Code</TableHead>
              <TableHead>CPSEs</TableHead>
              <TableHead>Materials</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-slate-400">
                  Loading...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-slate-400">
                  No legacy codes match your search.
                </TableCell>
              </TableRow>
            )}
            {data?.items.map((group) => (
              <TableRow key={group.original_material_code}>
                <TableCell className="font-mono font-semibold text-slate-800">{group.original_material_code}</TableCell>
                <TableCell>{group.cpses.join(", ")}</TableCell>
                <TableCell>{group.materials_count}</TableCell>
                <TableCell className="text-right">
                  <Link to={`/legacy-codes/${encodeURIComponent(group.original_material_code)}`} className="text-xs font-medium text-brand-600 hover:underline">
                    Compare
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
