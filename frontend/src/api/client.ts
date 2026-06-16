import type { ApiError } from '@/types';

const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';

export class HttpError extends Error {
  status: number;
  details?: Record<string, unknown>;

  constructor(status: number, message: string, details?: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

async function parseBody<T>(response: Response): Promise<T | undefined> {
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as T;
  } catch {
    return undefined;
  }
}

function flattenErrors(data: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value)) {
      parts.push(`${key}: ${value.join(', ')}`);
    } else if (typeof value === 'string') {
      parts.push(key === 'detail' || key === 'error' ? value : `${key}: ${value}`);
    }
  }
  return parts.join(' · ') || 'Request failed';
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers = new Headers(options.headers);

  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });

  const data = await parseBody<Record<string, unknown>>(response);

  if (!response.ok) {
    const message =
      (data && (typeof data.detail === 'string' ? data.detail : flattenErrors(data))) ||
      response.statusText;
    throw new HttpError(response.status, message, data);
  }

  return data as T;
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof HttpError) {
    return { message: err.message, details: err.details as ApiError['details'] };
  }
  if (err instanceof Error) return { message: err.message };
  return { message: 'Something went wrong' };
}
