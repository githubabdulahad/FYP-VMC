import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import DocumentTable from "../../../components/ui/DocumentTable";
import { getCodingResults } from "../api/recordsApi";
import type {  ReviewStatus } from "../../../types/document";

export default function AllRecordsPage() {
  const { data: allResults = [], isLoading } = useQuery({
    queryKey: ["codingResults"],
    queryFn: getCodingResults,
  });

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Filter state
  const [filterStatus, setFilterStatus] = useState<ReviewStatus | "all">("all");

  // Filter documents
  const filteredDocs = allResults.filter((doc) =>
    filterStatus === "all" ? true : doc.review_status === filterStatus
  );

  // Paginate
  const totalPages = Math.ceil(filteredDocs.length / pageSize);
  const startIdx = (currentPage - 1) * pageSize;
  const paginatedDocs = filteredDocs.slice(startIdx, startIdx + pageSize);

  // Reset to page 1 when filter changes
  const handleFilterChange = (status: ReviewStatus | "all") => {
    setFilterStatus(status);
    setCurrentPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Heading */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900">All Records</h2>
        <p className="text-sm text-slate-400 mt-0.5">
          Complete list of all documents and their coding status
        </p>
      </div>

      {/* Filter buttons */}
      <div className="flex gap-2 flex-wrap">
        {(
          [
            { value: "all" as const, label: "All" },
            { value: "pending" as const, label: "Pending Review" },
            { value: "approved" as const, label: "Approved" },
            { value: "rejected" as const, label: "Rejected" },
            { value: "revised" as const, label: "Revised" },
          ] as const
        ).map(({ value, label }) => (
          <button
            key={value}
            onClick={() => handleFilterChange(value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filterStatus === value
                ? "bg-teal-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {label}
            {value !== "all" && (
              <span className="ml-2 text-[10px] opacity-75">
                ({allResults.filter((d) => d.review_status === value).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <DocumentTable
        documents={paginatedDocs}
        isLoading={isLoading}
        title={`${filterStatus === "all" ? "All Documents" : filterStatus.charAt(0).toUpperCase() + filterStatus.slice(1)}`}
        subtitle={`Showing ${startIdx + 1}–${Math.min(startIdx + pageSize, filteredDocs.length)} of ${filteredDocs.length} document${filteredDocs.length !== 1 ? "s" : ""}`}
        showViewAll={false}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-xl">
          <p className="text-xs text-slate-500">
            Page <span className="font-semibold">{currentPage}</span> of{" "}
            <span className="font-semibold">{totalPages}</span>
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              ← Previous
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-medium hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}