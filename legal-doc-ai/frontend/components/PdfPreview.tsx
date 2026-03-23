import { Document, Page, pdfjs } from 'react-pdf';
import { useState } from 'react';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

type Props = {
  file: File | null;
};

export default function PdfPreview({ file }: Props) {
  const [numPages, setNumPages] = useState<number>(0);

  if (!file) {
    return (
      <section className="glass-panel rounded-2xl p-5">
        <h2 className="panel-title">PDF Preview</h2>
        <p className="mt-3 text-sm text-slate-600">Upload a document to inspect original pages alongside extracted output.</p>
      </section>
    );
  }

  return (
    <section className="glass-panel fade-in h-[84vh] overflow-y-auto rounded-2xl p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="panel-title">PDF Preview</h2>
        <span className="ribbon">{numPages || '?'} Pages</span>
      </div>
      <Document file={file} onLoadSuccess={(doc) => setNumPages(doc.numPages)} loading={<p className="text-sm text-slate-500">Rendering PDF...</p>}>
        {Array.from({ length: numPages }, (_, idx) => (
          <div key={idx + 1} className="mb-4 rounded-xl border border-slate-900/10 bg-white p-2">
            <Page pageNumber={idx + 1} width={560} className="mx-auto" />
          </div>
        ))}
      </Document>
    </section>
  );
}
