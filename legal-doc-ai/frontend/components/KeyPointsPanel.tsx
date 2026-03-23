import { AnalysisResult } from '../src/types';

type Props = {
  result: AnalysisResult | null;
};

export default function KeyPointsPanel({ result }: Props) {
  const items = result?.key_points || [];
  return (
    <section className="glass-panel fade-in rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <h2 className="panel-title">Important Points</h2>
        <span className="ribbon">Structured</span>
      </div>

      <div className="mt-3 space-y-2">
        {items.map((point, idx) => (
          <div key={idx} className="rounded-xl border border-slate-900/10 bg-white/70 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900">
              {point.label} · {point.confidence.toFixed(2)}
            </p>
            <p className="mt-1 text-sm text-slate-700">{point.sentence}</p>
          </div>
        ))}
        {!items.length && <p className="text-sm text-slate-500">Important points will appear here after analysis.</p>}
      </div>
    </section>
  );
}
