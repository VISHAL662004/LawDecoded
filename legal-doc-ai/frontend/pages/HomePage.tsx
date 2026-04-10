import { useMemo, useState } from 'react';
import EntitiesPanel from '../components/EntitiesPanel';
import KeyPointsPanel from '../components/KeyPointsPanel';
import NextStepsPanel from '../components/NextStepsPanel';
import ChatPanel from '../components/ChatPanel';
import PdfPreview from '../components/PdfPreview';
import PunishmentPanel from '../components/PunishmentPanel';
import SummaryPanel from '../components/SummaryPanel';
import UploadPanel from '../components/UploadPanel';
import RevealSection from '../components/RevealSection';
import SplitText from '../components/SplitText';
import { fetchJob, uploadPdf } from '../src/api';
import { AnalysisResult, ExtractedEntity } from '../src/types';

async function pollUntilComplete(jobId: string): Promise<AnalysisResult> {
  while (true) {
    const job = await fetchJob(jobId);
    if (job.status === 'completed' && job.result) return job.result;
    if (job.status === 'failed') throw new Error(job.error || 'Analysis failed');
    await new Promise((r) => setTimeout(r, 2500));
  }
}

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selectedSpan, setSelectedSpan] = useState('');

  const headerStat = useMemo(() => {
    if (!result) return 'Awaiting analysis';
    return `${result.extraction.parties.length + result.extraction.judges.length + result.extraction.legal_sections_cited.length} key entities detected`;
  }, [result]);

  const handleUpload = async (pdf: File) => {
    setLoading(true);
    setFile(pdf);
    setJobId(null);
    setResult(null);
    setSelectedSpan('');
    try {
      const { job_id } = await uploadPdf(pdf);
      setJobId(job_id);
      const analysis = await pollUntilComplete(job_id);
      setResult(analysis);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectEntity = (entity: ExtractedEntity) => {
    setSelectedSpan(`${entity.value} [${entity.source.start_char}-${entity.source.end_char}]`);
  };

  const metrics = useMemo(() => {
    if (!result) {
      return [
        { label: 'Documents', value: loading ? 'In Progress' : 'Ready' },
        { label: 'Entities', value: '0' },
        { label: 'Key Points', value: '0' },
      ];
    }

    return [
      { label: 'Documents', value: file ? '1 Active' : '0' },
      {
        label: 'Entities',
        value: String(
          result.extraction.parties.length +
            result.extraction.judges.length +
            result.extraction.court_names.length +
            result.extraction.important_dates.length +
            result.extraction.legal_sections_cited.length +
            result.extraction.punishment_sentence.length +
            (result.extraction.case_name ? 1 : 0),
        ),
      },
      { label: 'Key Points', value: String(result.key_points.length) },
    ];
  }, [result, loading, file]);

  return (
    <main className="app-shell">
      <div className="app-content">
        <RevealSection>
          <header className="hero-panel surface-glass mb-5 overflow-hidden rounded-3xl px-5 py-6 md:px-8 md:py-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <span className="badge-soft">Enterprise Legal Intelligence</span>
              <h1 className="mt-4 text-3xl font-semibold leading-tight text-slate-900 md:text-5xl">
                <SplitText
                  text="Litigation intelligence with precision-grade extraction and narrative clarity."
                  delay={70}
                  duration={1}
                />
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
                Designed for legal teams that need trustworthy output fast: entity extraction, document-grounded summaries, and structured action guidance in one cohesive workspace.
              </p>

              <div className="mt-5 flex flex-wrap gap-2">
                <span className="hero-chip">Evidence-linked entities</span>
                <span className="hero-chip">Actionable next steps</span>
                <span className="hero-chip">Judgment-first workflow</span>
              </div>
            </div>

            <div className="grid w-full gap-3 sm:grid-cols-3 lg:max-w-[580px]">
              {metrics.map((item) => (
                <div key={item.label} className="metric-card spotlight-border">
                  <p className="metric-label text-xs font-semibold uppercase tracking-wider text-slate-500">{item.label}</p>
                  <p className="metric-value mt-1 text-xl font-extrabold text-slate-900">{item.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/80 bg-white/72 px-4 py-3">
            <p className="text-sm text-slate-600">Pipeline Status</p>
            <div className={loading ? 'badge-gold' : 'badge-soft'}>{loading ? 'Processing document' : headerStat}</div>
          </div>
        </header>
        </RevealSection>

        <div className="grid grid-cols-1 gap-4 2xl:grid-cols-[430px_430px_1fr]">
          <aside className="space-y-4 2xl:sticky 2xl:top-4 2xl:h-fit">
            <RevealSection>
              <UploadPanel onSubmit={handleUpload} loading={loading} />
            </RevealSection>
            <RevealSection>
              <SummaryPanel result={result} />
            </RevealSection>
            <RevealSection>
              <ChatPanel key={jobId ?? 'chat-empty'} jobId={jobId} result={result} />
            </RevealSection>
            <RevealSection>
              <KeyPointsPanel result={result} />
            </RevealSection>
            <RevealSection>
              <PunishmentPanel result={result} onSelectSpan={handleSelectEntity} />
            </RevealSection>
            <RevealSection>
              <NextStepsPanel result={result} />
            </RevealSection>
          </aside>

          <section className="space-y-4">
            <RevealSection>
              <EntitiesPanel result={result} onSelectSpan={handleSelectEntity} />
            </RevealSection>
          </section>

          <section>
            <RevealSection>
              <PdfPreview file={file} />
            </RevealSection>
          </section>
        </div>
      </div>
    </main>
  );
}
