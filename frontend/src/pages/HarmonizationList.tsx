import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock, Layers } from "lucide-react";
import * as React from "react";
import { Link, useLocation } from "react-router-dom";

import { KpiCard } from "@/components/KpiCard";
import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDebounce } from "@/hooks/useDebounce";
import { listHarmonizationView, type HarmonizationView } from "@/services/harmonization";

const VIEW_META: Record<HarmonizationView, { title: string; subtitle: string }> = {
  recommendations: {
    title: "AI Recommendations",
    subtitle: "Every mapping the AI harmonization pipeline has proposed, across all relationship types.",
  },
  duplicates: {
    title: "Duplicate Materials",
    subtitle: "Materials the AI pipeline identified as IDENTICAL or DUPLICATE across participating CPSEs.",
  },
  "near-duplicates": {
    title: "Near Duplicates",
    subtitle: "Materials that are highly similar but not confirmed as identical - human validation required.",
  },
  "functional-equivalence": {
    title: "Functional Equivalence",
    subtitle: "Materials that serve the same function and classification despite differing wording.",
  },
  "technical-conflicts": {
    title: "Technical Conflicts",
    subtitle: "Pairs with high textual similarity but a genuine technical incompatibility (grade, dimension, standard) - never auto-harmonized.",
  },
};

function viewFromPath(pathname: string): HarmonizationView {
  const segment = pathname.split("/").pop() as HarmonizationView;
  return VIEW_META[segment] ? segment : "recommendations";
}

export default function HarmonizationList() {
  const location = useLocation();
  const view = viewFromPath(location.pathname);
  const meta = VIEW_META[view];

  const [q, setQ] = React.useState("");
  const [cpseId, setCpseId] = React.useState("");
  const [page, setPage] = React.useState(1);
  const pageSize = 15;
  const debouncedQ = useDebounce(q);

  const { data, isLoading } = useQuery({
    queryKey: ["harmonization", view, { q: debouncedQ, cpseId, page }],
    queryFn: () => listHarmonizationView(view, { q: debouncedQ || undefined, cpse_id: cpseId || undefined, page, page_size: pageSize }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div className="space-y-4">
      <PageHeader breadcrumbs={[{ label: "Harmonization" }, { label: meta.title }]} title={meta.title} subtitle={meta.subtitle} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Total in this view" value={data?.total_duplicates ?? "—"} icon={Layers} accent="brand" />
        <KpiCard label="Pending Validation" value={data?.pending_validation ?? "—"} icon={Clock} accent="warning" />
        <KpiCard label="Approved" value={data?.approved ?? "—"} icon={CheckCircle2} accent="success" />
        <KpiCard label="Common Materials Generated" value={data?.common_materials_generated ?? "—"} icon={AlertTriangle} accent="slate" />
      </div>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search material code or description..."
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          className="max-w-xs"
        />
        <OrganizationSelect
          includeAllOption
          value={cpseId}
          onChange={(e) => {
            setCpseId(e.target.value);
            setPage(1);
          }}
          className="max-w-[220px]"
        />
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Source CPSE</TableHead>
            <TableHead>Material Code</TableHead>
            <TableHead>Matched CPSE</TableHead>
            <TableHead>Matched Material Code</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Decision Status</TableHead>
            <TableHead>Common Code</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-slate-400">
                Loading...
              </TableCell>
            </TableRow>
          )}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-slate-400">
                Nothing in this view yet.
              </TableCell>
            </TableRow>
          )}
          {data?.items.map((item) => (
            <TableRow key={item.mapping_id}>
              <TableCell>{item.source_material.cpse.code}</TableCell>
              <TableCell>
                <Link to={`/materials/${item.source_material.id}`} className="font-medium text-brand-600 hover:underline">
                  {item.source_material.original_material_code}
                </Link>
              </TableCell>
              <TableCell>{item.matched_material.cpse.code}</TableCell>
              <TableCell>
                <Link to={`/materials/${item.matched_material.id}`} className="font-medium text-brand-600 hover:underline">
                  {item.matched_material.original_material_code}
                </Link>
              </TableCell>
              <TableCell className="font-semibold">{item.confidence_score != null ? `${item.confidence_score.toFixed(1)}%` : "—"}</TableCell>
              <TableCell>
                <StatusBadge status={item.decision_status} />
              </TableCell>
              <TableCell>
                <Link to={`/common-material-master/${item.common_material.common_code}`} className="text-brand-600 hover:underline">
                  {item.common_material.common_code}
                </Link>
              </TableCell>
              <TableCell className="text-right">
                <Link to={`/harmonization/pairs/${item.mapping_id}`} className="text-xs font-medium text-brand-600 hover:underline">
                  View Details
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between text-sm text-slate-500">
        <span>
          Page {page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
