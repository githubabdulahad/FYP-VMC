export default function ReviewLoading() {
  return (
    <div className="flex items-center justify-center py-20">
      <svg
        className="w-6 h-6 animate-spin text-teal-600"
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
      <span className="ml-2 text-slate-600">Loading document...</span>
    </div>
  );
}