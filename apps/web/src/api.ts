import type { MessagesResponse } from '@hamrakar/shared';

const ADMIN_BASE = '/api/admin';
const BALE_BASE = '/api/bale';
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN || '';

interface RequestOptions extends RequestInit {
  // allow passing custom base for non-admin endpoints
}

async function apiFetch<T>(base: string, path: string, options?: RequestOptions): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Token': ADMIN_TOKEN,
    },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

// Admin fetcher (for SWR and direct use)
async function fetcher<T>(url: string, options?: RequestInit): Promise<T> {
  return apiFetch<T>(ADMIN_BASE, url, options);
}

// SWR-compatible fetcher — generic so useSWR<Data> types flow correctly
export function swrFetcher<T>(url: string): Promise<T> {
  return fetcher<T>(url);
}

// ── Stats ──
export function getStats() {
  return fetcher('/stats');
}

// ── Users ──
export function getUsers() {
  return fetcher('/users');
}

// ── Jobs ──
export function getJobs() {
  return fetcher('/jobs');
}

export function approveJob(jobId: number) {
  return fetcher(`/approve-job/${jobId}`, { method: 'POST' });
}

export function rejectJob(jobId: number, reason?: string) {
  const query = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  return fetcher(`/reject-job/${jobId}${query}`, { method: 'POST' });
}

// ── Applications ──
export function getApplications() {
  return fetcher('/applications');
}

export function approveApplication(appId: number) {
  return fetcher(`/approve-application/${appId}`, { method: 'POST' });
}

export function rejectApplication(appId: number, reason?: string) {
  const query = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  return fetcher(`/reject-application/${appId}${query}`, { method: 'POST' });
}

// ── Resume Requests ──
export function getPendingResumeRequests() {
  return fetcher('/resume-requests/pending');
}

export function approveResumeRequest(reqId: number) {
  return fetcher(`/approve-resume-request/${reqId}`, { method: 'POST' });
}

export function rejectResumeRequest(reqId: number, reason?: string) {
  const query = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  return fetcher(`/reject-resume-request/${reqId}${query}`, { method: 'POST' });
}

// ── Settings ──
export function getWelcomeText() {
  return fetcher('/settings/welcome-text');
}

export function setWelcomeText(value: string) {
  return fetcher('/settings/welcome-text', {
    method: 'POST',
    body: JSON.stringify({ value }),
  });
}

// ── Messages (Phone Simulator) ──
export function getMessages(chatId: number, afterId?: number, limit = 50): Promise<MessagesResponse> {
  let url = `/messages?chat_id=${chatId}&limit=${limit}`;
  if (afterId != null) url += `&after_id=${afterId}`;
  return fetcher<MessagesResponse>(url);
}

// ── Bale Bot API (Phone Simulator) ──
// These go to /api/bale (the proxy's Bale router), not /api/admin
export function sendBaleMessage(chatId: number, text: string) {
  return apiFetch(BALE_BASE, '/sendMessage', {
    method: 'POST',
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}

export function getBaleMe() {
  return apiFetch(BALE_BASE, '/getMe');
}

// ── Broadcast ──
export function broadcastMessage(audience: 'all' | 'employer' | 'job_seeker', message: string) {
  return fetcher('/broadcast', {
    method: 'POST',
    body: JSON.stringify({ audience, message }),
  });
}
