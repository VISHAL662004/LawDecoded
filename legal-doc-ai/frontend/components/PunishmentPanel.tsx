import { AnalysisResult, ExtractedEntity } from '../src/types';

type Props = {
  result: AnalysisResult | null;
  onSelectSpan: (entity: ExtractedEntity) => void;
};

export default function PunishmentPanel({ result, onSelectSpan }: Props) {
  const items = result?.extraction.punishment_sentence || [];

  return (
    <section className="glass-panel fade-in rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <h2 className="panel-title">Punishment / Sentence</h2>
        <span className="ribbon">Entity</span>
      </div>
      <div className="mt-3 space-y-2">
        {items.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectSpan(item)}
            className="block w-full rounded-xl border border-amber-900/20 bg-white/80 p-3 text-left text-sm text-slate-700 transition hover:border-amber-700/40 hover:bg-amber-50"
          >
            {item.value}
          </button>
        ))}
        {!items.length && <p className="text-sm text-slate-500">No punishment sentence extracted.</p>}
      </div>
    </section>
  );
}
