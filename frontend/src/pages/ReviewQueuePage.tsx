import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listCodingResults } from '@/api/coding';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDate } from '@/utils/format';

export function ReviewQueuePage() {
  const { data: results = [], isLoading } = useQuery({
    queryKey: ['coding-results'],
    queryFn: listCodingResults,
  });

  const queue = results.filter((r) => r.review_status === 'pending');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Review queue</h1>
        <p className="mt-1 text-slate-400">Flagged or unvalidated codes awaiting human coder review</p>
      </div>

      {isLoading ? (
        <p className="text-slate-500">Loading…</p>
      ) : queue.length === 0 ? (
        <Card className="border-l-4 border-l-teal-500">
          <p className="text-teal-200">Queue is empty — all caught up.</p>
        </Card>
      ) : (
        <div className="grid gap-3">
          {queue.map((r) => {
            const meta = r.validation_metadata as { flagged_count?: number };
            return (
              <Link key={r.id} to={`/review/${r.id}`}>
                <Card className="transition hover:border-rose-500/30">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-white">{r.file_name || `Result #${r.id}`}</h3>
                      <p className="text-xs text-slate-500">{formatDate(r.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {(meta?.flagged_count ?? 0) > 0 && (
                        <Badge tone="failed">{meta.flagged_count} flagged</Badge>
                      )}
                      <Badge tone="pending">Review</Badge>
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
