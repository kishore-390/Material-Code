import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileUp, History, UploadCloud } from "lucide-react";
import * as React from "react";

import { useAuth } from "@/auth/AuthContext";
import { OrganizationSelect } from "@/components/OrganizationSelect";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiErrorMessage } from "@/services/api";
import {
  confirmMaterialUpload,
  downloadUploadTemplate,
  getMaterialUploadHistory,
  validateMaterialUpload,
} from "@/services/materialUpload";
import type { CsvImportHistoryItem, CsvImportResponse, CsvValidationResponse } from "@/types";

const OUTCOME_VARIANT: Record<string, "success" | "brand" | "outline" | "danger"> = {
  created: "success",
  updated: "brand",
  skipped: "outline",
  failed: "danger",
};

export default function MaterialUpload() {
  const { user } = useAuth();
  const isCentralUser = !user?.cpse;

  const [file, setFile] = React.useState<File | null>(null);
  const [cpseId, setCpseId] = React.useState("");
  const [validation, setValidation] = React.useState<CsvValidationResponse | null>(null);
  const [result, setResult] = React.useState<CsvImportResponse | null>(null);

  const historyQuery = useQuery({ queryKey: ["material-upload-history"], queryFn: getMaterialUploadHistory });

  const validateMutation = useMutation({
    mutationFn: (f: File) => validateMaterialUpload(f, isCentralUser ? cpseId : undefined),
    onSuccess: (data) => {
      setValidation(data);
      setResult(null);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: (f: File) => confirmMaterialUpload(f, isCentralUser ? cpseId : undefined),
    onSuccess: (data) => {
      setResult(data);
      historyQuery.refetch();
    },
  });

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setValidation(null);
    setResult(null);
    if (selected) validateMutation.mutate(selected);
  };

  return (
    <div className="space-y-4">
      <PageHeader
        breadcrumbs={[{ label: "Material Master", to: "/materials" }, { label: "Upload Materials" }]}
        title="Upload Materials"
        subtitle={
          user?.cpse
            ? `Upload your company's own real material master (CSV or Excel) for ${user.cpse.name}. Rows are permanent production data, not a demo - they flow through the same AI harmonization pipeline as an automatic database sync.`
            : "Upload a CPSE's real material master (CSV or Excel) on their behalf. Rows are permanent production data, not a demo."
        }
      />

      <Card>
        <CardContent className="space-y-4 p-4">
          {isCentralUser && (
            <div className="max-w-sm space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Uploading For</label>
              <OrganizationSelect value={cpseId} onChange={(e) => setCpseId(e.target.value)} includeInactive={false} />
            </div>
          )}
          {!isCentralUser && user?.cpse && (
            <p className="text-sm text-slate-600">
              Uploading for <span className="font-semibold">{user.cpse.name}</span> ({user.cpse.code}) - you can only
              upload materials for your own company.
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-slate-300 px-4 py-3 text-sm text-slate-600 hover:bg-slate-50">
              <UploadCloud className="h-4 w-4" />
              {file ? file.name : "Choose a CSV or Excel file..."}
              <input type="file" accept=".csv,.xlsx" className="hidden" onChange={onFileChange} disabled={isCentralUser && !cpseId} />
            </label>
            <Button variant="outline" size="sm" onClick={() => downloadUploadTemplate()}>
              <Download className="h-3.5 w-3.5" /> Download Template
            </Button>
          </div>

          {validateMutation.isPending && <p className="text-sm text-slate-400">Validating...</p>}
          {validateMutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(validateMutation.error)}</p>}

          {validation && <ValidationSummary validation={validation} />}

          {validation?.is_importable && !result && (
            <Button onClick={() => file && confirmMutation.mutate(file)} disabled={confirmMutation.isPending}>
              <FileUp className="h-4 w-4" />
              {confirmMutation.isPending ? "Uploading..." : `Confirm Upload (${validation.valid_count} rows)`}
            </Button>
          )}
          {confirmMutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(confirmMutation.error)}</p>}

          {result && <UploadResult result={result} />}
        </CardContent>
      </Card>

      <UploadHistory items={historyQuery.data?.items ?? []} isLoading={historyQuery.isLoading} />
    </div>
  );
}

