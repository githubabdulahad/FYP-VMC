import { apiRequest } from './client';
import type { Report } from '@/types';

export async function listReports() {
  return apiRequest<Report[]>('/api/reports/');
}

export async function getReport(id: number) {
  return apiRequest<Report>(`/api/reports/${id}/`);
}
