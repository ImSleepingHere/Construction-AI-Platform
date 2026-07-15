/**
 * Client-side PDF text extraction via pdfjs-dist. Runs entirely in the
 * browser -- no backend upload endpoint, so the extracted text is fed into
 * the existing meeting_intelligence `notes` input.
 */
"use client";

let workerConfigured = false;

async function loadPdfjs() {
  const pdfjsLib = await import("pdfjs-dist");
  if (!workerConfigured) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
      "pdfjs-dist/build/pdf.worker.min.mjs",
      import.meta.url,
    ).toString();
    workerConfigured = true;
  }
  return pdfjsLib;
}

export async function extractPdfText(file: File): Promise<string> {
  const pdfjsLib = await loadPdfjs();
  const buffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: buffer }).promise;

  const pages: string[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const text = content.items
      .map((item) => ("str" in item ? item.str : ""))
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    if (text) pages.push(text);
  }

  return pages.join("\n\n").trim();
}
