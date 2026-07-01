import type { CodingResult } from "../../../../types/document";

export default function SOAPNoteSection({
  soap,
}: {
  soap: CodingResult["soap_note"];
}) {
  const sections = [
    { key: "subjective" as const, label: "Subjective" },
    { key: "objective" as const, label: "Objective" },
    { key: "assessment" as const, label: "Assessment" },
    { key: "plan" as const, label: "Plan" },
  ];

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-4">SOAP Note</h3>
      <div className="grid grid-cols-2 gap-4">
        {sections.map(({ key, label }) => (
          <div key={key} className="bg-slate-50 rounded-lg p-4">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
              {label}
            </p>
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
              {soap[key] || "—"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}