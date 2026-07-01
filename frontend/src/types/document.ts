/* eslint-disable @typescript-eslint/no-explicit-any */
export type UploadStatus = "pending" | "processing" | "completed" | "failed";
export type ReviewStatus = "pending" | "approved" | "rejected" | "revised";

export interface CodeItem {
  code: string;
  system: string;
  description: string;
  db_description?: string;
  confidence: number;
  confidence_reason?: string;
  evidence_text: string;
  needs_review?: boolean;
  review_reason?: string;
  source?: string;
  reason?: string;
  was_coded?: boolean;
  coding_decision?: string;
  validation_rule?: string;
}

export interface SoapNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface CodingResult {
  id: number;
  upload_record_id: number;       // just the ID
  file_url: string;               // flattened from upload_record
  file_type: FileType;            // flattened
  file_name: string;              // flattened
  upload_status: UploadStatus;    // flattened
  soap_note: SoapNote;
  extracted_evidence: Record<string, any>;
  extracted_diagnoses: any[];
  icd_codes: CodeItem[];
  cpt_codes: CodeItem[];
  validation_metadata: Record<string, any>;
  validation_log: Record<string, any>;
  summary: string;
  confidence: number | null;
  review_status: ReviewStatus;
  review_notes: string;
  reviewed_by_username: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total: number;
  processing: number;
  ready_for_review: number;
  approved: number;
}

// --- Upload types ---

export type FileType = "pdf" | "image" | "audio" | "raw_text";

export interface UploadPayload {
  file_type: FileType;
  file_url?: string;    // for files
  file_name?: string;   // for files
  raw_text?: string;    // for raw text
}

export interface UploadRecord {
  id: number;
  status: "pending" | "processing" | "completed" | "failed";
  file_type: FileType;
  file_name: string;
  error_message?: string;
}