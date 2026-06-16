import type { SoapNote } from '@/types';

const sections: { key: keyof SoapNote; label: string; color: string }[] = [
  { key: 'subjective', label: 'Subjective', color: 'border-l-teal-500' },
  { key: 'objective', label: 'Objective', color: 'border-l-sky-500' },
  { key: 'assessment', label: 'Assessment', color: 'border-l-purple-500' },
  { key: 'plan', label: 'Plan', color: 'border-l-amber-500' },
];

export function SoapPanel({ soap }: { soap: SoapNote }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {sections.map(({ key, label, color }) => (
        <div
          key={key}
          className={`rounded-xl border border-slate-700/40 bg-surface-900/60 p-4 border-l-4 ${color}`}
        >
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {label}
          </h4>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
            {(soap[key] as string) || '—'}
          </p>
        </div>
      ))}
    </div>
  );
}
