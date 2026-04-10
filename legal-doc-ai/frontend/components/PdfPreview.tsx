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
      <section className="section-card h-full min-h-[280px] fade-up stagger-3">
        <div className="section-header">
          <div className="panel-header-main">
            <span className="panel-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="4" y="3" width="16" height="18" rx="2" />
                <path d="M8 7h8" />
                <path d="M8 12h8" />
                <path d="M8 17h5" />
              </svg>
            </span>
            <h2 className="panel-title">PDF Preview</h2>
          </div>
          <span className="badge-soft">Source</span>
        </div>
        <p className="panel-subtitle">Upload a document to inspect original pages alongside extracted output.</p>
      </section>
    );
  }

  return (
    <section className="section-card fade-up h-[84vh] overflow-y-auto stagger-3">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="4" y="3" width="16" height="18" rx="2" />
              <path d="M8 7h8" />
              <path d="M8 12h8" />
              <path d="M8 17h5" />
            </svg>
          </span>
          <h2 className="panel-title">PDF Preview</h2>
        </div>
        <span className="badge-soft">{numPages || '?'} Pages</span>
      </div>

      <Document
        file={file}
        onLoadSuccess={(doc) => setNumPages(doc.numPages)}
        loading={<p className="text-sm text-slate-500">Rendering document pages...</p>}
      >
        {Array.from({ length: numPages }, (_, idx) => (
          <div key={idx + 1} className="card-hover-dark spotlight-border mb-4 rounded-xl border border-slate-200 bg-slate-50/70 p-2 shadow-sm">
            <Page pageNumber={idx + 1} width={560} className="mx-auto" />
          </div>
        ))}
      </Document>
    </section>
  );
}
