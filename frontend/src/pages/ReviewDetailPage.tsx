import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getCodingResult, submitReview } from '@/api/coding';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { CodeTable } from '@/components/coding/CodeTable';
import { SoapPanel } from '@/components/coding/SoapPanel';
import { toApiError } from '@/api/client';
import type { MedicalCode, ReviewStatus } from '@/types';
import { deleteCode } from '@/api/coding';

export function ReviewDetailPage() {
  const { id } = useParams<{ id: string }>();
  const resultId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: result, isLoading } = useQuery({
    queryKey: ['coding-result', resultId],
    queryFn: () => getCodingResult(resultId),
    enabled: Number.isFinite(resultId),
  });

  const [icdCodes, setIcdCodes] = useState<MedicalCode[]>([]);
  const [cptCodes, setCptCodes] = useState<MedicalCode[]>([]);
  const [reviewNotes, setReviewNotes] = useState('');

  useEffect(() => {
    if (result) {
      setIcdCodes(result.icd_codes);
      setCptCodes(result.cpt_codes);
      setReviewNotes(result.review_notes ?? '');
    }
  }, [result]);

  const mutation = useMutation({
    mutationFn: (status: ReviewStatus) =>
      submitReview(resultId, {
        review_status: status,
        icd_codes: icdCodes,
        cpt_codes: cptCodes,
        review_notes: reviewNotes,
        feedback_type: status === 'revised' ? 'incorrect_code' : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['coding-results'] });
      queryClient.invalidateQueries({ queryKey: ['coding-result', resultId] });
      navigate(`/results/${resultId}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: ({ code, type }: { code: string; type: 'icd' | 'cpt' }) =>
      deleteCode(resultId, code, type),
    onSuccess: (data) => {
      queryClient.setQueryData(['coding-result', resultId], data);
    },
  });

  const [error, setError] = useState('');

  const handleAction = async (status: ReviewStatus) => {
    setError('');
    try {
      await mutation.mutateAsync(status);
    } catch (err) {
      setError(toApiError(err).message);
    }
  };

  const handleDeleteCode = async (code: string, type: 'icd' | 'cpt') => {
    setError('');
    try {
      await deleteMutation.mutateAsync({ code, type });
    } catch (err) {
      setError(toApiError(err).message);
    }
  };

  if (isLoading || !result) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Review: {result.file_name}</h1>

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-white">SOAP note</h2>
        <SoapPanel soap={result.soap_note} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <CodeTable title="ICD-10 (editable in API)" codes={icdCodes} onDeleteCode={handleDeleteCode} />
        <CodeTable title="CPT" codes={cptCodes} onDeleteCode={handleDeleteCode} />
      </div>

      <Card>
        <label className="mb-1 block text-xs font-medium text-slate-400">Review notes</label>
        <textarea
          className="min-h-[80px] w-full rounded-xl border border-slate-600/50 bg-surface-900 px-3 py-2 text-sm"
          value={reviewNotes}
          onChange={(e) => setReviewNotes(e.target.value)}
        />
      </Card>

      {error && <p className="text-sm text-rose-400">{error}</p>}

      <div className="flex flex-wrap gap-3">
        <Button
          loading={mutation.isPending}
          onClick={() => handleAction('approved')}
        >
          Approve
        </Button>
        <Button
          variant="secondary"
          loading={mutation.isPending}
          onClick={() => handleAction('revised')}
        >
          Save revisions
        </Button>
        <Button
          variant="danger"
          loading={mutation.isPending}
          onClick={() => handleAction('rejected')}
        >
          Reject
        </Button>
      </div>
    </div>
  );
}
