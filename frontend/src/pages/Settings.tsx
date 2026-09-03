import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

export default function Settings() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const [form, setForm] = React.useState<SystemSettings | null>(null);

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

  if (!form) return <p className="text-sm text-slate-400">Loading...</p>;

  const weightSum = WEIGHT_FIELDS.reduce((sum, f) => sum + Number(form[f.key] ?? 0), 0);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Admin Settings</h1>
        <p className="text-sm text-slate-500">
          Configure the decision thresholds and scoring weights used by the AI matching engine.
        </p>
      </div>

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
