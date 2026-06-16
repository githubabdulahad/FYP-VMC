import { useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { getUploadStatus } from '@/api/ingestion';
import { listCodingResults } from '@/api/coding';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PipelineProgress } from '@/components/pipeline/PipelineProgress';
import { stageIndexFromUpload } from '@/utils/pipeline';
import type { PipelineStage } from '@/types';

const STAGE_IDS: PipelineStage[] = [
  'upload',
  'detect',
  'normalize',
  'llm',
  'postprocess',
  'validate',
  'review',
  'complete',
];

export function ProcessingPage() {
  const { recordId } = useParams<{ recordId: string }>();
  const id = Number(recordId);
  const navigate = useNavigate();

  const { data: upload, isError } = useQuery({
    queryKey: ['upload', id],
    queryFn: () => getUploadStatus(id),
    enabled: Number.isFinite(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 2000;
    },
  });

  const { data: results } = useQuery({
    queryKey: ['coding-results'],
    queryFn: listCodingResults,
    enabled: upload?.status === 'completed',
    refetchInterval: upload?.status === 'completed' ? 2000 : false,
  });

  const codingResult = results?.find((r) => r.upload_record_id === id);

  useEffect(() => {
    if (upload?.status === 'completed' && codingResult) {
      const t = setTimeout(() => {
        if (codingResult.review_status === 'pending') {
          navigate(`/review/${codingResult.id}`);
        } else {
          navigate(`/results/${codingResult.id}`);
        }
      }, 1500);
      return () => clearTimeout(t);
    }
  }, [upload?.status, codingResult, navigate]);

  if (isError || !Number.isFinite(id)) {
    return <p className="text-rose-400">Invalid upload id</p>;
  }

  const stageIdx = upload ? stageIndexFromUpload(upload.status) : 0;
  const activeStage = STAGE_IDS[Math.max(0, stageIdx)] ?? 'upload';
  const failed = upload?.status === 'failed';

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h1 className="text-3xl font-bold text-white">Processing</h1>
        <p className="mt-1 text-slate-400">
          {upload?.file_name ?? `Upload #${id}`} — {upload?.status ?? 'loading…'}
        </p>
      </motion.div>

      <Card>
        <PipelineProgress activeStage={activeStage} failed={failed} />
        {failed && upload?.error_message && (
          <p className="mt-4 rounded-lg bg-rose-500/10 p-3 text-sm text-rose-300">{upload.error_message}</p>
        )}
        {upload?.status === 'completed' && !codingResult && (
          <p className="mt-4 text-center text-sm text-slate-400">Finalizing coding result…</p>
        )}
      </Card>

      <div className="flex gap-3">
        <Link to="/">
          <Button variant="secondary" type="button">
            Back to dashboard
          </Button>
        </Link>
        {codingResult && (
          <Link to={`/results/${codingResult.id}`}>
            <Button type="button">View result</Button>
          </Link>
        )}
      </div>
    </div>
  );
}
