import { useQuery } from "@tanstack/react-query";
import DocumentTable from "../../../components/ui/DocumentTable";
import { getCodingResults } from "../api/reviewApi";
import type { CodingResult } from "../../../types/document";

export default function ReviewQueuePage() {
  const { data: allResults = [], isLoading } = useQuery({
    queryKey: ["codingResults"],
    queryFn: getCodingResults,
  });

  // Filter to only pending documents
  const pendingDocs: CodingResult[] = allResults.filter(
    (result) => result.review_status === "pending"
  );

  return (
    <div className="space-y-6">
      {/* Heading */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Review Queue</h2>
        <p className="text-sm text-slate-400 mt-0.5">
          Documents awaiting your review
        </p>
      </div>

      {/* Table — no stats, no limit */}
      <DocumentTable
        documents={pendingDocs}
        isLoading={isLoading}
        title="Pending Documents"
        subtitle={`${pendingDocs.length} document${pendingDocs.length !== 1 ? "s" : ""} ready for review`}
        showViewAll={false}
      />
    </div>
  );
}