import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAccessibilitySettings } from "@/hooks/useAccessibilitySettings";
import { apiErrorMessage } from "@/services/api";
import { getSettings, updateSettings } from "@/services/settings";
import type { SystemSettings } from "@/types";

const THRESHOLD_FIELDS: { key: keyof SystemSettings; label: string }[] = [
  { key: "threshold_auto", label: "Auto Harmonization Threshold (%)" },
  { key: "threshold_review", label: "Human Review Threshold (%)" },
  { key: "threshold_low", label: "Low Confidence Threshold (%)" },
];

const WEIGHT_FIELDS: { key: keyof SystemSettings; label: string }[] = [
  { key: "weight_description", label: "Description Weight" },
  { key: "weight_specification", label: "Specification Weight" },
  { key: "weight_category", label: "Category Weight" },
  { key: "weight_uom", label: "UOM Weight" },
  { key: "weight_image", label: "Image Weight" },
  { key: "weight_attributes", label: "Attributes Weight" },
];

const AUTO_MAP_STORAGE_KEY = "app-auto-map-policy";

export default function Settings() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const [form, setForm] = React.useState<SystemSettings | null>(null);
  const { decreaseFont, resetFont, increaseFont, language, setLanguage } = useAccessibilitySettings();
  const [autoMapPolicy, setAutoMapPolicy] = React.useState(() => localStorage.getItem(AUTO_MAP_STORAGE_KEY) !== "false");

  React.useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  const mutation = useMutation({
    mutationFn: (payload: Partial<SystemSettings>) => updateSettings(payload),
    onSuccess: (updated) => {
      setForm(updated);
      queryClient.setQueryData(["settings"], updated);
    },
  });

  function toggleAutoMapPolicy() {
    const next = !autoMapPolicy;
    setAutoMapPolicy(next);
    localStorage.setItem(AUTO_MAP_STORAGE_KEY, String(next));
  }

  if (!form) return <p className="text-sm text-slate-400">Loading...</p>;

  const weightSum = WEIGHT_FIELDS.reduce((sum, f) => sum + Number(form[f.key] ?? 0), 0);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        breadcrumbs={[{ label: "System", to: "/settings" }, { label: "Settings" }]}
        title="Admin Settings"
        subtitle="Configure the decision thresholds and scoring weights used by the AI matching engine, plus accessibility and display preferences."
      />

      <Card>
        <CardHeader>
          <CardTitle>Accessibility &amp; Display</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Font Size</Label>
            <div className="flex items-center rounded border border-slate-300 text-slate-600">
              <button onClick={decreaseFont} className="flex h-8 w-8 items-center justify-center border-r border-slate-300 hover:bg-slate-100">−</button>
              <button onClick={resetFont} className="flex h-8 items-center px-3 text-xs font-semibold hover:bg-slate-100">Reset</button>
              <button onClick={increaseFont} className="flex h-8 w-8 items-center justify-center border-l border-slate-300 hover:bg-slate-100">+</button>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <Label>Language</Label>
            <div className="flex items-center overflow-hidden rounded border border-slate-300 text-xs font-medium">
              <button
                onClick={() => setLanguage("EN")}
                className={"px-3 py-1.5 " + (language === "EN" ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-100")}
              >
                English
              </button>
              <button
                onClick={() => setLanguage("HI")}
                className={"border-l border-slate-300 px-3 py-1.5 " + (language === "HI" ? "bg-brand-600 text-white" : "bg-white text-slate-600 hover:bg-slate-100")}
              >
                हिंदी
              </button>
            </div>
          </div>
          <p className="text-xs text-slate-400">
            These preferences are saved locally to this browser and mirror the controls in the top header.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Decision Thresholds</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {THRESHOLD_FIELDS.map((f) => (
            <div key={f.key} className="space-y-1.5">
              <Label>{f.label}</Label>
              <Input
                type="number"
                step="0.1"
                value={form[f.key]}
                onChange={(e) => setForm({ ...form, [f.key]: Number(e.target.value) })}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Similarity Scoring Weights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {WEIGHT_FIELDS.map((f) => (
              <div key={f.key} className="space-y-1.5">
                <Label>{f.label}</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={form[f.key]}
                  onChange={(e) => setForm({ ...form, [f.key]: Number(e.target.value) })}
                />
              </div>
            ))}
          </div>
          <p className={`mt-3 text-xs ${Math.abs(weightSum - 1) < 0.01 ? "text-success-600" : "text-warning-600"}`}>
            Weights sum to {weightSum.toFixed(2)} (should equal 1.00)
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Auto-Mapping Policy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-700">Allow AI to auto-map at or above the Auto Harmonization Threshold</p>
              <p className="text-xs text-slate-500">
                Currently a display preference only — it does not change the decision engine's behavior
                (that is always governed by the Decision Thresholds above).
              </p>
            </div>
            <button
              onClick={toggleAutoMapPolicy}
              className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${autoMapPolicy ? "bg-brand-600" : "bg-slate-300"}`}
            >
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${autoMapPolicy ? "translate-x-5" : "translate-x-0.5"}`} />
            </button>
          </div>
          <Badge variant="outline">UI Preference Only — Not Wired to Backend Enforcement</Badge>
        </CardContent>
      </Card>

      {mutation.isError && <p className="text-sm text-danger-600">{apiErrorMessage(mutation.error)}</p>}
      {mutation.isSuccess && <p className="text-sm text-success-600">Settings saved.</p>}

      <div className="flex justify-end">
        <Button onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
          {mutation.isPending ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </div>
  );
}
