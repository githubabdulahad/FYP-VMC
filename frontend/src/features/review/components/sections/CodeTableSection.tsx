import { useState } from "react";

interface CodeTableSectionProps {
  title: string;
  codes: Array<{
    code: string;
    description: string;
    confidence: number;
    evidence_text?: string;
    needs_review?: boolean;
  }>;
  system: "ICD10" | "CPT";
  onDeleteCode: (code: string) => Promise<void>;
  onGetSuggestions?: (code: string, evidenceText?: string) => void;
  isDeleting: boolean;
}

export default function CodeTableSection({
  title,
  codes,
  system,
  onDeleteCode,
  onGetSuggestions,
  isDeleting,
}: CodeTableSectionProps) {
  const [deletingCode, setDeletingCode] = useState<string | null>(null);

  const handleDelete = async (code: string) => {
    setDeletingCode(code);
    try {
      await onDeleteCode(code);
    } finally {
      setDeletingCode(null);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-200 bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      </div>

      {codes.length === 0 ? (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <p className="text-sm">
            No {system === "ICD10" ? "ICD" : "CPT"} codes
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">
                  Code
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">
                  Description
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">
                  Confidence
                </th>
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase">
                  Evidence
                </th>
                <th className="text-center px-5 py-3 text-xs font-medium text-slate-500 uppercase">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {codes.map((code) => (
                <tr key={code.code} className="hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <span className="font-medium text-slate-900">
                      {code.code}
                    </span>
                    {code.needs_review && (
                      <span className="ml-2 text-xs px-2 py-1 rounded-full bg-amber-50 text-amber-700 font-medium">
                        ⚠️ Needs Review
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-slate-700">
                    {code.description}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-12 bg-slate-200 rounded-full h-1.5">
                        <div
                          className="bg-teal-600 h-1.5 rounded-full"
                          style={{ width: `${(code.confidence || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-slate-600">
                        {Math.round((code.confidence || 0) * 100)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <p className="text-xs text-slate-500 max-w-xs truncate">
                      {code.evidence_text || "—"}
                    </p>
                  </td>
                  <td className="px-5 py-3 text-center">
                    <div className="flex gap-2 justify-center">
                      {onGetSuggestions && (
                        <button
                          onClick={() =>
                            onGetSuggestions(code.code, code.evidence_text)
                          }
                          className="text-xs font-medium text-teal-600 hover:text-teal-700"
                        >
                          Suggest
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(code.code)}
                        disabled={isDeleting || deletingCode === code.code}
                        className="text-xs font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
                      >
                        {deletingCode === code.code ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}