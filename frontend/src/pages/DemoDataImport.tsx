import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Download, FileUp, History, UploadCloud } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiErrorMessage } from "@/services/api";
import { confirmDemoCsvImport, downloadSampleCsv, getDemoImportHistory, validateDemoCsv } from "@/services/demoImport";
import type { CsvImportHistoryItem, CsvImportResponse, CsvValidationResponse } from "@/types";

const OUTCOME_VARIANT: Record<string, "success" | "brand" | "outline" | "danger"> = {
  created: "success",
  updated: "brand",
  skipped: "outline",
  failed: "danger",
};

export default function DemoDataImport() {
  const [file, setFile] = React.useState<File | null>(null);
  const [validation, setValidation] = React.useState<CsvValidationResponse | null>(null);
  const [result, setResult] = React.useState<CsvImportResponse | null>(null);

  const historyQuery = useQuery({ queryKey: ["demo-import-history"], queryFn: getDemoImportHistory });

  const validateMutation = useMutation({
    mutationFn: (f: File) => validateDemoCsv(f),
    onSuccess: (data) => {
      setValidation(data);
      setResult(null);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: (f: File) => confirmDemoCsvImport(f),
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
        breadcrumbs={[{ label: "CPSE Network", to: "/cpse" }, { label: "Demo Data Import" }]}
        title="Demo Data Import"
        subtitle="This CSV import is provided only for demonstration/testing. Production CPSE material data is synchronized automatically through secure read-only database connectors."
        actions={<Badge variant="warning">DEMO ONLY</Badge>}
      />

      <Card className="border-warning-600/30 bg-warning-50">
        <CardContent className="flex gap-3 p-4 text-sm text-warning-800">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Not a production ingestion path.</p>
            <p className="mt-1 text-warning-700">
              Every row imported here is permanently marked as demo data and passes through the exact same AI
              harmonization pipeline as a real database sync. It can only target CPSEs already onboarded under{" "}
              <span className="font-medium">Participating CPSEs</span> - it never creates new CPSE organizations, and
              it can never overwrite real production material data.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-slate-300 px-4 py-3 text-sm text-slate-600 hover:bg-slate-50">
              <UploadCloud className="h-4 w-4" />
              {file ? file.name : "Choose a CSV file..."}
              <input type="file" accept=".csv" className="hidden" onChange={onFileChange} />
            </label>
            <Button variant="outline" size="sm" onClick={() => downloadSampleCsv()}>
              <Download className="h-3.5 w-3.5" /> Download Sample CSV
            </Button>
          </div>

          {validateMutation.isPending && <p className="text-sm text-slate-400">Validating...</p>}
          {validateMutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(validateMutation.error)}</p>}

          {validation && <ValidationSummary validation={validation} />}

          {validation?.is_importable && !result && (
            <Button onClick={() => file && confirmMutation.mutate(file)} disabled={confirmMutation.isPending}>
              <FileUp className="h-4 w-4" />
              {confirmMutation.isPending ? "Importing..." : `Confirm Import (${validation.valid_count} rows)`}
            </Button>
          )}
          {confirmMutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(confirmMutation.error)}</p>}

          {result && <ImportResult result={result} />}
        </CardContent>
      </Card>

      <ImportHistory items={historyQuery.data?.items ?? []} isLoading={historyQuery.isLoading} />
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

function ImportResult({ result }: { result: CsvImportResponse }) {
  return (
    <div className="space-y-3 rounded-md border border-success-600/30 bg-success-50 p-3">
      <p className="text-sm font-semibold text-success-800">
        Import complete - {result.created} created, {result.updated} updated, {result.skipped} skipped,{" "}
        {result.failed} failed.
      </p>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Row</TableHead>
              <TableHead>CPSE</TableHead>
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
                <TableCell>{row.cpse_code}</TableCell>
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

function ImportHistory({ items, isLoading }: { items: CsvImportHistoryItem[]; isLoading: boolean }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <History className="h-4 w-4" /> Import History
        </p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Imported At</TableHead>
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
                  No demo CSV imports yet.
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
