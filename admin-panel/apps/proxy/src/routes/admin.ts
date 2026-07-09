import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.js';

export const adminRouter = Router();

// All admin routes require auth
adminRouter.use(authMiddleware);

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
  const timeout = setTimeout(() => controller.abort(), 15000);

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
    const data = await response.json();
    return { status: response.status, data };
  } catch (err: any) {
    clearTimeout(timeout);
    if (err.name === 'AbortError') {
      throw new Error('Railway request timed out');
    }
    throw err;
  }
}

// ── Stats ──
adminRouter.get('/stats', async (_req, res) => {
  try {
    const { data } = await proxyToRailway('GET', '/stats');
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: `Railway unreachable: ${err.message}` });
  }
});

// ── Users ──
adminRouter.get('/users', async (_req, res) => {
  try {
    const { data } = await proxyToRailway('GET', '/users');
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Jobs ──
adminRouter.get('/jobs', async (_req, res) => {
  try {
    const { data } = await proxyToRailway('GET', '/jobs');
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/approve-job/:id', async (req, res) => {
  try {
    const { data } = await proxyToRailway('POST', `/approve-job/${req.params.id}`);
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/reject-job/:id', async (req, res) => {
  try {
    const reason = (req.query.reason as string) || '';
    const { data } = await proxyToRailway('POST', `/reject-job/${req.params.id}?reason=${encodeURIComponent(reason)}`);
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Applications ──
adminRouter.get('/applications', async (_req, res) => {
  try {
    const { data } = await proxyToRailway('GET', '/applications');
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/approve-application/:id', async (req, res) => {
  try {
    const { data } = await proxyToRailway('POST', `/approve-application/${req.params.id}`);
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/reject-application/:id', async (req, res) => {
  try {
    const reason = (req.query.reason as string) || '';
    const { data } = await proxyToRailway('POST', `/reject-application/${req.params.id}?reason=${encodeURIComponent(reason)}`);
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Resume Requests ──
adminRouter.get('/resume-requests/pending', async (_req, res) => {
  try {
    const { data } = await proxyToRailway('GET', '/resume-requests/pending');
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/approve-resume-request/:id', async (req, res) => {
  try {
    const { data } = await proxyToRailway('POST', `/approve-resume-request/${req.params.id}`);
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/reject-resume-request/:id', async (req, res) => {
  try {
    const reason = (req.query.reason as string) || '';
    const { data } = await proxyToRailway('POST', `/reject-resume-request/${req.params.id}?reason=${encodeURIComponent(reason)}`);
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Settings ──
adminRouter.get('/settings/welcome-text', async (_req, res) => {
  try {
    const { data } = await proxyToRailway('GET', '/settings/welcome-text');
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

adminRouter.post('/settings/welcome-text', async (req, res) => {
  try {
    const { data } = await proxyToRailway('POST', '/settings/welcome-text', req.body);
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});

// ── Messages (for Phone Simulator) ──
adminRouter.get('/messages', async (req, res) => {
  try {
    const chatId = req.query.chat_id as string;
    const afterId = req.query.after_id as string;
    const limit = req.query.limit || '50';

    let path = `/admin/messages?limit=${encodeURIComponent(String(limit))}`;
    if (chatId) path += `&chat_id=${encodeURIComponent(chatId)}`;
    if (afterId) path += `&after_id=${encodeURIComponent(afterId)}`;

    const { data } = await proxyToRailway('GET', path);
    res.json(data);
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
    const { data } = await proxyToRailway('POST', '/broadcast', { audience, message });
    res.json(data);
  } catch (err: any) {
    res.status(502).json({ ok: false, error: err.message });
  }
});
