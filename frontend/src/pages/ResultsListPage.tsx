import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listCodingResults } from '@/api/coding';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDate, fileTypeLabel, reviewStatusLabel } from '@/utils/format';

export function ResultsListPage() {
  const { data: results = [], isLoading } = useQuery({
    queryKey: ['coding-results'],
    queryFn: listCodingResults,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Coding results</h1>

      {isLoading ? (
        <p className="text-slate-500">Loading…</p>
      ) : results.length === 0 ? (
        <Card>
          <p className="text-slate-400">No results yet.</p>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-700/40">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-800/80 text-xs text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id} className="border-t border-slate-800/80 hover:bg-surface-800/40">
                  <td className="px-4 py-3">
                    <Link to={`/results/${r.id}`} className="font-medium text-teal-300 hover:underline">
                      {r.file_name || `#${r.id}`}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{fileTypeLabel(r.file_type)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={r.review_status}>{reviewStatusLabel(r.review_status)}</Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
