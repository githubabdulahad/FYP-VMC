import { apiRequest } from './client';
import type { CodingResult, MedicalCode, ReviewStatus } from '@/types';

export async function listCodingResults() {
  return apiRequest<CodingResult[]>('/api/coding/');
}

export async function getCodingResult(id: number) {
  return apiRequest<CodingResult>(`/api/coding/${id}/`);
}

export interface ReviewPayload {
  review_status: ReviewStatus;
  icd_codes?: MedicalCode[];
  cpt_codes?: MedicalCode[];
  summary?: string;
  review_notes?: string;
  feedback_type?: string;
  explanation?: string;
}

export async function submitReview(id: number, payload: ReviewPayload) {
  return apiRequest<CodingResult>(`/api/coding/${id}/review/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getCodeAlternatives(
  id: number,
  system: 'ICD10' | 'CPT',
  evidenceText: string,
) {
  return apiRequest<{ candidates: MedicalCode[] }>(`/api/coding/${id}/alternatives/`, {
    method: 'POST',
    body: JSON.stringify({ system, evidence_text: evidenceText }),
  });
}

export async function deleteCode(resultId: number, code: string, type: 'icd' | 'cpt') {
  return apiRequest<CodingResult>(`/api/coding/${resultId}/code/`, {
    method: 'DELETE',
    body: JSON.stringify({ code, type }),
  });
}
