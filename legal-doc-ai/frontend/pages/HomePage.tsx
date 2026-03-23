import { useMemo, useState } from 'react';
import EntitiesPanel from '../components/EntitiesPanel';
import KeyPointsPanel from '../components/KeyPointsPanel';
import NextStepsPanel from '../components/NextStepsPanel';
import PdfPreview from '../components/PdfPreview';
import PunishmentPanel from '../components/PunishmentPanel';
import SummaryPanel from '../components/SummaryPanel';
import UploadPanel from '../components/UploadPanel';
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
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selectedSpan, setSelectedSpan] = useState('');

  const headerStat = useMemo(() => {
    if (!result) return 'Awaiting analysis';
    return `${result.extraction.parties.length + result.extraction.judges.length + result.extraction.legal_sections_cited.length} key entities detected`;
  }, [result]);

  const handleUpload = async (pdf: File) => {
    setLoading(true);
    setFile(pdf);
    setResult(null);
    setSelectedSpan('');
    try {
      const { job_id } = await uploadPdf(pdf);
      const analysis = await pollUntilComplete(job_id);
      setResult(analysis);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectEntity = (entity: ExtractedEntity) => {
    setSelectedSpan(`${entity.value} [${entity.source.start_char}-${entity.source.end_char}]`);
  };

  return (
    <main className="min-h-screen px-4 py-6 md:px-8">
      <header className="mb-5 rounded-2xl border border-slate-900/10 bg-white/60 px-5 py-4 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 md:text-4xl">Legal Document Intelligence</h1>
            <p className="mt-1 text-sm text-slate-600">End-to-end extraction, decision intelligence, and evidence-backed legal summarization.</p>
          </div>
          <div className="ribbon w-fit">{loading ? 'Processing...' : headerStat}</div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-[430px_430px_1fr]">
        <aside className="space-y-4 2xl:sticky 2xl:top-4 2xl:h-fit">
          <UploadPanel onSubmit={handleUpload} loading={loading} />
          <SummaryPanel result={result} />
          <KeyPointsPanel result={result} />
          <PunishmentPanel result={result} onSelectSpan={handleSelectEntity} />
          <NextStepsPanel result={result} selectedSpan={selectedSpan} />
        </aside>

        <section className="space-y-4">
          <EntitiesPanel result={result} onSelectSpan={handleSelectEntity} />
        </section>

        <section>
          <PdfPreview file={file} />
        </section>
      </div>
    </main>
  );
}
