import clsx from 'clsx';

const toneMap: Record<string, string> = {
  pending: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  processing: 'bg-purple-500/15 text-purple-300 ring-purple-500/30',
  completed: 'bg-teal-500/15 text-teal-300 ring-teal-500/30',
  failed: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  approved: 'bg-teal-500/15 text-teal-300 ring-teal-500/30',
  revised: 'bg-sky-500/15 text-sky-300 ring-sky-500/30',
  rejected: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
};

export function Badge({
  children,
  tone = 'pending',
  className,
}: {
  children: React.ReactNode;
  tone?: string;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        toneMap[tone] ?? 'bg-slate-500/15 text-slate-300 ring-slate-500/30',
        className,
      )}
    >
      {children}
    </span>
  );
}
