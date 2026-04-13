import { AnalysisResult } from '../src/types';
import TypewriterText from './TypewriterText';

type Props = {
  result: AnalysisResult | null;
};

export default function SummaryPanel({ result }: Props) {
  const extractive = result?.summary_extractive || 'Waiting for analysis output...';
  const generative = result?.summary_abstractive || 'Waiting for analysis output...';
  const animate = !!result;

  return (
    <section className="section-card fade-up stagger-1">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 6h16" />
              <path d="M4 12h16" />
              <path d="M4 18h10" />
            </svg>
          </span>
          <h2 className="panel-title">Summary</h2>
        </div>
      </div>

      <div className="mt-4 space-y-4 text-sm leading-6">
        <article className="card-hover-dark spotlight-border rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <p className="card-muted text-xs font-semibold uppercase tracking-wide text-slate-700">Extractive</p>
          <TypewriterText
            className="card-strong mt-2 whitespace-pre-wrap text-slate-700"
            text={extractive}
            enabled={animate}
            speed={9}
            startDelay={120}
          />
        </article>

        <article className="card-hover-dark spotlight-border rounded-xl border border-amber-300/40 bg-amber-50/55 p-4">
          <p className="card-muted text-xs font-semibold uppercase tracking-wide text-amber-900">Generative</p>
          <TypewriterText
            className="card-strong mt-2 whitespace-pre-wrap text-slate-700"
            text={generative}
            enabled={animate}
            speed={8}
            startDelay={220}
          />
        </article>
      </div>
    </section>
  );
}
