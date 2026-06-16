import { apiRequest } from './client';
import type { User } from '@/types';

export async function login(username: string, password: string) {
  return apiRequest<{ message: string; user: User }>('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function register(payload: {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
}) {
  return apiRequest<{ message: string; user: User }>('/api/auth/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function logout() {
  return apiRequest<{ message: string }>('/api/auth/logout/', { method: 'POST' });
}

export async function refreshToken() {
  return apiRequest<{ message: string }>('/api/auth/refresh/', { method: 'POST' });
}

export async function getMe() {
  return apiRequest<{ user: User }>('/api/auth/me/');
}
