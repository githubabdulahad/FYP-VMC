export interface SuggestionsModalProps {
  isOpen: boolean;
  isLoading: boolean;
  suggestions: Array<{ code: string; description: string; score: number }>;
  onClose: () => void;
  onSelect: (suggestion: { code: string; description: string }) => void;
}

export default function SuggestionsModal({
  isOpen,
  isLoading,
  suggestions,
  onClose,
  onSelect,
}: SuggestionsModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-lg max-w-md w-full">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">
            Alternative Suggestions
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <svg
                className="w-5 h-5 animate-spin text-teal-600 mr-2"
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
              <span className="text-sm text-slate-600">Fetching suggestions...</span>
            </div>
          ) : suggestions.length === 0 ? (
            <p className="text-sm text-slate-500 py-8 text-center">
              No alternative suggestions found
            </p>
          ) : (
            <div className="space-y-3">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion.code}
                  onClick={() => {
                    onSelect(suggestion);
                    onClose();
                  }}
                  className="w-full p-3 border border-slate-200 rounded-lg hover:bg-teal-50 hover:border-teal-300 transition-colors text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900">
                        {suggestion.code}
                      </p>
                      <p className="text-xs text-slate-600 mt-1 leading-tight">
                        {suggestion.description}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-xs font-medium text-teal-600">
                        {Math.round(suggestion.score * 100)}%
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 rounded-b-xl">
          <button
            onClick={onClose}
            className="w-full py-2 text-sm font-medium text-slate-700 hover:text-slate-900"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}