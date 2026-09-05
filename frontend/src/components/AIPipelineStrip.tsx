const STAGES = [
  "Data Ingestion",
  "Data Normalization",
  "Specification Extraction",
  "SBERT Embedding",
  "pgvector Candidate Search",
  "XGBoost Classification",
  "Human Validation",
];

export function AIPipelineStrip() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {STAGES.map((stage, idx) => (
        <div key={stage} className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded border border-slate-300 bg-slate-50 px-3 py-1.5">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white">
              {idx + 1}
            </span>
            <span className="text-xs font-medium text-slate-700">{stage}</span>
          </div>
          {idx < STAGES.length - 1 && <span className="text-slate-300">→</span>}
        </div>
      ))}
    </div>
  );
}
