import type { PipelineStage, UploadStatus } from '@/types';

export const PIPELINE_STAGES: { id: PipelineStage; label: string; description: string }[] = [
  { id: 'upload', label: 'Upload', description: 'Receiving clinical input' },
  { id: 'detect', label: 'Detect type', description: 'Conversation vs clinical note' },
  { id: 'normalize', label: 'Normalize', description: 'Clean note from conversation' },
  { id: 'llm', label: 'AI coding', description: 'SOAP + ICD / CPT / SNOMED' },
  { id: 'postprocess', label: 'Post-process', description: 'Filter unconfirmed diagnoses' },
  { id: 'validate', label: 'Validate', description: 'Database & confidence checks' },
  { id: 'review', label: 'Review', description: 'Human coder if flagged' },
  { id: 'complete', label: 'Verified', description: 'Final report ready' },
];

export function stageIndexFromUpload(status: UploadStatus): number {
  switch (status) {
    case 'pending':
      return 0;
    case 'processing':
      return 3;
    case 'completed':
      return 6;
    case 'failed':
      return -1;
    default:
      return 0;
  }
}
