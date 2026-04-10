import { AnalysisResult } from '../src/types';

type Props = {
  result: AnalysisResult | null;
};

export default function NextStepsPanel({ result }: Props) {
  return (
    <section className="section-card fade-up stagger-2">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="m9 18 6-6-6-6" />
            </svg>
          </span>
          <h2 className="panel-title">Suggested Next Steps</h2>
        </div>
        <span className="badge-gold">Actionable</span>
      </div>

      <ol className="mt-3 space-y-2 text-sm text-slate-700">
        {(result?.next_steps || []).map((step, idx) => (
          <li key={idx} className="timeline-step card-hover-dark">
            <span className="card-strong mr-2 font-semibold text-slate-900">{idx + 1}.</span>
            <span className="card-strong">{step}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
