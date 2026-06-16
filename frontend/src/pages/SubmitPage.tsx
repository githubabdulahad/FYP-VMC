import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileAudio, FileImage, FileText, FileType, Upload } from 'lucide-react';
import { submitUpload } from '@/api/ingestion';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { toApiError } from '@/api/client';
import { isCloudinaryConfigured, uploadToCloudinary } from '@/utils/cloudinary';
import type { FileType as Ft } from '@/types';

type InputMode = 'text' | 'pdf' | 'image' | 'audio';

const modes: { id: InputMode; label: string; icon: typeof FileText; fileType: Ft }[] = [
  { id: 'text', label: 'Clinical text', icon: FileText, fileType: 'raw_text' },
  { id: 'pdf', label: 'PDF', icon: FileType, fileType: 'pdf' },
  { id: 'image', label: 'Image', icon: FileImage, fileType: 'image' },
  { id: 'audio', label: 'Audio', icon: FileAudio, fileType: 'audio' },
];

export function SubmitPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<InputMode>('text');
  const [rawText, setRawText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const selected = modes.find((m) => m.id === mode)!;
  const needsFile = mode !== 'text';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let fileUrl = '';
      if (needsFile) {
        if (!file) {
          setError('Please select a file');
          setLoading(false);
          return;
        }
        if (!isCloudinaryConfigured()) {
          setError('Configure Cloudinary in Frontend/.env (see .env.example)');
          setLoading(false);
          return;
        }
        fileUrl = await uploadToCloudinary(file);
      }

      const record = await submitUpload({
        file_type: selected.fileType,
        file_url: needsFile ? fileUrl : undefined,
        file_name: needsFile ? file?.name : 'Direct text input',
        raw_text: mode === 'text' ? rawText : undefined,
      });

      navigate(`/processing/${record.id}`);
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">New submission</h1>
        <p className="mt-1 text-slate-400">
          Submit clinical notes — the pipeline will normalize, code, and validate automatically.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {modes.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setMode(id)}
            className={`rounded-xl border p-3 text-left transition ${
              mode === id
                ? 'border-teal-500/50 bg-teal-500/10 text-teal-200'
                : 'border-slate-700/40 bg-surface-900/50 text-slate-400 hover:border-slate-600'
            }`}
          >
            <Icon className="mb-2 h-5 w-5" />
            <span className="text-sm font-medium">{label}</span>
          </button>
        ))}
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'text' ? (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">Clinical text</label>
              <textarea
                className="min-h-[200px] w-full rounded-xl border border-slate-600/50 bg-surface-900 px-3 py-2.5 text-sm outline-none focus:border-teal-500/50"
                placeholder="Paste conversation transcript or clinical note…"
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                required
              />
            </div>
          ) : (
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-600/50 bg-surface-900/50 px-6 py-12 transition hover:border-teal-500/40">
              <Upload className="mb-3 h-10 w-10 text-slate-500" />
              <span className="text-sm text-slate-300">
                {file ? file.name : `Drop or click to upload ${labelForMode(mode)}`}
              </span>
              <input
                type="file"
                className="hidden"
                accept={acceptForMode(mode)}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          )}

          {!isCloudinaryConfigured() && needsFile && (
            <p className="text-xs text-amber-400/90">
              Cloudinary env vars missing — file upload will fail until you configure .env
            </p>
          )}

          {error && <p className="text-sm text-rose-400">{error}</p>}

          <Button type="submit" loading={loading} className="w-full sm:w-auto">
            Start processing
          </Button>
        </form>
      </Card>
    </div>
  );
}

function labelForMode(mode: InputMode) {
  return modes.find((m) => m.id === mode)?.label.toLowerCase() ?? 'file';
}

function acceptForMode(mode: InputMode) {
  switch (mode) {
    case 'pdf':
      return 'application/pdf';
    case 'image':
      return 'image/*';
    case 'audio':
      return 'audio/*';
    default:
      return '*/*';
  }
}
