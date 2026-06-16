const CLOUD = import.meta.env.VITE_CLOUDINARY_CLOUD_NAME;
const PRESET = import.meta.env.VITE_CLOUDINARY_UPLOAD_PRESET;
const FOLDER = import.meta.env.VITE_CLOUDINARY_FOLDER ?? 'medical-coder/uploads';

export function isCloudinaryConfigured(): boolean {
  return Boolean(CLOUD && PRESET);
}

export async function uploadToCloudinary(file: File): Promise<string> {
  if (!isCloudinaryConfigured()) {
    throw new Error(
      'Cloudinary is not configured. Add VITE_CLOUDINARY_CLOUD_NAME and VITE_CLOUDINARY_UPLOAD_PRESET to .env',
    );
  }

  const form = new FormData();
  form.append('file', file);
  form.append('upload_preset', PRESET!);
  form.append('folder', FOLDER);

  const res = await fetch(`https://api.cloudinary.com/v1_1/${CLOUD}/auto/upload`, {
    method: 'POST',
    body: form,
  });

  const data = (await res.json()) as { secure_url?: string; error?: { message: string } };
  if (!res.ok || !data.secure_url) {
    throw new Error(data.error?.message ?? 'Cloudinary upload failed');
  }
  return data.secure_url;
}
