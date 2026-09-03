import { useQuery } from "@tanstack/react-query";
import { Search as SearchIcon } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDebounce } from "@/hooks/useDebounce";
import { searchMaterials } from "@/services/materials";

export default function MaterialSearch() {
  const [q, setQ] = React.useState("");
  const debouncedQ = useDebounce(q, 400);

  const { data, isFetching } = useQuery({
    queryKey: ["materials", "search", debouncedQ],
    queryFn: () => searchMaterials(debouncedQ),
    enabled: debouncedQ.trim().length > 1,
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Intelligent Material Search</h1>
        <p className="text-sm text-slate-500">
          Search by material code, description, specification, category or UOM. Results are ranked using
          semantic (pgvector) similarity alongside exact matches.
        </p>
      </div>

      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          className="pl-9"
          placeholder='e.g. "carbon steel seamless pipe"'
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoFocus
        />
      </div>

      {debouncedQ.trim().length > 1 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Material</TableHead>
              <TableHead>CPSE</TableHead>
              <TableHead>Similarity</TableHead>
              <TableHead>Common Code</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isFetching && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-slate-400">
                  Searching...
                </TableCell>
              </TableRow>
            )}
            {!isFetching && (data ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-slate-400">
                  No matches found.
                </TableCell>
              </TableRow>
            )}
            {data?.map((item) => (
              <TableRow key={item.material.id}>
                <TableCell>
                  <Link to={`/materials/${item.material.id}`} className="font-medium text-brand-600 hover:underline">
                    {item.material.material_code}
                  </Link>
                  <p className="text-xs text-slate-400">{item.material.description}</p>
                </TableCell>
                <TableCell>{item.material.cpse.code}</TableCell>
                <TableCell className="font-semibold">{item.similarity.toFixed(1)}%</TableCell>
                <TableCell>{item.material.common_code?.code ?? "—"}</TableCell>
                <TableCell>
                  <StatusBadge status={item.material.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
