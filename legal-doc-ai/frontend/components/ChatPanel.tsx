import { useEffect, useMemo, useRef, useState } from 'react';
import { sendChatQuestion } from '../src/api';
import { AnalysisResult, ChatMessage } from '../src/types';

type Props = {
  jobId: string | null;
  result: AnalysisResult | null;
};

const suggestedQuestions = [
  'What was the final order of the court?',
  'Which legal sections were cited in the judgment?',
  'Summarize the main facts and reasoning in simple language.',
];

export default function ChatPanel({ jobId, result }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMessages([]);
    setQuestion('');
    setLoading(false);
    setError('');
  }, [jobId]);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const canChat = useMemo(() => Boolean(jobId && result), [jobId, result]);

  const handleSubmit = async (prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed || !jobId || !result || loading) return;

    const nextUserMessage: ChatMessage = { role: 'user', content: trimmed };
    const history = [...messages, nextUserMessage].map(({ role, content }) => ({ role, content }));

    setMessages((current) => [...current, nextUserMessage]);
    setQuestion('');
    setLoading(true);
    setError('');

    try {
      const answer = await sendChatQuestion(jobId, trimmed, history);
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: answer.answer, sources: answer.sources },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to answer that question right now.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="section-card fade-up stagger-2 chat-panel">
      <div className="section-header">
        <div className="panel-header-main">
          <span className="panel-icon chat-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z" />
              <path d="M7 9h10" />
              <path d="M7 13h7" />
            </svg>
          </span>
          <h2 className="panel-title">PDF Chat</h2>
        </div>
      </div>

      <p className="panel-subtitle">
        Ask follow-up questions about the uploaded judgment. Answers are grounded in the PDF and the analysis output.
      </p>

      <div ref={transcriptRef} className="chat-transcript mt-4 space-y-3">
        {!messages.length && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/80 p-4 text-sm text-slate-600">
            {canChat
              ? 'Start with a direct question, or try one of the prompts below.'
              : 'Upload and analyze a PDF first, then the chat assistant will become available.'}
          </div>
        )}

        {messages.map((message, index) => (
          <article
            key={`${message.role}-${index}`}
            className={message.role === 'user' ? 'chat-bubble user-bubble' : 'chat-bubble assistant-bubble'}
          >
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              {message.role === 'user' ? 'You' : 'Assistant'}
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{message.content}</p>
            {message.sources?.length ? (
              <div className="mt-3 space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Sources</p>
                <div className="space-y-2">
                  {message.sources.map((source, sourceIndex) => (
                    <div key={`${index}-${sourceIndex}`} className="source-chip">
                      <span className="source-page">Page {source.page ?? 'Unknown'}</span>
                      <span className="source-snippet">{source.snippet}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </article>
        ))}

        {loading && (
          <div className="chat-bubble assistant-bubble opacity-75">
            <p className="text-sm text-slate-600">Thinking through the document...</p>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {suggestedQuestions.map((item) => (
          <button
            key={item}
            className="chat-prompt"
            disabled={!canChat || loading}
            onClick={() => handleSubmit(item)}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-3">
        <textarea
          className="chat-input"
          rows={4}
          value={question}
          disabled={!canChat || loading}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void handleSubmit(question);
            }
          }}
          placeholder={canChat ? 'Ask a question about the uploaded PDF...' : 'Upload and analyze a PDF first'}
        />

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">{error || 'Answers are generated on the backend using Groq.'}</p>
          <button className="btn-primary" disabled={!canChat || loading || !question.trim()} onClick={() => handleSubmit(question)}>
            {loading ? 'Answering...' : 'Ask'}
          </button>
        </div>
      </div>
    </section>
  );
}