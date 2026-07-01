/* eslint-disable @typescript-eslint/no-unused-vars */
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  getCodingDetail,
  getCodingResults,
  submitReview,
  deleteCode,
  getReportData,
  getAlternativeCodeSuggestions,
} from "../api/reviewApi";
import { generatePDF } from "../utils/pdfGenerator";
import StatusBadge from "../../../components/ui/Statusbadge";
import SOAPNoteSection from "./sections/SOAPNoteSection";
import CodeTableSection from "./sections/CodeTableSection";
import ActionButtonsSection from "./sections/ActionButtonsSection";
import ReviewSuccess from "./Reviewsuccess";
import ReviewLoading from "./ReviewLoading";
import SuggestionsModal from "./modals/SuggestionsModal";

export default function ReviewDetail() {
  const queryClient = useQueryClient();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const codingId = parseInt(id || "0", 10);

  // Queries
  const { data: currentDoc, isLoading: isLoadingDetail } = useQuery({
    queryKey: ["codingDetail", codingId],
    queryFn: () => getCodingDetail(codingId),
  });

  const { data: allDocs = [] } = useQuery({
    queryKey: ["codingResults"],
    queryFn: getCodingResults,
  });

  // State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successData, setSuccessData] = useState<{
    documentId: number;
    status: "approved" | "rejected";
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [suggestionsModal, setSuggestionsModal] = useState<{
    isOpen: boolean;
    codeType: "ICD10" | "CPT" | null;
    currentCode: string;
    suggestions: Array<{ code: string; description: string; score: number }>;
    isLoading: boolean;
  } | null>(null);

  // Handlers
  const handleDeleteCode = async (code: string) => {
    if (!currentDoc) return;
    try {
      const codeType = currentDoc.icd_codes?.some((c) => c.code === code)
        ? "icd"
        : "cpt";
      await deleteCode(codingId, { code, type: codeType });
      await queryClient.invalidateQueries({
        queryKey: ["codingDetail", codingId],
      });
    } catch (err) {
      setErrorMsg("Failed to delete code. Please try again.");
    }
  };

  const handleGetSuggestions = async (
    code: string,
    system: "ICD10" | "CPT",
    evidenceText?: string
  ) => {
    if (!evidenceText) {
      setErrorMsg("No evidence text available for this code");
      return;
    }

    setSuggestionsModal({
      isOpen: true,
      codeType: system,
      currentCode: code,
      suggestions: [],
      isLoading: true,
    });

    try {
      const result = await getAlternativeCodeSuggestions(codingId, {
        system,
        evidence_text: evidenceText,
      });
      setSuggestionsModal((prev) =>
        prev ? { ...prev, suggestions: result.candidates, isLoading: false } : null
      );
    } catch (err) {
      setErrorMsg("Failed to fetch suggestions. Please try again.");
      setSuggestionsModal(null);
    }
  };

  const handleSelectSuggestion = (suggestion: {
    code: string;
    description: string;
  }) => {
    setErrorMsg(`Selected: ${suggestion.code} - ${suggestion.description}`);
  };

  const handleDownloadPDF = async () => {
    if (!currentDoc) return;
    try {
      setIsSubmitting(true);
      const reportData = await getReportData(codingId);
      generatePDF(reportData, `${currentDoc.file_name}-report.pdf`);
    } catch (err) {
      setErrorMsg("Failed to download PDF. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitReview = async (status: "approved" | "rejected") => {
    if (!currentDoc) return;
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      await submitReview(codingId, {
        review_status: status,
        review_notes: "",
      });
      await queryClient.invalidateQueries({
        queryKey: ["codingDetail", codingId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["codingResults"],
      });
      setSuccessData({ documentId: codingId, status });
    } catch (err) {
      setErrorMsg("Failed to submit review. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Loading
  if (isLoadingDetail) return <ReviewLoading />;

  if (!currentDoc) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-slate-600 mb-4">Document not found</p>
        <button
          onClick={() => navigate("/review-queue")}
          className="text-teal-600 hover:text-teal-700 font-medium text-sm"
        >
          Back to Review Queue →
        </button>
      </div>
    );
  }

  // Success
  const nextPending = allDocs.find(
    (doc) => doc.review_status === "pending" && doc.id !== codingId
  );

  if (successData && successData.documentId === codingId) {
    return (
      <ReviewSuccess
        currentDoc={currentDoc}
        status={successData.status}
        nextPending={nextPending}
      />
    );
  }

  // Main content
  return (
    <div className="max-w-4xl mx-auto py-10 px-4 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            {currentDoc.file_name}
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <StatusBadge status={currentDoc.review_status} />
            <p className="text-xs text-slate-500">#{currentDoc.id}</p>
          </div>
        </div>
        <button
          onClick={() => navigate("/review-queue")}
          className="text-slate-600 hover:text-slate-800"
        >
          ✕
        </button>
      </div>

      {/* Error */}
      {errorMsg && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {/* Sections */}
      <SOAPNoteSection soap={currentDoc.soap_note} />

      <CodeTableSection
        title="ICD-10 Diagnosis Codes"
        codes={currentDoc.icd_codes || []}
        system="ICD10"
        onDeleteCode={handleDeleteCode}
        onGetSuggestions={(code, evidence) =>
          handleGetSuggestions(code, "ICD10", evidence)
        }
        isDeleting={isSubmitting}
      />

      <CodeTableSection
        title="CPT Procedure Codes"
        codes={currentDoc.cpt_codes || []}
        system="CPT"
        onDeleteCode={handleDeleteCode}
        onGetSuggestions={(code, evidence) =>
          handleGetSuggestions(code, "CPT", evidence)
        }
        isDeleting={isSubmitting}
      />

      <ActionButtonsSection
        currentDoc={currentDoc}
        isSubmitting={isSubmitting}
        onApprove={() => handleSubmitReview("approved")}
        onReject={() => handleSubmitReview("rejected")}
        onDownloadPDF={handleDownloadPDF}
      />

      {/* Modal */}
      {suggestionsModal && (
        <SuggestionsModal
          isOpen={suggestionsModal.isOpen}
          isLoading={suggestionsModal.isLoading}
          suggestions={suggestionsModal.suggestions}
          onClose={() => setSuggestionsModal(null)}
          onSelect={handleSelectSuggestion}
        />
      )}
    </div>
  );
}