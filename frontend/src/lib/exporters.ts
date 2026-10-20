// exceljs and jspdf are large, so they are loaded on demand when a user actually exports.

export type Cell = string | number | boolean | null | undefined;

/** Intermediate table used by every exporter. */
export interface ExportTable {
  name: string;
  columns: string[];
  rows: Cell[][];
}

export interface ExportDocument {
  title: string;
  subtitle?: string;
  generatedAt?: string;
  tables: ExportTable[];
}

export function safeFileName(value: string): string {
  return value.replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^_+|_+$/g, "") || "export";
}

export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Defer revoke so the browser has started the download.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function exportJson(fileName: string, data: unknown): void {
  const json = JSON.stringify(data, null, 2);
  downloadBlob(new Blob([json], { type: "application/json" }), `${safeFileName(fileName)}.json`);
}

export async function exportExcel(fileName: string, doc: ExportDocument): Promise<void> {
  const ExcelJS = (await import("exceljs")).default;
  const workbook = new ExcelJS.Workbook();
  workbook.creator = "USERSTORYAI";
  workbook.created = new Date();
  const usedNames = new Set<string>();

  for (const table of doc.tables) {
    // Excel sheet names: max 31 characters, no []:*?/\ characters, unique.
    let sheetName = table.name.replace(/[[\]:*?/\\]/g, " ").slice(0, 31) || "Sheet";
    let suffix = 2;
    while (usedNames.has(sheetName)) {
      sheetName = `${table.name.slice(0, 28)} ${suffix}`;
      suffix += 1;
    }
    usedNames.add(sheetName);

    const sheet = workbook.addWorksheet(sheetName);
    const header = sheet.addRow(table.columns);
    header.font = { bold: true };
    sheet.views = [{ state: "frozen", ySplit: 1 }];
    for (const row of table.rows) {
      sheet.addRow(row.map((cell) => (cell === undefined ? null : cell)));
    }
    table.columns.forEach((column, index) => {
      sheet.getColumn(index + 1).width = Math.min(60, Math.max(12, column.length + 4));
    });
  }

  const buffer = await workbook.xlsx.writeBuffer();
  downloadBlob(
    new Blob([buffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
    `${safeFileName(fileName)}.xlsx`,
  );
}

export async function exportPdf(fileName: string, doc: ExportDocument): Promise<void> {
  const [{ jsPDF }, { default: autoTable }] = await Promise.all([import("jspdf"), import("jspdf-autotable")]);
  const pdf = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });
  pdf.setFontSize(16);
  pdf.text(doc.title, 40, 44);
  pdf.setFontSize(10);
  let y = 62;
  if (doc.subtitle) {
    pdf.text(doc.subtitle, 40, y);
    y += 16;
  }
  pdf.text(`Generated ${doc.generatedAt ?? new Date().toISOString()}`, 40, y);
  y += 12;

  for (const table of doc.tables) {
    pdf.setFontSize(12);
    pdf.text(table.name, 40, y + 18);
    autoTable(pdf, {
      startY: y + 26,
      head: [table.columns],
      body: table.rows.map((row) => row.map((cell) => (cell === null || cell === undefined ? "" : String(cell)))),
      styles: { fontSize: 8, cellPadding: 3 },
      headStyles: { fillColor: [14, 116, 144] },
      margin: { left: 40, right: 40 },
    });
    // autoTable records the final Y position on the document.
    const last = (pdf as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable;
    y = (last?.finalY ?? y) + 24;
    if (y > pdf.internal.pageSize.getHeight() - 80) {
      pdf.addPage();
      y = 40;
    }
  }

  pdf.save(`${safeFileName(fileName)}.pdf`);
}
