import { useState } from "react";
import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { exportExcel, exportJson, exportPdf, type ExportDocument } from "@/lib/exporters";

interface ExportMenuProps {
  fileName: string;
  /** Builds the tabular document lazily so large payloads are only converted on demand. */
  buildDocument: () => ExportDocument;
  /** Raw payload written to JSON. */
  jsonData: unknown;
  disabled?: boolean;
}

export function ExportMenu({ fileName, buildDocument, jsonData, disabled }: ExportMenuProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (kind: "json" | "excel" | "pdf") => {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "json") exportJson(fileName, jsonData);
      else if (kind === "excel") await exportExcel(fileName, buildDocument());
      else await exportPdf(fileName, buildDocument());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2 no-print" role="group" aria-label="Export">
      <Download className="size-4 text-muted-foreground" aria-hidden="true" />
      <Button variant="outline" size="sm" onClick={() => run("json")} disabled={disabled || busy !== null}>
        <FileJson aria-hidden="true" /> JSON
      </Button>
      <Button variant="outline" size="sm" onClick={() => run("excel")} disabled={disabled || busy !== null}>
        <FileSpreadsheet aria-hidden="true" /> {busy === "excel" ? "Exporting..." : "Excel"}
      </Button>
      <Button variant="outline" size="sm" onClick={() => run("pdf")} disabled={disabled || busy !== null}>
        <FileText aria-hidden="true" /> {busy === "pdf" ? "Exporting..." : "PDF"}
      </Button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}
