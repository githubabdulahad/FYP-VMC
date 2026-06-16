export type UserRole = 'admin' | 'coder';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  role: UserRole;
}

export type UploadStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type FileType = 'pdf' | 'image' | 'audio' | 'raw_text';
export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'revised';

export interface UploadRecord {
  id: number;
  file_url: string;
  file_type: FileType;
  file_name: string;
  status: UploadStatus;
  extracted_text: string;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface MedicalCode {
  code: string;
  description?: string;
  confidence?: number;
  evidence_text?: string;
  flagged?: boolean;
  system?: string;
  [key: string]: unknown;
}

export interface SoapNote {
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  [key: string]: unknown;
}

export interface CodingResult {
  id: number;
  upload_record_id?: number;
  file_url: string;
  file_type: FileType;
  file_name: string;
  upload_status: UploadStatus;
  soap_note: SoapNote;
  extracted_evidence: Record<string, unknown>;
  extracted_diagnoses: unknown[];
  icd_codes: MedicalCode[];
  cpt_codes: MedicalCode[];
  summary: string;
  confidence: number | null;
  validation_metadata: Record<string, unknown>;
  validation_log: Record<string, unknown>;
  review_status: ReviewStatus;
  review_notes: string;
  reviewed_by_username: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Report {
  id: number;
  file_name: string;
  file_type: FileType;
  file_url: string;
  extracted_text: string;
  soap_note: SoapNote;
  icd_codes: MedicalCode[];
  cpt_codes: MedicalCode[];
  summary: string;
  confidence: number | null;
  review_status: ReviewStatus;
  created_at: string;
}

export type PipelineStage =
  | 'upload'
  | 'detect'
  | 'normalize'
  | 'llm'
  | 'postprocess'
  | 'validate'
  | 'review'
  | 'complete';

export interface ApiError {
  message: string;
  details?: Record<string, string[] | string>;
}
