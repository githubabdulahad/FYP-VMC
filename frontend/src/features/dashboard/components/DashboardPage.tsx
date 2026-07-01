import { useQuery } from "@tanstack/react-query";
import { getCodingResults } from "../api/dashboardApi";
import type {DashboardStats } from "../../../types/document";
import DocumentTable from "../../../components/ui/DocumentTable";


// ── Stat card ─────────────────────────────────────────────
function StatCard({
  label, value, iconBg, iconColor, icon,
}: {
  label: string;
  value: number;
  iconBg: string;
  iconColor: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-slate-500">{label}</p>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconBg}`}>
          <span className={iconColor}>{icon}</span>
        </div>
      </div>
      <p className="text-2xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}


// ── Main page ─────────────────────────────────────────────
function DashboardPage() {
  const { data: results = [], isLoading } = useQuery({
    queryKey: ["codingResults"],
    queryFn: getCodingResults,
  });

  // compute stats from the list directly, no separate endpoint needed
  const stats: DashboardStats = {
    total: results.length,
    processing: 0, // processing docs don't appear in /coding/ yet
    ready_for_review: results.filter((r) => r.review_status === "pending").length,
    approved: results.filter((r) => r.review_status === "approved" || r.review_status === "revised").length,
  };

  // latest 5 only for dashboard
  const recentDocs = results.slice(0, 5);
  
  return (
    <div className="space-y-6">

      {/* Heading */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Dashboard</h2>
        <p className="text-sm text-slate-400 mt-0.5">Overview of your coding activity</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Total Documents"
          value={stats.total}
          iconBg="bg-slate-100"
          iconColor="text-slate-500"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />
        <StatCard
          label="Processing"
          value={stats.processing}
          iconBg="bg-amber-50"
          iconColor="text-amber-500"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          label="Ready for Review"
          value={stats.ready_for_review}
          iconBg="bg-blue-50"
          iconColor="text-blue-500"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          }
        />
        <StatCard
          label="Approved"
          value={stats.approved}
          iconBg="bg-teal-50"
          iconColor="text-teal-600"
          icon={
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {/* Table */}
      <DocumentTable
        documents={recentDocs}
        isLoading={isLoading}
        title="Latest Documents"
        subtitle="Your 5 most recent uploads"
        showViewAll={true}
      />
    </div>
  );
}

export default DashboardPage;