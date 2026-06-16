import type { MedicalCode } from '@/types';
import { formatPercent } from '@/utils/format';
import { Trash2 } from 'lucide-react';

export function CodeTable({
  title,
  codes,
  accent = 'teal',
  onDeleteCode,
}: {
  title: string;
  codes: MedicalCode[];
  accent?: 'teal' | 'amber' | 'purple';
  onDeleteCode?: (code: string, type: 'icd' | 'cpt') => void;
}) {
  const accentClass =
    accent === 'amber' ? 'text-amber-300' : accent === 'purple' ? 'text-purple-300' : 'text-teal-300';

  if (!codes?.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-600/40 p-4 text-sm text-slate-500">
        No {title} codes
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-700/40">
      <div className={`border-b border-slate-700/40 bg-surface-800/80 px-4 py-2 text-sm font-semibold ${accentClass}`}>
        {title}
      </div>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-700/30 text-xs text-slate-500">
            <th className="px-4 py-2 font-medium">Code</th>
            <th className="px-4 py-2 font-medium">Description</th>
            <th className="px-4 py-2 font-medium">Conf.</th>
            {onDeleteCode && <th className="px-4 py-2 font-medium"></th>}
          </tr>
        </thead>
        <tbody>
          {codes.map((c, i) => (
            <tr
              key={`${c.code}-${i}`}
              className="border-b border-slate-800/80 last:border-0 hover:bg-surface-800/50"
            >
              <td className="px-4 py-2.5 font-mono text-teal-300">{c.code}</td>
              <td className="px-4 py-2.5 text-slate-300">{c.description ?? '—'}</td>
              <td className="px-4 py-2.5 text-slate-400">
                {c.confidence != null ? formatPercent(c.confidence) : '—'}
                {c.flagged && (
                  <span className="ml-2 rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] text-rose-300">
                    flagged
                  </span>
                )}
              </td>
              <td>
                {onDeleteCode && (
                  <button
                    type="button"
                    onClick={() => onDeleteCode(c.code, title.includes('ICD') ? 'icd' : 'cpt')}
                    className="text-slate-500 hover:text-rose-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
