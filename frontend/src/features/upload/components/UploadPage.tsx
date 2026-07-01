/* eslint-disable @typescript-eslint/no-unused-vars */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { FileType } from "../../../types/document";
import {
  uploadToCloudinary,
  createUploadRecord,
  getUploadStatus,
} from "../api/uploadApi";

export default function UploadPage() {
  const navigate = useNavigate();

  // --- Form state ---
  const [fileType, setFileType] = useState<FileType>("raw_text");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [rawText, setRawText] = useState("");

  // --- Process state ---
  const [uploadId, setUploadId] = useState<number | null>(null);
  const [stage, setStage] = useState<"idle" | "uploading" | "submitting" | "polling" | "failed"
  >("idle");
  const [error, setError] = useState<string | null>(null);

  // --- Polling ---
  // This query only runs when uploadId exists (we have a record to poll)
  // refetchInterval keeps re-running every 3 seconds automatically
  const { data: statusData } = useQuery({
    queryKey: ["uploadStatus", uploadId],
    queryFn: () => getUploadStatus(uploadId!),
    enabled: stage === "polling" && uploadId !== null,
    refetchInterval: 3000,
  });

  // --- React to polling results ---
  // Only navigate is here — navigate() is a true external side effect (fine in useEffect)
  // setStage/setError are removed from here to avoid cascading renders
  useEffect(() => {
    if (statusData?.status === "completed") {
      navigate("/review-queue");
    }
  }, [statusData, navigate]);

  // --- Derive failed state directly from statusData ---
  // Instead of syncing statusData → state via useEffect, we compute it during render
  const processingFailed =
    stage === "polling" && statusData?.status === "failed";

  const effectiveError = processingFailed
    ? statusData?.error_message || "Processing failed. Please try again."
    : error;

  // --- Form submission handler ---
  async function handleSubmit() {
    // Basic validation
    if (fileType === "raw_text" && !rawText.trim()) {
      setError("Please enter some text.");
      return;
    }
    if (fileType !== "raw_text" && !selectedFile) {
      setError("Please select a file.");
      return;
    }

    setError(null);

    try {
      let fileUrl: string | undefined;
      let fileName: string | undefined;

      // Step 1: if it's a file, upload to Cloudinary first
      if (fileType !== "raw_text" && selectedFile) {
        setStage("uploading");
        fileUrl = await uploadToCloudinary(selectedFile);
        fileName = selectedFile.name;
      }

      // Step 2: send the record to Django
      setStage("submitting");
      const record = await createUploadRecord({
        file_type: fileType,
        ...(fileType === "raw_text"
          ? { raw_text: rawText }
          : { file_url: fileUrl, file_name: fileName }),
      });

      // Step 3: start polling with the returned ID
      setUploadId(record.id);
      setStage("polling");
    } catch (err) {
      setStage("failed");
      setError("Something went wrong. Please try again.");
    }
  }

  // --- Derived helpers ---
  // isLoading is false when failed (including processingFailed) so the button re-enables
  const isLoading =
    stage !== "idle" && stage !== "failed" && !processingFailed;

  const stageLabel = {
    idle: "",
    uploading: "Uploading file to cloud...",
    submitting: "Sending to server...",
    polling: "Processing your document... this may take a minute.",
    failed: "",
  }[stage];

  // --- Accepted file types per input type ---
  const acceptMap: Record<string, string> = {
    pdf: ".pdf",
    image: ".png,.jpg,.jpeg,.webp",
    audio: "audio/*",
  };

  return (
    <div className="max-w-2xl mx-auto py-10 px-4">
      <h1 className="text-2xl font-semibold text-slate-800 mb-1">
        Upload Clinical Note
      </h1>
      <p className="text-slate-500 mb-8">
        Upload a file or paste raw text to begin AI-assisted medical coding.
      </p>

      {/* Input type selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Input Type
        </label>
        <div className="flex gap-3 flex-wrap">
          {(["raw_text", "pdf", "image", "audio"] as FileType[]).map((type) => (
            <button
              key={type}
              onClick={() => {
                setFileType(type);
                setSelectedFile(null);
                setError(null);
              }}
              disabled={isLoading}
              className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors
                ${
                  fileType === type
                    ? "bg-teal-600 text-white border-teal-600"
                    : "bg-white text-slate-600 border-slate-300 hover:border-teal-400"
                }`}
            >
              {type === "raw_text" ? "Raw Text" : type.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Conditional input area */}
      {fileType === "raw_text" ? (
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Clinical Note Text
          </label>
          <textarea
            rows={10}
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            disabled={isLoading}
            placeholder="Paste or type the clinical note here..."
            className="w-full border border-slate-300 rounded-lg px-4 py-3 text-sm text-slate-800 
                       placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500
                       disabled:bg-slate-50 disabled:text-slate-400 resize-none"
          />
        </div>
      ) : (
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Select File
          </label>
          <div
            className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center
                          hover:border-teal-400 transition-colors"
          >
            <input
              type="file"
              accept={acceptMap[fileType]}
              disabled={isLoading}
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                setSelectedFile(file);
                setError(null);
              }}
              className="hidden"
              id="file-input"
            />
            <label htmlFor="file-input" className="cursor-pointer">
              <p className="text-slate-500 text-sm">
                {selectedFile
                  ? selectedFile.name
                  : `Click to select a ${fileType.toUpperCase()} file`}
              </p>
              {selectedFile && (
                <p className="text-xs text-slate-400 mt-1">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              )}
            </label>
          </div>
        </div>
      )}

      {/* Error message — uses effectiveError to cover both local and processing errors */}
      {effectiveError && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {effectiveError}
        </div>
      )}

      {/* Status message while processing */}
      {isLoading && (
        <div className="mb-4 px-4 py-3 bg-teal-50 border border-teal-200 rounded-lg text-sm text-teal-700 flex items-center gap-2">
          <svg
            className="animate-spin h-4 w-4 text-teal-600"
            viewBox="0 0 24 24"
            fill="none"
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
          {stageLabel}
        </div>
      )}

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={isLoading}
        className="w-full py-3 bg-teal-600 text-white rounded-lg font-medium text-sm
                   hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? "Processing..." : "Submit for Coding"}
      </button>
    </div>
  );
}