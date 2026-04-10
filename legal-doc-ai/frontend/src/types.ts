export type SourceSpan = {
  text: string;
  start_char: number;
  end_char: number;
  page: number | null;
};

export type ExtractedEntity = {
  label: string;
  value: string;
  confidence: number;
  source: SourceSpan;
};

export type CoreExtraction = {
  case_name: ExtractedEntity | null;
  parties: ExtractedEntity[];
  judges: ExtractedEntity[];
  court_names: ExtractedEntity[];
  important_dates: ExtractedEntity[];
  legal_sections_cited: ExtractedEntity[];
  punishment_sentence: ExtractedEntity[];
  final_order: ExtractedEntity | null;
};

export type RetrievalHit = {
  doc_id: string;
  score: number;
  snippet: string;
};

export type AnalysisResult = {
  summary_extractive: string;
  summary_abstractive: string;
  key_points: {
    label: string;
    sentence: string;
    confidence: number;
    source: SourceSpan;
  }[];
  next_steps: string[];
  extraction: CoreExtraction;
  retrieval_context: RetrievalHit[];
  disclaimer: string;
};

export type JobStatus = {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  error?: string;
  result?: AnalysisResult;
};

export type ChatSource = {
  page: number | null;
  snippet: string;
};

export type ChatTurn = {
  role: 'user' | 'assistant';
  content: string;
};

export type ChatAnswer = {
  answer: string;
  sources: ChatSource[];
  disclaimer: string;
};

export type ChatMessage = ChatTurn & {
  sources?: ChatSource[];
};
