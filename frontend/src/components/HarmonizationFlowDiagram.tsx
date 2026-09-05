import { ArrowRight } from "lucide-react";

interface HarmonizationFlowDiagramProps {
  cpseCodes?: string[];
}

export function HarmonizationFlowDiagram({ cpseCodes = ["IOCL", "ONGC", "BPCL", "HPCL"] }: HarmonizationFlowDiagramProps) {
  return (
    <div className="flex flex-col items-stretch gap-3 rounded border border-slate-300 bg-slate-50 p-4 lg:flex-row lg:items-center lg:justify-center">
      <div className="rounded border border-slate-300 bg-white px-4 py-3 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Multiple CPSE Codes</p>
        {cpseCodes.map((code) => (
          <p key={code} className="mt-1 font-mono text-xs text-slate-700">
            {code}-xxxxx
          </p>
        ))}
      </div>
      <ArrowRight className="mx-auto h-5 w-5 shrink-0 rotate-90 text-slate-400 lg:rotate-0" />
      <div className="rounded border border-brand-100 bg-brand-50 px-4 py-3 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-700">AI Engine</p>
        <p className="mt-1 text-xs text-slate-700">SBERT → pgvector → XGBoost</p>
        <p className="text-xs text-slate-700">Equivalence &amp; Conflict Detection</p>
      </div>
      <ArrowRight className="mx-auto h-5 w-5 shrink-0 rotate-90 text-slate-400 lg:rotate-0" />
      <div className="rounded border border-success-600/30 bg-success-50 px-4 py-3 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-success-700">One Common Code</p>
        <p className="mt-1 font-mono text-sm font-bold text-success-700">CM-XXXXXX</p>
      </div>
      <ArrowRight className="mx-auto h-5 w-5 shrink-0 rotate-90 text-slate-400 lg:rotate-0" />
      <div className="rounded border border-slate-300 bg-white px-4 py-3 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Common Material Master</p>
        <p className="mt-1 text-xs text-slate-700">National authoritative record</p>
      </div>
    </div>
  );
}
