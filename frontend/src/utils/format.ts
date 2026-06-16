export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso));
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—';
  return `${Math.round(value * 100)}%`;
}

export function fileTypeLabel(type: string): string {
  const map: Record<string, string> = {
    pdf: 'PDF',
    image: 'Image',
    audio: 'Audio',
    raw_text: 'Text',
  };
  return map[type] ?? type;
}

export function reviewStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: 'Needs review',
    approved: 'Approved',
    rejected: 'Rejected',
    revised: 'Revised',
  };
  return map[status] ?? status;
}
