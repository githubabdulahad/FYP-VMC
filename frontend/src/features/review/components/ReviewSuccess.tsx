import { useNavigate } from "react-router-dom";
import type { CodingResult } from "../../../types/document";

interface ReviewSuccessProps {
  currentDoc: CodingResult;
  status: "approved" | "rejected";
  nextPending: CodingResult | undefined;
}

export default function ReviewSuccess({
  currentDoc,
  status,
  nextPending,
}: ReviewSuccessProps) {
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="bg-teal-50 border border-teal-200 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <svg
            className="w-6 h-6 text-teal-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            />
          </svg>
          <div>
            <p className="font-semibold text-teal-900">
              Document {status === "approved" ? "Approved" : "Rejected"}
            </p>
            <p className="text-sm text-teal-700">
              {currentDoc.file_name} has been{" "}
              {status === "approved" ? "approved" : "rejected"}.
            </p>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-teal-200">
          {nextPending ? (
            <button
              onClick={() => navigate(`/review/${nextPending.id}`)}
              className="flex-1 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-colors"
            >
              Next Review →
            </button>
          ) : (
            <button
              onClick={() => navigate("/review-queue")}
              className="flex-1 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-colors"
            >
              Back to Review Queue
            </button>
          )}
          <button
            onClick={() => navigate("/dashboard")}
            className="flex-1 py-2 bg-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-300 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}