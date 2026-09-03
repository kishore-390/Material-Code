import { UploadCloud } from "lucide-react";
import * as React from "react";

import { cn } from "@/utils/cn";

interface FileDropzoneProps {
  accept?: string;
  onFileSelected: (file: File) => void;
  label: string;
  hint?: string;
  selectedFileName?: string | null;
}

export function FileDropzone({ accept, onFileSelected, label, hint, selectedFileName }: FileDropzoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [isDragActive, setIsDragActive] = React.useState(false);

  const handleFiles = (files: FileList | null) => {
    if (files && files[0]) onFileSelected(files[0]);
  };

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragActive(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors",
        isDragActive ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100"
      )}
    >
      <UploadCloud className="h-8 w-8 text-slate-400" />
      <p className="text-sm font-medium text-slate-700">{selectedFileName || label}</p>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
