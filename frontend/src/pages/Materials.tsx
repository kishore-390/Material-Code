import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link } from "react-router-dom";

import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDebounce } from "@/hooks/useDebounce";
import { listMaterials } from "@/services/materials";

const CATEGORIES = [
  "Pipes", "Valves", "Bearings", "Lubricants", "Flanges", "Motors",
  "Pumps", "Cables", "Transformers", "Fasteners", "Gaskets", "Industrial Chemicals",
];
const STATUSES = ["PENDING", "PROCESSING", "ANALYZED", "HARMONIZED", "REJECTED", "FAILED"];

export default function Materials() {
  const [q, setQ] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [cpseId, setCpseId] = React.useState("");
  const [page, setPage] = React.useState(1);
  const pageSize = 15;
  const debouncedQ = useDebounce(q);

  const { data, isLoading } = useQuery({
    queryKey: ["materials", { q: debouncedQ, category, status, cpseId, page }],
    queryFn: () =>
      listMaterials({
        q: debouncedQ || undefined,
        category: category || undefined,
        status: status || undefined,
        cpse_id: cpseId || undefined,
        page,
        page_size: pageSize,
      }),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Material Management", to: "/materials" }, { label: "Materials" }]}
        title="Materials"
        subtitle={`${data?.total ?? 0} materials in the catalogue`}
      />

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search by code or description..."
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
        <Select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="max-w-[180px]"
        >
          <option value="">All Categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </Select>
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className="max-w-[180px]"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">Sl.No.</TableHead>
            <TableHead>Material Code</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>UOM</TableHead>
            <TableHead>CPSE</TableHead>
            <TableHead>Common Code</TableHead>
            <TableHead>Status</TableHead>
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
                No materials found.
              </TableCell>
            </TableRow>
          )}
          {data?.items.map((material, idx) => (
            <TableRow key={material.id}>
              <TableCell className="text-slate-400">{(page - 1) * pageSize + idx + 1}</TableCell>
              <TableCell>
                <Link to={`/materials/${material.id}`} className="font-medium text-brand-600 hover:underline">
                  {material.material_code}
                </Link>
              </TableCell>
              <TableCell className="max-w-xs truncate">{material.description}</TableCell>
              <TableCell>{material.category}</TableCell>
              <TableCell>{material.uom}</TableCell>
              <TableCell>{material.cpse.code}</TableCell>
              <TableCell>
                {material.common_code ? (
                  <Link to={`/common-material-master/${material.common_code.code}`} className="text-brand-600 hover:underline">
                    {material.common_code.code}
                  </Link>
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </TableCell>
              <TableCell>
                <StatusBadge status={material.status} />
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
