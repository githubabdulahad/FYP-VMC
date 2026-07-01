import type { CodingResult } from "../../../../types/document";

interface ActionButtonsSectionProps {
  currentDoc: CodingResult;
  isSubmitting: boolean;
  onApprove: () => void;
  onReject: () => void;
  onDownloadPDF: () => void;
}

export default function ActionButtonsSection({
  currentDoc,
  isSubmitting,
  onApprove,
  onReject,
  onDownloadPDF,
}: ActionButtonsSectionProps) {
  return (
    <>
      {/* Download button for approved documents */}
      {(currentDoc.review_status === "approved" ||
        currentDoc.review_status === "revised") && (
        <button
          onClick={onDownloadPDF}
          disabled={isSubmitting}
          className="w-full py-3 bg-slate-600 text-white rounded-lg font-medium text-sm
                     hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Download PDF Report
        </button>
      )}

      {/* Approve/Reject buttons */}
      {currentDoc.review_status === "pending" && (
        <div className="flex gap-3 sticky bottom-4">
          <button
            onClick={onReject}
            disabled={isSubmitting}
            className="flex-1 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Processing..." : "Reject"}
          </button>
          <button
            onClick={onApprove}
            disabled={isSubmitting}
            className="flex-1 py-3 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Processing..." : "Approve"}
          </button>
        </div>
      )}
    </>
  );
}