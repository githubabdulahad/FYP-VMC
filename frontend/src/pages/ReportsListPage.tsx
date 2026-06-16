import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listReports } from '@/api/reports';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDate, reviewStatusLabel } from '@/utils/format';

export function ReportsListPage() {
  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: listReports,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Verified reports</h1>
        <p className="mt-1 text-slate-400">Approved and revised outputs ready for download</p>
      </div>

      {isLoading ? (
        <p className="text-slate-500">Loading…</p>
      ) : reports.length === 0 ? (
        <Card>
          <p className="text-slate-400">No verified reports yet. Complete a review to generate one.</p>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {reports.map((r) => (
            <Link key={r.id} to={`/reports/${r.id}`}>
              <Card className="border-l-4 border-l-sky-500 transition hover:border-sky-400/50">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-white">{r.file_name}</h3>
                    <p className="text-xs text-slate-500">{formatDate(r.created_at)}</p>
                  </div>
                  <Badge tone={r.review_status}>{reviewStatusLabel(r.review_status)}</Badge>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
