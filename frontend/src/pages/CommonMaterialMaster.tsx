import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getCommonCode, listCommonCodes } from "@/services/commonCodes";

export default function CommonMaterialMaster() {
  const { data: codes, isLoading } = useQuery({ queryKey: ["common-codes"], queryFn: listCommonCodes });

  const detailQueries = useQueries({
    queries: (codes ?? []).map((c) => ({
      queryKey: ["common-code", c.code],
      queryFn: () => getCommonCode(c.code),
      enabled: !!codes,
    })),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Common Material Master</h1>
        <p className="text-sm text-slate-500">The single source of truth for harmonized materials across CPSEs.</p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Common Code</TableHead>
            <TableHead>Standard Description</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>UOM</TableHead>
            <TableHead>Linked CPSEs</TableHead>
            <TableHead>Original Codes</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-slate-400">Loading...</TableCell>
            </TableRow>
          )}
          {!isLoading && (codes ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="text-center text-slate-400">
                No common material codes generated yet.
              </TableCell>
            </TableRow>
          )}
          {codes?.map((code, idx) => {
            const detail = detailQueries[idx]?.data;
            const cpses = detail?.linked_cpses ?? [];
            const originalCodesCount = detail?.linked_materials.length ?? 0;
            return (
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
                <TableCell>
                  <StatusBadge status={code.status} />
                </TableCell>
                <TableCell className="text-xs text-slate-500">{new Date(code.created_at).toLocaleDateString()}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
