import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, ClipboardList, FileUp, Sparkles } from 'lucide-react';
import { listCodingResults } from '@/api/coding';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDate, reviewStatusLabel } from '@/utils/format';

export function DashboardPage() {
  const { data: results = [], isLoading } = useQuery({
    queryKey: ['coding-results'],
    queryFn: listCodingResults,
  });

  const pendingReview = results.filter((r) => r.review_status === 'pending').length;
  const approved = results.filter((r) => ['approved', 'revised'].includes(r.review_status)).length;

  const recent = results.slice(0, 5);

  return (
    <div className="space-y-8">
      <div>
        <motion.h1
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl font-bold text-white"
        >
          Dashboard
        </motion.h1>
        <p className="mt-1 text-slate-400">Overview of your coding pipeline</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-l-4 border-l-purple-500">
          <p className="text-xs font-medium uppercase text-slate-500">Total submissions</p>
          <p className="mt-2 text-3xl font-bold text-white">{isLoading ? '…' : results.length}</p>
        </Card>
        <Card className="border-l-4 border-l-rose-500">
          <p className="text-xs font-medium uppercase text-slate-500">Needs review</p>
          <p className="mt-2 text-3xl font-bold text-rose-300">{pendingReview}</p>
        </Card>
        <Card className="border-l-4 border-l-teal-500">
          <p className="text-xs font-medium uppercase text-slate-500">Verified</p>
          <p className="mt-2 text-3xl font-bold text-teal-300">{approved}</p>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link to="/submit">
          <Card className="group cursor-pointer transition hover:border-teal-500/30">
            <div className="flex items-start justify-between">
              <div>
                <FileUp className="mb-3 h-8 w-8 text-teal-400" />
                <h3 className="font-semibold text-white">New submission</h3>
                <p className="mt-1 text-sm text-slate-400">Upload text, PDF, image, or audio</p>
              </div>
              <ArrowRight className="h-5 w-5 text-slate-600 transition group-hover:translate-x-1 group-hover:text-teal-400" />
            </div>
          </Card>
        </Link>
        <Link to="/review">
          <Card className="group cursor-pointer transition hover:border-rose-500/30">
            <div className="flex items-start justify-between">
              <div>
                <ClipboardList className="mb-3 h-8 w-8 text-rose-400" />
                <h3 className="font-semibold text-white">Review queue</h3>
                <p className="mt-1 text-sm text-slate-400">{pendingReview} items awaiting coder review</p>
              </div>
              <ArrowRight className="h-5 w-5 text-slate-600 transition group-hover:translate-x-1 group-hover:text-rose-400" />
            </div>
          </Card>
        </Link>
      </div>

      <Card>
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-400" />
          <h2 className="font-semibold text-white">Recent activity</h2>
        </div>
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : recent.length === 0 ? (
          <p className="text-sm text-slate-500">No submissions yet. Start with a new submission.</p>
        ) : (
          <ul className="divide-y divide-slate-700/40">
            {recent.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                <div>
                  <Link to={`/results/${r.id}`} className="font-medium text-teal-300 hover:underline">
                    {r.file_name || `Result #${r.id}`}
                  </Link>
                  <p className="text-xs text-slate-500">{formatDate(r.created_at)}</p>
                </div>
                <Badge tone={r.review_status}>{reviewStatusLabel(r.review_status)}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
