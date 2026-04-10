import { AnalysisResult } from '../src/types';

type Props = {
  result: AnalysisResult | null;
};

export default function KeyPointsPanel({ result }: Props) {
  const items = [...(result?.key_points || [])].sort((a, b) => b.confidence - a.confidence);
  return (
    <section className="section-card fade-up stagger-2">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="m9 12 2 2 4-4" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </span>
          <h2 className="panel-title">Important Points</h2>
        </div>
        <span className="badge-soft">Structured</span>
      </div>

      <div className="mt-3 space-y-2">
        {items.map((point, idx) => (
          <article key={idx} className="card-hover-dark rounded-xl border border-slate-200 bg-white p-3 transition hover:border-slate-300 hover:shadow-sm">
            <p className="card-muted text-xs font-semibold uppercase tracking-wide text-slate-700">
              {point.label} · {point.confidence.toFixed(2)}
            </p>
            <p className="card-strong mt-1 text-sm text-slate-700">{point.sentence}</p>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-slate-700/80"
                style={{ width: `${Math.max(8, Math.min(100, point.confidence * 100))}%` }}
              />
            </div>
          </article>
        ))}
        {!items.length && <p className="text-sm text-slate-500">Important points will appear here after analysis.</p>}
      </div>
    </section>
  );
}
