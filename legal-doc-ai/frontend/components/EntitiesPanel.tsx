import { AnalysisResult, ExtractedEntity } from '../src/types';

type Props = {
  result: AnalysisResult | null;
  onSelectSpan: (entity: ExtractedEntity) => void;
};

const groups: Array<{ key: keyof AnalysisResult['extraction']; title: string }> = [
  { key: 'parties', title: 'Parties' },
  { key: 'judges', title: 'Judges' },
  { key: 'court_names', title: 'Court Names' },
  { key: 'important_dates', title: 'Important Dates' },
  { key: 'legal_sections_cited', title: 'Sections Cited' },
];

export default function EntitiesPanel({ result, onSelectSpan }: Props) {
  if (!result) {
    return <section className="section-card text-sm text-slate-600">Entities will appear here after analysis.</section>;
  }

  return (
    <section className="section-card fade-up">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 19V5" />
              <path d="M20 19V5" />
              <path d="M8 9h8" />
              <path d="M8 15h8" />
            </svg>
          </span>
          <h2 className="panel-title">Extracted Entities</h2>
        </div>
        <span className="badge-soft">Evidence Linked</span>
      </div>

      {result.extraction.case_name && (
        <div className="card-hover-dark spotlight-border mt-3 rounded-xl border border-slate-300/70 bg-slate-50/70 p-3 text-sm">
          <p className="card-muted text-xs font-semibold uppercase tracking-wide text-slate-700">Case Name</p>
          <p className="card-strong mt-1 font-medium text-slate-800">{result.extraction.case_name.value}</p>
        </div>
      )}

      <div className="mt-4 space-y-4">
        {groups.map((group) => {
          const items = result.extraction[group.key] as ExtractedEntity[];
          return (
            <article key={group.key} className="card-hover-dark rounded-xl border border-slate-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="card-strong text-sm font-semibold text-slate-800">{group.title}</h3>
                <span className="card-muted text-xs font-semibold text-slate-500">{items.length}</span>
              </div>
              <div className="space-y-2">
                {items.map((item, i) => (
                  <button
                    key={`${group.key}-${i}`}
                    className="interactive-row"
                    onClick={() => onSelectSpan(item)}
                  >
                    {item.value}
                  </button>
                ))}
                {!items.length && <p className="text-xs text-slate-500">Not detected.</p>}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
