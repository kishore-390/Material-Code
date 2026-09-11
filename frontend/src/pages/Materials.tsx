import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";

import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDebounce } from "@/hooks/useDebounce";
import { listMaterials } from "@/services/materials";

const STATUSES = ["PENDING", "PROCESSING", "ANALYZED", "HARMONIZED", "FAILED"];

export default function Materials() {
  const [searchParams] = useSearchParams();
  const forcedCpseOnly = searchParams.get("scope") === "cpse";

  const [q, setQ] = React.useState("");
  const [classification, setClassification] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [cpseId, setCpseId] = React.useState("");
  const [page, setPage] = React.useState(1);
  const pageSize = 15;
  const debouncedQ = useDebounce(q);

  const { data, isLoading } = useQuery({
    queryKey: ["materials", { q: debouncedQ, classification, status, cpseId, page }],
    queryFn: () =>
      listMaterials({
        q: debouncedQ || undefined,
        classification: classification || undefined,
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
        breadcrumbs={[{ label: "Material Master" }, { label: forcedCpseOnly ? "CPSE Materials" : "All Materials" }]}
        title={forcedCpseOnly ? "CPSE Materials" : "All Materials"}
        subtitle={`${data?.total ?? 0} materials synchronized from participating CPSE source systems`}
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
        <Input
          placeholder="Classification..."
          value={classification}
          onChange={(e) => {
            setClassification(e.target.value);
            setPage(1);
          }}
          className="max-w-[180px]"
        />
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
            <TableHead>Original Material Code</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Classification</TableHead>
            <TableHead>UOM</TableHead>
            <TableHead>CPSE</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-slate-400">
                Loading...
              </TableCell>
            </TableRow>
          )}
          {!isLoading && (data?.items.length ?? 0) === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-slate-400">
                No materials found. Materials only appear here once a CPSE's data has been synchronized.
              </TableCell>
            </TableRow>
          )}
          {data?.items.map((material, idx) => (
            <TableRow key={material.id}>
              <TableCell className="text-slate-400">{(page - 1) * pageSize + idx + 1}</TableCell>
              <TableCell>
                <Link to={`/materials/${material.id}`} className="font-medium text-brand-600 hover:underline">
                  {material.original_material_code}
                </Link>
              </TableCell>
              <TableCell className="max-w-xs truncate">{material.original_description}</TableCell>
              <TableCell>{material.classification}</TableCell>
              <TableCell>{material.uom}</TableCell>
              <TableCell>{material.cpse.code}</TableCell>
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
