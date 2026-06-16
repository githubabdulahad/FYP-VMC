import { apiRequest } from './client';
import type { FileType, UploadRecord } from '@/types';

export interface SubmitUploadPayload {
  file_type: FileType;
  file_url?: string;
  file_name?: string;
  raw_text?: string;
}

export async function submitUpload(payload: SubmitUploadPayload) {
  return apiRequest<UploadRecord>('/api/ingestion/upload/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getUploadStatus(recordId: number) {
  return apiRequest<UploadRecord>(`/api/ingestion/upload/${recordId}/`);
}
