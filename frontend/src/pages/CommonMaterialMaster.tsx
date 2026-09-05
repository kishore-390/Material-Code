import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, RefreshCw, SlidersHorizontal, X } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCommonCode, listCommonCodes } from "@/services/commonCodes";

const PAGE_SIZE = 10;

function formatDate(iso: string) {
  const d = new Date(iso);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()}`;
}

function toCsvValue(value: string) {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

export default function CommonMaterialMaster() {
  const queryClient = useQueryClient();
  const [cpseId, setCpseId] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [showAdvanced, setShowAdvanced] = React.useState(false);
  const [statusFilter, setStatusFilter] = React.useState("");
  const [categoryFilter, setCategoryFilter] = React.useState("");
  const [page, setPage] = React.useState(1);

  const { data: codes, isLoading, isFetching } = useQuery({
    queryKey: ["common-codes", cpseId],
    queryFn: () => listCommonCodes(cpseId || undefined),
  });

  const detailQueries = useQueries({
    queries: (codes ?? []).map((c) => ({
      queryKey: ["common-code", c.code],
      queryFn: () => getCommonCode(c.code),
      enabled: !!codes,
    })),
  });

  const rows = React.useMemo(() => {
    return (codes ?? []).map((code, idx) => {
      const detail = detailQueries[idx]?.data;
      return {
        code,
        cpses: detail?.linked_cpses ?? [],
        originalCodesCount: detail?.linked_materials.length ?? 0,
      };
    });
  }, [codes, detailQueries]);

  const categories = React.useMemo(
    () => Array.from(new Set((codes ?? []).map((c) => c.category))).sort(),
    [codes]
  );
  const statuses = React.useMemo(
    () => Array.from(new Set((codes ?? []).map((c) => c.status))).sort(),
    [codes]
  );

  const filteredRows = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((r) => {
      if (statusFilter && r.code.status !== statusFilter) return false;
      if (categoryFilter && r.code.category !== categoryFilter) return false;
      if (!q) return true;
      return (
        r.code.code.toLowerCase().includes(q) ||
        r.code.standard_description.toLowerCase().includes(q) ||
        r.code.category.toLowerCase().includes(q)
      );
    });
  }, [rows, search, statusFilter, categoryFilter]);

  React.useEffect(() => {
    setPage(1);
  }, [search, statusFilter, categoryFilter, cpseId]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageRows = filteredRows.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  function handleRefresh() {
    queryClient.invalidateQueries({ queryKey: ["common-codes"] });
    queryClient.invalidateQueries({ queryKey: ["common-code"] });
  }

  function handleExport() {
    const header = [
      "Common Code",
      "Standard Description",
      "Category",
      "UOM",
      "Linked CPSEs",
      "Original Codes",
      "AI Confidence",
      "Status",
      "Created Date",
    ];
    const lines = [header.join(",")];
    for (const r of filteredRows) {
      lines.push(
        [
          r.code.code,
          r.code.standard_description,
          r.code.category,
          r.code.uom,
          r.cpses.join("; "),
          String(r.originalCodesCount),
          r.code.confidence_score != null ? r.code.confidence_score.toFixed(1) : "",
          r.code.status,
          formatDate(r.code.created_at),
        ]
          .map(toCsvValue)
          .join(",")
      );
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "common-material-master.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const activeAdvancedFilters = (statusFilter ? 1 : 0) + (categoryFilter ? 1 : 0);

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Governance", to: "/common-material-master" }, { label: "Common Material Master" }]}
        title="Common Material Master"
        subtitle="Centralized master repository for harmonized materials across participating CPSEs. Only AI-recommended pairs that have completed automatic or human-validated harmonization appear here."
      />

      <Card className="p-3">
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Search materials by code, description or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 min-w-[240px] flex-1 rounded border border-slate-300 px-3 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <OrganizationSelect includeAllOption value={cpseId} onChange={(e) => setCpseId(e.target.value)} className="h-9 max-w-[200px]" />
          <Button variant="outline" size="sm" onClick={() => setShowAdvanced((v) => !v)}>
            <SlidersHorizontal className="h-4 w-4" />
            Advanced Filter
            {activeAdvancedFilters > 0 && (
              <span className="ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white">
                {activeAdvancedFilters}
              </span>
            )}
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isFetching}>
            <RefreshCw className={"h-4 w-4" + (isFetching ? " animate-spin" : "")} />
            Refresh
          </Button>
        </div>

        {showAdvanced && (
          <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-3">
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-8 rounded border border-slate-300 px-2 text-sm focus:border-brand-500 focus:outline-none"
              >
                <option value="">All</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium uppercase tracking-wide text-slate-500">Category</label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="h-8 rounded border border-slate-300 px-2 text-sm focus:border-brand-500 focus:outline-none"
              >
                <option value="">All</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            {activeAdvancedFilters > 0 && (
              <button
                onClick={() => {
                  setStatusFilter("");
                  setCategoryFilter("");
                }}
                className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline"
              >
                <X className="h-3 w-3" /> Clear filters
              </button>
            )}
          </div>
        )}
      </Card>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Common Code</TableHead>
            <TableHead>Standard Description</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>UOM</TableHead>
            <TableHead>Linked CPSEs</TableHead>
            <TableHead>Original Codes</TableHead>
            <TableHead>AI Confidence</TableHead>
            <TableHead>Approval Status</TableHead>
            <TableHead>Created Date</TableHead>
            <TableHead>Last Updated</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={11} className="text-center text-slate-400">
                Loading...
              </TableCell>
            </TableRow>
          )}
          {!isLoading && pageRows.length === 0 && (
            <TableRow>
              <TableCell colSpan={11} className="text-center text-slate-400">
                No common material codes match the current filters.
              </TableCell>
            </TableRow>
          )}
          {pageRows.map(({ code, cpses, originalCodesCount }) => (
            <TableRow key={code.id}>
              <TableCell>
                <Link to={`/common-material-master/${code.code}`} className="font-semibold text-brand-600 hover:underline">
                  {code.code}
                </Link>
              </TableCell>
              <TableCell className="max-w-xs truncate">{code.standard_description}</TableCell>
              <TableCell>{code.category}</TableCell>
              <TableCell>{code.uom}</TableCell>
              <TableCell>{cpses.join(", ") || "—"}</TableCell>
              <TableCell>{originalCodesCount}</TableCell>
              <TableCell>{code.confidence_score != null ? `${code.confidence_score.toFixed(1)}%` : "—"}</TableCell>
              <TableCell>
                <StatusBadge status={code.status} />
              </TableCell>
              <TableCell className="text-xs text-slate-500">{formatDate(code.created_at)}</TableCell>
              <TableCell className="text-xs text-slate-400">Not available</TableCell>
              <TableCell className="text-right">
                <Link
                  to={`/common-material-master/${code.code}`}
                  className="text-xs font-medium text-brand-600 hover:underline"
                >
                  View
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {filteredRows.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-sm text-slate-500">
          <p>
            Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredRows.length)} of{" "}
            {filteredRows.length} materials
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((n) => n === 1 || n === totalPages || Math.abs(n - currentPage) <= 1)
              .reduce<number[]>((acc, n) => {
                if (acc.length && n - acc[acc.length - 1] > 1) acc.push(-1);
                acc.push(n);
                return acc;
              }, [])
              .map((n, i) =>
                n === -1 ? (
                  <span key={`gap-${i}`} className="px-1 text-slate-400">
                    …
                  </span>
                ) : (
                  <button
                    key={n}
                    onClick={() => setPage(n)}
                    className={
                      "rounded border px-2.5 py-1 text-xs font-medium " +
                      (n === currentPage
                        ? "border-brand-600 bg-brand-600 text-white"
                        : "border-slate-300 hover:bg-slate-100")
                    }
                  >
                    {n}
                  </button>
                )
              )}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