function ValidationSummary({ validation }: { validation: CsvValidationResponse }) {
  return (
    <div className="space-y-3 rounded-md border border-slate-200 p-3">
      <div className="flex flex-wrap gap-4 text-sm">
        <span>
          Total rows: <span className="font-semibold">{validation.total_rows}</span>
        </span>
        <span className="text-success-600">
          Valid: <span className="font-semibold">{validation.valid_count}</span>
        </span>
        <span className="text-danger-600">
          Invalid: <span className="font-semibold">{validation.invalid_count}</span>
        </span>
      </div>

      {validation.file_errors.length > 0 && (
        <div className="space-y-1 rounded-md bg-danger-50 p-3 text-sm text-danger-700">
          {validation.file_errors.map((err, i) => (
            <p key={i}>{err}</p>
          ))}
        </div>
      )}

      {validation.invalid_rows.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Invalid Rows</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Row</TableHead>
                <TableHead>CPSE</TableHead>
                <TableHead>Material Code</TableHead>
                <TableHead>Errors</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {validation.invalid_rows.map((row) => (
                <TableRow key={row.row_number}>
                  <TableCell>{row.row_number}</TableCell>
                  <TableCell>{row.cpse_code}</TableCell>
                  <TableCell className="font-mono text-xs">{row.original_material_code}</TableCell>
                  <TableCell className="text-xs text-danger-600">{row.errors.join("; ")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {validation.preview.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Preview (first {validation.preview.length} valid rows)
          </p>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>CPSE</TableHead>
                  <TableHead>Material Code</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>UOM</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {validation.preview.map((row, i) => (
                  <TableRow key={i}>
                    <TableCell>{row.cpse_code}</TableCell>
                    <TableCell className="font-mono text-xs">{row.original_material_code}</TableCell>
                    <TableCell>{row.original_description}</TableCell>
                    <TableCell>{row.uom}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}

function UploadResult({ result }: { result: CsvImportResponse }) {
  return (
    <div className="space-y-3 rounded-md border border-success-600/30 bg-success-50 p-3">
      <p className="text-sm font-semibold text-success-800">
        Upload complete - {result.created} created, {result.updated} updated, {result.skipped} skipped,{" "}
        {result.failed} failed.
      </p>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Row</TableHead>
              <TableHead>Material Code</TableHead>
              <TableHead>Outcome</TableHead>
              <TableHead>Common Code</TableHead>
              <TableHead>Mapping Type</TableHead>
              <TableHead>Decision Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.results.map((row) => (
              <TableRow key={row.row_number}>
                <TableCell>{row.row_number}</TableCell>
                <TableCell className="font-mono text-xs">{row.original_material_code}</TableCell>
                <TableCell>
                  <Badge variant={OUTCOME_VARIANT[row.outcome] ?? "outline"}>{row.outcome.toUpperCase()}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{row.common_material_code ?? "-"}</TableCell>
                <TableCell className="text-xs">{row.mapping_type ?? "-"}</TableCell>
                <TableCell className="text-xs">{row.decision_status ?? "-"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function UploadHistory({ items, isLoading }: { items: CsvImportHistoryItem[]; isLoading: boolean }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <History className="h-4 w-4" /> Upload History
        </p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Uploaded At</TableHead>
              <TableHead>By</TableHead>
              <TableHead>Rows</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead>Skipped</TableHead>
              <TableHead>Failed</TableHead>
              <TableHead>Invalid</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-slate-400">
                  Loading...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && items.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-slate-400">
                  No uploads yet.
                </TableCell>
              </TableRow>
            )}
            {items.map((item) => (
              <TableRow key={item.batch_id}>
                <TableCell className="font-mono text-xs">{item.filename}</TableCell>
                <TableCell className="text-xs">{new Date(item.imported_at).toLocaleString()}</TableCell>
                <TableCell className="text-xs">{item.actor_name}</TableCell>
                <TableCell className="tabular-nums">{item.total_rows}</TableCell>
                <TableCell className="tabular-nums text-success-600">{item.created}</TableCell>
                <TableCell className="tabular-nums text-brand-600">{item.updated}</TableCell>
                <TableCell className="tabular-nums text-slate-400">{item.skipped}</TableCell>
                <TableCell className="tabular-nums text-danger-600">{item.failed}</TableCell>
                <TableCell className="tabular-nums text-danger-600">{item.invalid_count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
