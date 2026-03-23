import { AnalysisResult } from '../src/types';

type Props = {
  result: AnalysisResult | null;
  selectedSpan: string;
};

export default function NextStepsPanel({ result, selectedSpan }: Props) {
  return (
    <section className="glass-panel fade-in rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <h2 className="panel-title">Suggested Next Steps</h2>
        <span className="ribbon">Actionable</span>
      </div>

      <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-700">
        {(result?.next_steps || []).map((step, idx) => (
          <li key={idx}>{step}</li>
        ))}
      </ol>

      <div className="mt-4 rounded-xl border border-slate-900/10 bg-white/70 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-700">Selected Supporting Span</p>
        <p className="mt-1 text-sm text-slate-700">{selectedSpan || 'Click any extracted entity to inspect source span.'}</p>
      </div>

      {result?.disclaimer && <p className="mt-3 text-xs text-red-700">{result.disclaimer}</p>}
    </section>
  );
}
