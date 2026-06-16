import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Download, Printer } from 'lucide-react';
import { getReport } from '@/api/reports';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { CodeTable } from '@/components/coding/CodeTable';
import { SoapPanel } from '@/components/coding/SoapPanel';
import { formatDate, formatPercent, reviewStatusLabel } from '@/utils/format';

export function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const reportId = Number(id);

  const { data: report, isLoading, isError } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => getReport(reportId),
    enabled: Number.isFinite(reportId),
  });

  const downloadJson = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `medical-report-${report.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const printReport = () => window.print();

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (isError || !report) return <p className="text-rose-400">Report not found</p>;

  return (
    <div className="space-y-6 print:text-black">
      <div className="flex flex-wrap items-start justify-between gap-4 print:hidden">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-sky-400">Verified report</p>
          <h1 className="text-3xl font-bold text-white">{report.file_name}</h1>
          <p className="mt-1 text-slate-400">
            {reviewStatusLabel(report.review_status)} · {formatDate(report.created_at)}
            {report.confidence != null && ` · ${formatPercent(report.confidence)} confidence`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" type="button" onClick={printReport}>
            <Printer className="h-4 w-4" />
            Print
          </Button>
          <Button type="button" onClick={downloadJson}>
            <Download className="h-4 w-4" />
            Download
          </Button>
        </div>
      </div>

      <Card className="print:border print:bg-white print:text-black">
        <h2 className="mb-2 text-lg font-semibold text-white print:text-black">Clinical summary</h2>
        <p className="whitespace-pre-wrap text-sm text-slate-300 print:text-gray-800">{report.summary || '—'}</p>
      </Card>

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-white print:text-black">SOAP note</h2>
        <SoapPanel soap={report.soap_note} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <CodeTable title="ICD-10" codes={report.icd_codes} />
        <CodeTable title="CPT" codes={report.cpt_codes} />
      </div>

      {report.extracted_text && (
        <Card>
          <h2 className="mb-2 text-sm font-semibold text-slate-400">Source text</h2>
          <p className="max-h-48 overflow-y-auto whitespace-pre-wrap text-xs text-slate-500">
            {report.extracted_text}
          </p>
        </Card>
      )}
    </div>
  );
}
