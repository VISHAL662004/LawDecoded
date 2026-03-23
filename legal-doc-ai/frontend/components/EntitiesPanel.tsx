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
    return <section className="glass-panel rounded-2xl p-5 text-sm text-slate-600">Entities will appear here after analysis.</section>;
  }

  return (
    <section className="glass-panel fade-in rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <h2 className="panel-title">Extracted Entities</h2>
        <span className="ribbon">Evidence Linked</span>
      </div>

      {result.extraction.case_name && (
        <div className="mt-3 rounded-xl border border-emerald-900/20 bg-emerald-50/70 p-3 text-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-900">Case Name</p>
          <p className="mt-1 font-medium text-slate-800">{result.extraction.case_name.value}</p>
        </div>
      )}

      <div className="mt-3 space-y-3">
        {groups.map((group) => {
          const items = result.extraction[group.key] as ExtractedEntity[];
          return (
            <div key={group.key}>
              <h3 className="text-sm font-semibold text-slate-700">{group.title}</h3>
              <div className="mt-1 space-y-2">
                {items.map((item, i) => (
                  <button
                    key={`${group.key}-${i}`}
                    className="block w-full rounded-xl border border-slate-900/10 bg-white/75 p-2.5 text-left text-sm text-slate-700 transition hover:border-emerald-700/40 hover:bg-emerald-50"
                    onClick={() => onSelectSpan(item)}
                  >
                    {item.value}
                  </button>
                ))}
                {!items.length && <p className="text-xs text-slate-500">Not detected.</p>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
