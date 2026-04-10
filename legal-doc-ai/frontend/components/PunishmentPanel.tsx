import { AnalysisResult, ExtractedEntity } from '../src/types';

type Props = {
  result: AnalysisResult | null;
  onSelectSpan: (entity: ExtractedEntity) => void;
};

export default function PunishmentPanel({ result, onSelectSpan }: Props) {
  const items = result?.extraction.punishment_sentence || [];

  return (
    <section className="section-card fade-up stagger-1">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M12 2v6" />
              <path d="M6.2 6.2 10 10" />
              <path d="M2 12h6" />
              <path d="M6.2 17.8 10 14" />
              <path d="M12 22v-6" />
              <path d="m17.8 17.8-3.8-3.8" />
              <path d="M22 12h-6" />
              <path d="m17.8 6.2-3.8 3.8" />
            </svg>
          </span>
          <h2 className="panel-title">Punishment / Sentence</h2>
        </div>
        <span className="badge-gold">Critical</span>
      </div>
      <div className="mt-3 space-y-2">
        {items.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectSpan(item)}
            className="interactive-row"
          >
            {item.value}
          </button>
        ))}
        {!items.length && <p className="text-sm text-slate-500">No punishment sentence extracted.</p>}
      </div>
    </section>
  );
}
