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
  getReviewFeedbackHistory,
  addCodeToResult,
} from "../api/reviewApi";
import { generatePDF } from "../utils/pdfGenerator";
import StatusBadge from "../../../components/ui/Statusbadge";
import SOAPNoteSection from "./sections/SOAPNoteSection";
import CodeTableSection from "./sections/CodeTableSection";
import ActionButtonsSection from "./sections/ActionButtonsSection";
import ReviewSuccess from "./ReviewSuccess";
import ReviewLoading from "./ReviewLoading";
import SuggestionsModal from "./modals/SuggestionsModal";

interface ReviewFeedbackEntry {
  id: number;
  reviewer_username: string;
  llm_codes: unknown[];
  corrected_codes: unknown[];
  feedback_type: string;
  explanation: string;
  created_at: string;
}

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

  const { data: feedbackHistory = [] } = useQuery<ReviewFeedbackEntry[]>({
    queryKey: ["reviewFeedback", codingId],
    queryFn: () => getReviewFeedbackHistory(codingId),
    enabled: codingId > 0,
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
  const [manualCodeType, setManualCodeType] = useState<"icd" | "cpt">("icd");
  const [manualCode, setManualCode] = useState("");
  const [manualDescription, setManualDescription] = useState("");
  const [manualEvidenceText, setManualEvidenceText] = useState("");
  const [manualCodeMessage, setManualCodeMessage] = useState<string | null>(null);

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

  const handleAddManualCode = async () => {
    if (!manualCode.trim() || !manualDescription.trim()) {
      setErrorMsg("Code and description are required to add a manual code.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setManualCodeMessage(null);

    try {
      const response = await addCodeToResult(codingId, {
        type: manualCodeType,
        code: manualCode.trim(),
        description: manualDescription.trim(),
        evidence_text: manualEvidenceText.trim(),
      });

      setManualCodeMessage(response.message || "Code added successfully.");
      setManualCode("");
      setManualDescription("");
      setManualEvidenceText("");
      await queryClient.invalidateQueries({ queryKey: ["codingDetail", codingId] });
      await queryClient.invalidateQueries({ queryKey: ["reviewFeedback", codingId] });
    } catch (err) {
      setErrorMsg("Failed to add code. Please try again.");
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

      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Manual Code Add</h3>
          <p className="text-xs text-slate-500 mt-1">
            Wire to the backend add-code endpoint when the AI misses a code.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-2 block">
            <span className="block text-xs font-medium text-slate-700">Code type</span>
            <select
              value={manualCodeType}
              onChange={(e) => setManualCodeType(e.target.value as "icd" | "cpt")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="icd">ICD-10</option>
              <option value="cpt">CPT</option>
            </select>
          </label>
          <label className="space-y-2 block">
            <span className="block text-xs font-medium text-slate-700">Code</span>
            <input
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="E11.9"
            />
          </label>
        </div>

        <label className="space-y-2 block">
          <span className="block text-xs font-medium text-slate-700">Description</span>
          <input
            value={manualDescription}
            onChange={(e) => setManualDescription(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Type 2 diabetes mellitus without complications"
          />
        </label>

        <label className="space-y-2 block">
          <span className="block text-xs font-medium text-slate-700">Evidence text</span>
          <textarea
            value={manualEvidenceText}
            onChange={(e) => setManualEvidenceText(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm resize-none"
            placeholder="Optional supporting evidence from the chart"
          />
        </label>

        {manualCodeMessage && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {manualCodeMessage}
          </div>
        )}

        <button
          onClick={handleAddManualCode}
          disabled={isSubmitting}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : "Add code"}
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Review Feedback History</h3>
          <p className="text-xs text-slate-500 mt-1">
            History from the backend review-feedback endpoint.
          </p>
        </div>

        {feedbackHistory.length === 0 ? (
          <p className="text-sm text-slate-500">No feedback history yet.</p>
        ) : (
          <div className="space-y-3">
            {feedbackHistory.map((entry: ReviewFeedbackEntry) => (
              <div key={entry.id} className="rounded-lg border border-slate-200 p-4 text-sm">
                <div className="flex flex-wrap gap-2 items-center justify-between">
                  <p className="font-medium text-slate-900">{entry.feedback_type}</p>
                  <p className="text-xs text-slate-500">{entry.reviewer_username} · {entry.created_at}</p>
                </div>
                <p className="mt-2 text-slate-600">{entry.explanation || "No explanation provided."}</p>
              </div>
            ))}
          </div>
        )}
      </div>

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