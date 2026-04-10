import { useMemo, useState } from 'react';

type Props = {
  onSubmit: (file: File) => Promise<void>;
  loading: boolean;
};

export default function UploadPanel({ onSubmit, loading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const label = useMemo(() => {
    if (!file) return 'No file selected';
    return `${file.name.slice(0, 48)}${file.name.length > 48 ? '...' : ''}`;
  }, [file]);

  return (
    <section className="section-card fade-up">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
              <path d="M14 3v5h5" />
              <path d="m12 11-3 3h2v4h2v-4h2z" />
            </svg>
          </span>
          <h2 className="panel-title">Document Upload</h2>
        </div>
        <span className="badge-soft">PDF</span>
      </div>
      <p className="panel-subtitle">Upload a judgment or order to run extraction, summarization, and recommendations.</p>

      <label className="mt-4 block cursor-pointer rounded-xl border border-slate-300/90 bg-slate-50/70 p-3 transition hover:border-slate-400 focus-within:ring-2 focus-within:ring-slate-500/40">
        <input
          className="hidden"
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <div className="flex items-center justify-between gap-2 text-sm">
          <span className="btn-secondary">Select PDF</span>
          <span className="max-w-[68%] truncate text-slate-700">{label}</span>
        </div>
        <p className="mt-3 text-xs text-slate-500">Only PDF files are accepted. Your uploaded file is processed for extraction and summarization.</p>
      </label>

      <button
        className="btn-primary mt-4 w-full"
        disabled={!file || loading}
        onClick={() => file && onSubmit(file)}
      >
        {loading ? 'Analyzing Document...' : 'Analyze Document'}
      </button>
    </section>
  );
}
