import axios from 'axios';
import { ChatAnswer, ChatTurn, JobStatus } from './types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
});

export async function uploadPdf(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await api.post('/analyze/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function fetchJob(jobId: string): Promise<JobStatus> {
  const res = await api.get(`/analyze/jobs/${jobId}`);
  return res.data;
}

export async function sendChatQuestion(
  jobId: string,
  question: string,
  history: ChatTurn[],
): Promise<ChatAnswer> {
  const res = await api.post(`/analyze/jobs/${jobId}/chat`, {
    question,
    history,
  });
  return res.data;
}
