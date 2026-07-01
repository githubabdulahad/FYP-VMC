import axios from "../../../lib/axios";
import type { CodingResult } from "../../../types/document";

// Get all coding results (for review queue listing)
export async function getCodingResults(): Promise<CodingResult[]> {
  const response = await axios.get("/coding/");
  return response.data;
}

// Get single coding result with full details
export async function getCodingDetail(id: number): Promise<CodingResult> {
  const response = await axios.get(`/coding/${id}/`);
  return response.data;
}

// Submit review (approve, reject, or revise)
export interface ReviewSubmission {
  review_status: "approved" | "rejected" | "revised";
  review_notes?: string;
  icd_codes?: Array<{ code: string; description: string }>;
  cpt_codes?: Array<{ code: string; description: string }>;
}

export async function submitReview(
  id: number,
  payload: ReviewSubmission
): Promise<CodingResult> {
  const response = await axios.post(`/coding/${id}/review/`, payload);
  return response.data;
}

// Delete a single code from a coding result
export async function deleteCode(
  id: number,
  payload: { code: string; type: "icd" | "cpt" }
): Promise<CodingResult> {
  const response = await axios.delete(`/coding/${id}/code/`, {
    data: payload,
  });
  return response.data;
}

// Get alternative code suggestions
export interface AlternativeCodeRequest {
  system: "ICD10" | "CPT";
  evidence_text: string;
}

export interface AlternativeCodeSuggestion {
  code: string;
  description: string;
  score: number;
  source: string;
}

export async function getAlternativeCodeSuggestions(
  id: number,
  payload: AlternativeCodeRequest
): Promise<{ candidates: AlternativeCodeSuggestion[] }> {
  const response = await axios.post(`/coding/${id}/alternatives/`, payload);
  return response.data;
}

export async function getReportData(id: number) {
  const response = await axios.get(`/reports/${id}/`);
  return response.data;
}