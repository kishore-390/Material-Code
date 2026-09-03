import { useMutation } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import * as React from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { FileDropzone } from "@/components/FileDropzone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/services/api";
import { createMaterial, importBulkUpload, validateBulkUpload } from "@/services/materials";
import type { BulkValidationResponse } from "@/types";

const CATEGORIES = [
  "Pipes", "Valves", "Bearings", "Lubricants", "Flanges", "Motors",
  "Pumps", "Cables", "Transformers", "Fasteners", "Gaskets", "Industrial Chemicals",
];
const UOMS = ["Meter", "Kilogram", "Numbers", "Each", "Liter", "Set", "Roll", "Box", "Pair", "Ton"];

export default function MaterialUpload() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = React.useState({
    material_code: "",
    description: "",
    specification: "",
    category: CATEGORIES[0],
    uom: UOMS[0],
    cpse_code: user?.cpse?.code ?? "",
    manufacturer: "",
    brand: "",
    material_type: "",
  });
  const [attributes, setAttributes] = React.useState<{ key: string; value: string }[]>([]);
  const [image, setImage] = React.useState<File | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      createMaterial({
        ...form,
        attributes: Object.fromEntries(attributes.filter((a) => a.key).map((a) => [a.key, a.value])),
        image,
      }),
    onSuccess: (material) => navigate(`/materials/${material.id}/analysis`),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate();
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Upload Material</h1>
        <p className="text-sm text-slate-500">
          Add a single material or bulk-import a CSV / Excel file. Every material is automatically
          queued for AI analysis after upload.
        </p>
      </div>

      <Tabs defaultValue="single">
        <TabsList>
          <TabsTrigger value="single">Single Upload</TabsTrigger>
          <TabsTrigger value="bulk">Bulk Upload (CSV / Excel)</TabsTrigger>
        </TabsList>

        <TabsContent value="single">
          <Card>
            <CardContent className="pt-6">
              <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Material Code *</Label>
                  <Input
                    required
                    value={form.material_code}
                    onChange={(e) => setForm({ ...form, material_code: e.target.value })}
                    placeholder="e.g. IOCL-PIP-1023"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>CPSE Organization *</Label>
                  <Input
                    required
                    disabled={user?.role.name === "CPSE_USER"}
                    value={form.cpse_code}
                    onChange={(e) => setForm({ ...form, cpse_code: e.target.value.toUpperCase() })}
                    placeholder="e.g. IOCL"
                  />
                </div>
                <div className="space-y-1.5 md:col-span-2">
                  <Label>Material Description *</Label>
                  <Input
                    required
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    placeholder="e.g. Carbon Steel Seamless Pipe"
                  />
                </div>
                <div className="space-y-1.5 md:col-span-2">
                  <Label>Detailed Specification</Label>
                  <Textarea
                    value={form.specification}
                    onChange={(e) => setForm({ ...form, specification: e.target.value })}
                    placeholder="e.g. ASTM A106 Grade B, 4 inch"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Category *</Label>
                  <Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Unit of Measurement *</Label>
                  <Select value={form.uom} onChange={(e) => setForm({ ...form, uom: e.target.value })}>
                    {UOMS.map((u) => (
                      <option key={u} value={u}>
                        {u}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Manufacturer</Label>
                  <Input
                    value={form.manufacturer}
                    onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Brand</Label>
                  <Input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label>Material Type</Label>
                  <Input
                    value={form.material_type}
                    onChange={(e) => setForm({ ...form, material_type: e.target.value })}
                    placeholder="e.g. Carbon Steel"
                  />
                </div>

                <div className="md:col-span-2">
                  <div className="mb-2 flex items-center justify-between">
                    <Label>Additional Attributes</Label>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setAttributes([...attributes, { key: "", value: "" }])}
                    >
                      <Plus className="h-3.5 w-3.5" /> Add Attribute
                    </Button>
                  </div>
                  <div className="space-y-2">
                    {attributes.map((attr, idx) => (
                      <div key={idx} className="flex gap-2">
                        <Input
                          placeholder="Attribute name (e.g. Schedule)"
                          value={attr.key}
                          onChange={(e) => {
                            const next = [...attributes];
                            next[idx] = { ...next[idx], key: e.target.value };
                            setAttributes(next);
                          }}
                        />
                        <Input
                          placeholder="Value (e.g. SCH 40)"
                          value={attr.value}
                          onChange={(e) => {
                            const next = [...attributes];
                            next[idx] = { ...next[idx], value: e.target.value };
                            setAttributes(next);
                          }}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => setAttributes(attributes.filter((_, i) => i !== idx))}
                        >
                          <Trash2 className="h-4 w-4 text-danger-500" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="md:col-span-2 space-y-1.5">
                  <Label>Material Image</Label>
                  <FileDropzone
                    accept="image/*"
                    label="Click or drag an image here"
                    hint="JPG, PNG or WEBP up to 15 MB"
                    selectedFileName={image?.name}
                    onFileSelected={setImage}
                  />
                </div>

                {createMutation.isError && (
                  <p className="md:col-span-2 text-sm text-danger-600">
                    {apiErrorMessage(createMutation.error)}
                  </p>
                )}

                <div className="md:col-span-2 flex justify-end gap-2">
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Uploading..." : "Upload & Run AI Analysis"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="bulk">
          <BulkUploadPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function BulkUploadPanel() {
  const [file, setFile] = React.useState<File | null>(null);
  const [validation, setValidation] = React.useState<BulkValidationResponse | null>(null);
  const [importSummary, setImportSummary] = React.useState<{
    total_uploaded: number;
    successfully_imported: number;
    validation_errors: number;
    queued_for_ai: number;
  } | null>(null);

  const validateMutation = useMutation({
    mutationFn: (f: File) => validateBulkUpload(f),
    onSuccess: (data) => setValidation(data),
  });

  const importMutation = useMutation({
    mutationFn: (batchToken: string) => importBulkUpload(batchToken),
    onSuccess: (data) => {
      setImportSummary(data);
      setValidation(null);
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Step 1 - Upload File</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-slate-500">
            Required columns: material_code, description, specification, category, uom, cpse, manufacturer, brand,
            material_type, image
          </p>
          <FileDropzone
            accept=".csv,.xlsx,.xls"
            label="Click or drag a CSV / Excel file here"
            selectedFileName={file?.name}
            onFileSelected={(f) => {
              setFile(f);
              setValidation(null);
              setImportSummary(null);
            }}
          />
          <Button disabled={!file || validateMutation.isPending} onClick={() => file && validateMutation.mutate(file)}>
            {validateMutation.isPending ? "Validating..." : "Validate File"}
          </Button>
          {validateMutation.isError && (
            <p className="text-sm text-danger-600">{apiErrorMessage(validateMutation.error)}</p>
          )}
        </CardContent>
      </Card>

      {validation && (
        <Card>
          <CardHeader>
            <CardTitle>Step 2 - Review & Confirm</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Badge variant="outline">Total rows: {validation.total_rows}</Badge>
              <Badge variant="success">Valid: {validation.valid_rows}</Badge>
              <Badge variant="danger">Errors: {validation.invalid_rows}</Badge>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Material Code</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>CPSE</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {validation.rows.slice(0, 50).map((row) => (
                  <TableRow key={row.row_number}>
                    <TableCell>{row.row_number}</TableCell>
                    <TableCell>{row.data.material_code || "—"}</TableCell>
                    <TableCell className="max-w-xs truncate">{row.data.description || "—"}</TableCell>
                    <TableCell>{row.data.cpse || "—"}</TableCell>
                    <TableCell>
                      {row.is_valid ? (
                        <Badge variant="success">Valid</Badge>
                      ) : (
                        <span className="text-xs text-danger-600">{row.errors.join("; ")}</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="flex justify-end">
              <Button
                disabled={validation.valid_rows === 0 || importMutation.isPending}
                onClick={() => importMutation.mutate(validation.batch_token)}
              >
                {importMutation.isPending ? "Importing..." : `Confirm Import (${validation.valid_rows} rows)`}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {importSummary && (
        <Card>
          <CardHeader>
            <CardTitle>Step 3 - Import Results</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <SummaryStat label="Total uploaded" value={importSummary.total_uploaded} />
            <SummaryStat label="Successfully imported" value={importSummary.successfully_imported} tone="success" />
            <SummaryStat label="Validation errors" value={importSummary.validation_errors} tone="danger" />
            <SummaryStat label="Queued for AI" value={importSummary.queued_for_ai} tone="brand" />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function SummaryStat({ label, value, tone = "default" }: { label: string; value: number; tone?: "default" | "success" | "danger" | "brand" }) {
  const colors: Record<string, string> = {
    default: "text-slate-900",
    success: "text-success-600",
    danger: "text-danger-600",
    brand: "text-brand-600",
  };
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`text-2xl font-bold ${colors[tone]}`}>{value}</p>
    </div>
  );
}
