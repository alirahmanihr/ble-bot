import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.js';
import { mockStats, mockUsers, mockJobs, mockApplications, mockWelcomeText, mockMessages } from '../mock.js';

export const adminRouter = Router();

// All admin routes require auth
adminRouter.use(authMiddleware);

// Track whether Railway is alive so we can skip retries when down
let railwayDown = false;
let lastRailwayCheck = 0;

function getRailwayUrl(): string {
  return process.env.RAILWAY_API_URL || 'http://localhost:8000';
}

function getAdminToken(): string {
  return process.env.ADMIN_TOKEN || '';
}

// Helper to proxy requests to Railway
async function proxyToRailway(method: string, path: string, body?: unknown) {
  const url = `${getRailwayUrl()}${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const adminToken = getAdminToken();
  if (adminToken) {
    headers['X-Admin-Token'] = adminToken;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000); // 5s — mock fallback kicks in quickly

  const options: RequestInit = {
    method,
    headers,
    signal: controller.signal,
  };

  if (body && method !== 'GET') {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    clearTimeout(timeout);
    railwayDown = false;
    lastRailwayCheck = Date.now();
    const data = await response.json();
    return { status: response.status, data };
  } catch (err: any) {
    clearTimeout(timeout);
    throw err;
  }
}

// Returns mock data if Railway is unreachable (throws on Railway error to trigger fallback)
async function withFallback<T>(railwayCall: () => Promise<T>, mockData: T): Promise<T> {
  // If Railway was down and last check was < 30s ago, skip retry
  if (railwayDown && Date.now() - lastRailwayCheck < 30000) {
    return mockData;
  }
  try {
    const result = await railwayCall();
    return result;
  } catch {
    railwayDown = true;
    lastRailwayCheck = Date.now();
    console.log('⚠️  Railway unreachable — serving mock data');
    return mockData;
  }
}

// ── Stats ──
adminRouter.get('/stats', async (_req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('GET', '/stats'); return data; },
      mockStats,
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: `Railway unreachable: ${err.message}` });
  }
});

// ── Users ──
adminRouter.get('/users', async (_req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('GET', '/users'); return data; },
      { count: mockUsers.length, users: mockUsers },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Jobs ──
adminRouter.get('/jobs', async (_req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('GET', '/jobs'); return data; },
      { count: mockJobs.length, jobs: mockJobs },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/approve-job/:id', async (req, res) => {
  try {
    const jobId = parseInt(req.params.id);
    const idx = mockJobs.findIndex(j => j.job_id === jobId);
    if (idx !== -1) mockJobs[idx] = { ...mockJobs[idx], status: 'active' as const, admin_approved: 1 };
    // Try Railway, fall back to mock success
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', `/approve-job/${req.params.id}`); return data; },
      { ok: true, message: 'آگهی تأیید شد (mock)' },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/reject-job/:id', async (req, res) => {
  try {
    const reason = (req.query.reason as string) || '';
    const jobId = parseInt(req.params.id);
    const idx = mockJobs.findIndex(j => j.job_id === jobId);
    if (idx !== -1) mockJobs[idx] = { ...mockJobs[idx], status: 'rejected' as const, reject_reason: reason };
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', `/reject-job/${req.params.id}?reason=${encodeURIComponent(reason)}`); return data; },
      { ok: true, message: 'آگهی رد شد (mock)' },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Applications ──
adminRouter.get('/applications', async (_req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('GET', '/applications'); return data; },
      { count: mockApplications.length, applications: mockApplications },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/approve-application/:id', async (req, res) => {
  try {
    const appId = parseInt(req.params.id);
    const idx = mockApplications.findIndex(a => a.app_id === appId);
    if (idx !== -1) mockApplications[idx] = { ...mockApplications[idx], status: 'approved' as const };
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', `/approve-application/${req.params.id}`); return data; },
      { ok: true, message: 'رزومه تأیید شد (mock)' },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/reject-application/:id', async (req, res) => {
  try {
    const reason = (req.query.reason as string) || '';
    const appId = parseInt(req.params.id);
    const idx = mockApplications.findIndex(a => a.app_id === appId);
    if (idx !== -1) mockApplications[idx] = { ...mockApplications[idx], status: 'rejected' as const, reject_reason: reason };
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', `/reject-application/${req.params.id}?reason=${encodeURIComponent(reason)}`); return data; },
      { ok: true, message: 'رزومه رد شد (mock)' },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Resume Requests ──
adminRouter.get('/resume-requests/pending', async (_req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('GET', '/resume-requests/pending'); return data; },
      { count: 0, requests: [] },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/approve-resume-request/:id', async (req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', `/approve-resume-request/${req.params.id}`); return data; },
      { ok: true, message: 'درخواست تأیید شد (mock)' },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/reject-resume-request/:id', async (req, res) => {
  try {
    const reason = (req.query.reason as string) || '';
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', `/reject-resume-request/${req.params.id}?reason=${encodeURIComponent(reason)}`); return data; },
      { ok: true, message: 'درخواست رد شد (mock)' },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Settings ──
adminRouter.get('/settings/welcome-text', async (_req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('GET', '/settings/welcome-text'); return data; },
      mockWelcomeText,
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/settings/welcome-text', async (req, res) => {
  try {
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', '/settings/welcome-text', req.body); return data; },
      { ok: true, key: 'welcome_text', value: req.body.value },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Messages (for Phone Simulator) ──
adminRouter.get('/messages', async (req, res) => {
  try {
    const chatId = req.query.chat_id as string;
    const afterId = req.query.after_id as string;
    const limitQ = parseInt(req.query.limit as string || '50');

    const result = await withFallback(
      async () => {
        let path = `/admin/messages?limit=${encodeURIComponent(String(limitQ))}`;
        if (chatId) path += `&chat_id=${encodeURIComponent(chatId)}`;
        if (afterId) path += `&after_id=${encodeURIComponent(afterId)}`;
        const { data } = await proxyToRailway('GET', path);
        return data;
      },
      {
        count: mockMessages.length,
        messages: mockMessages.filter(m => {
          if (chatId && String(m.chat_id) !== chatId) return false;
          if (afterId && m.msg_id <= parseInt(afterId)) return false;
          return true;
        }),
      },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Broadcast ──
adminRouter.post('/broadcast', async (req, res) => {
  try {
    const { audience, message } = req.body;
    if (!message || !audience) {
      return res.status(400).json({ ok: false, error: 'audience and message are required' });
    }
    if (!['all', 'employer', 'job_seeker'].includes(audience)) {
      return res.status(400).json({ ok: false, error: 'audience must be all, employer, or job_seeker' });
    }
    const result = await withFallback(
      async () => { const { data } = await proxyToRailway('POST', '/broadcast', { audience, message }); return data; },
      { ok: true, message: 'پیام همگانی ارسال شد (mock)', sent_to: audience === 'all' ? mockUsers.length : audience === 'employer' ? 5 : 5 },
    );
    res.json(result);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});
