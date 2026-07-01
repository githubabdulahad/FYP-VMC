import { useNavigate } from "react-router-dom";
import type { CodingResult, ReviewStatus } from "../../types/document";

// ── Status badge ──────────────────────────────────────────
const statusConfig: Record <
  ReviewStatus,
  { label: string; dot: string; bg: string; text: string }
> = {
  pending: {
    label: "Ready for Review",
    dot: "bg-blue-500",
    bg: "bg-blue-50",
    text: "text-blue-800",
  },
  approved: {
    label: "Approved",
    dot: "bg-teal-500",
    bg: "bg-teal-50",
    text: "text-teal-800",
  },
  rejected: {
    label: "Rejected",
    dot: "bg-red-400",
    bg: "bg-red-50",
    text: "text-red-800",
  },
  revised: {
    label: "Revised",
    dot: "bg-purple-400",
    bg: "bg-purple-50",
    text: "text-purple-800",
  },
};

function StatusBadge({ status }: { status: ReviewStatus }) {
  const config = statusConfig[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}

// ── Action button ─────────────────────────────────────────
function ActionButton({ doc }: { doc: CodingResult }) {
  const navigate = useNavigate();

  if (doc.review_status === "pending") {
    return (
      <button
        onClick={() => navigate(`/review/${doc.id}`)}
        className="text-xs font-medium text-teal-600 hover:text-teal-700 transition-colors"
      >
        Review →
      </button>
    );
  }

  if (doc.review_status === "approved" || doc.review_status === "revised") {
    return (
      <button
        onClick={() => navigate(`/review/${doc.id}`)}
        className="text-xs font-medium text-teal-600 hover:text-teal-700 transition-colors"
      >
        Download →
      </button>
    );
  }

  return (
    <button
      onClick={() => navigate(`/review/${doc.id}`)}
      className="text-xs font-medium text-slate-400 hover:text-slate-600 transition-colors"
    >
      View →
    </button>
  );
}

// ── Helpers ───────────────────────────────────────────────
const fileTypeLabel: Record<string, string> = {
  pdf: "PDF",
  audio: "Audio",
  image: "Image",
  raw_text: "Text",
};

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

// ── DocumentTable component ───────────────────────────────
interface DocumentTableProps {
  documents: CodingResult[];
  isLoading: boolean;
  title?: string;
  subtitle?: string;
  showViewAll?: boolean;
}

export default function DocumentTable({
  documents,
  isLoading,
  title = "Documents",
  subtitle = "",
  showViewAll = false,
}: DocumentTableProps) {
  const navigate = useNavigate();

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          {subtitle && (
            <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
          )}
        </div>
        {showViewAll && (
          <button
            onClick={() => navigate("/records")}
            className="text-xs font-medium text-teal-600 hover:text-teal-700 transition-colors"
          >
            View all →
          </button>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <svg
            className="w-5 h-5 animate-spin mr-2"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8z"
            />
          </svg>
          <span className="text-sm">Loading documents...</span>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && documents.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16">
          <svg
            className="w-10 h-10 mb-3 text-slate-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-sm font-medium text-slate-500">No documents yet</p>
          <p className="text-xs text-slate-400 mt-1">
            {title.toLowerCase().includes("review")
              ? "All documents have been reviewed"
              : "Upload a doctor's note to get started"}
          </p>
        </div>
      )}

      {/* Table rows */}
      {!isLoading && documents.length > 0 && (
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              {["Document", "Type", "Uploaded", "Status", "Action"].map(
                (h) => (
                  <th
                    key={h}
                    className="text-left text-[11px] font-medium text-slate-400 uppercase tracking-wider px-5 py-3"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {documents.map((doc) => (
              <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-5 py-3.5">
                  <p className="text-sm font-medium text-slate-900">
                    {doc.file_name}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    #{doc.upload_record_id}
                  </p>
                </td>
                <td className="px-5 py-3.5 text-sm text-slate-500">
                  {fileTypeLabel[doc.file_type] ?? doc.file_type}
                </td>
                <td className="px-5 py-3.5 text-sm text-slate-500">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-5 py-3.5">
                  <StatusBadge status={doc.review_status} />
                </td>
                <td className="px-5 py-3.5">
                  <ActionButton doc={doc} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}