import { AnalysisResult } from '../src/types';

type Props = {
  result: AnalysisResult | null;
};

export default function SummaryPanel({ result }: Props) {
  return (
    <section className="glass-panel fade-in rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <h2 className="panel-title">Summary</h2>
        <span className="ribbon">Easy Language</span>
      </div>

      <div className="mt-4 space-y-4 text-sm leading-6">
        <article className="rounded-xl border border-emerald-950/10 bg-white/70 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900">Extractive</p>
          <p className="mt-2 text-slate-700">{result?.summary_extractive || 'Waiting for analysis output...'}</p>
        </article>

        <article className="rounded-xl border border-amber-800/20 bg-amber-50/70 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">Generative</p>
          <p className="mt-2 text-slate-700">{result?.summary_abstractive || 'Waiting for analysis output...'}</p>
        </article>
      </div>
    </section>
  );
}
