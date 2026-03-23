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
    <section className="glass-panel fade-in rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <h2 className="panel-title">Document Upload</h2>
        <span className="ribbon">PDF</span>
      </div>
      <p className="mt-2 text-sm text-slate-600">Upload a judgment/order PDF to run extraction and summary pipeline.</p>

      <label className="mt-4 block cursor-pointer rounded-xl border border-emerald-900/20 bg-white/80 p-3 transition hover:border-emerald-700/45">
        <input
          className="hidden"
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <div className="flex items-center justify-between gap-2 text-sm">
          <span className="rounded-md bg-emerald-100 px-2 py-1 font-semibold text-emerald-900">Choose File</span>
          <span className="truncate text-slate-700">{label}</span>
        </div>
      </label>

      <button
        className="mt-4 w-full rounded-xl bg-emerald-800 px-4 py-3 font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!file || loading}
        onClick={() => file && onSubmit(file)}
      >
        {loading ? 'Analyzing Document...' : 'Analyze Document'}
      </button>
    </section>
  );
}
