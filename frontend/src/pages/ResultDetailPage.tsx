import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { getCodingResult } from '@/api/coding';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { CodeTable } from '@/components/coding/CodeTable';
import { SoapPanel } from '@/components/coding/SoapPanel';
import { formatDate, formatPercent, reviewStatusLabel } from '@/utils/format';

export function ResultDetailPage() {
  const { id } = useParams<{ id: string }>();
  const resultId = Number(id);

  const { data: result, isLoading, isError } = useQuery({
    queryKey: ['coding-result', resultId],
    queryFn: () => getCodingResult(resultId),
    enabled: Number.isFinite(resultId),
  });

  const downloadReport = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `coding-result-${result.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (isError || !result) return <p className="text-rose-400">Result not found</p>;

  const meta = result.validation_metadata as { needs_review?: boolean; flagged_count?: number };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{result.file_name || `Result #${result.id}`}</h1>
          <p className="mt-1 text-slate-400">{formatDate(result.created_at)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={result.review_status}>{reviewStatusLabel(result.review_status)}</Badge>
          {result.confidence != null && (
            <span className="text-sm text-slate-400">Confidence {formatPercent(result.confidence)}</span>
          )}
          {result.review_status === 'pending' && (
            <Link to={`/review/${result.id}`}>
              <Button type="button">Open review</Button>
            </Link>
          )}
          {['approved', 'revised'].includes(result.review_status) && (
            <Link to={`/reports/${result.id}`}>
              <Button variant="secondary" type="button">
                View report
              </Button>
            </Link>
          )}
          <Button variant="ghost" type="button" onClick={downloadReport}>
            <Download className="h-4 w-4" />
            Export JSON
          </Button>
        </div>
      </div>

      {meta?.needs_review && (
        <Card className="border-l-4 border-l-amber-500">
          <p className="text-sm text-amber-200">
            Validation flagged {meta.flagged_count ?? 0} code(s) — human review recommended.
          </p>
        </Card>
      )}

      {result.summary && (
        <Card>
          <h2 className="mb-2 text-sm font-semibold text-slate-400">Summary</h2>
          <p className="text-slate-200">{result.summary}</p>
        </Card>
      )}

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-white">SOAP note</h2>
        <SoapPanel soap={result.soap_note} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <CodeTable title="ICD-10" codes={result.icd_codes} accent="teal" />
        <CodeTable title="CPT" codes={result.cpt_codes} accent="amber" />
      </div>
    </div>
  );
}
