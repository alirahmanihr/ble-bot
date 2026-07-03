import { Router } from 'express';
import { authMiddleware } from '../middleware/auth.js';

export const baleRouter = Router();

const BALE_API = 'https://tapi.bale.ai';

baleRouter.use(authMiddleware);

function getBotToken(): string {
  return process.env.BALE_BOT_TOKEN || '';
}

function getBaleUrl(method: string): string {
  return `${BALE_API}/bot${getBotToken()}/${method}`;
}

// Send message as the bot
baleRouter.post('/sendMessage', async (req, res) => {
  try {
    const botToken = getBotToken();
    if (!botToken || botToken === 'your_bot_token_here') {
      return res.status(400).json({ ok: false, error: 'BALE_BOT_TOKEN not configured' });
    }

    const { chat_id, text } = req.body;
    if (!chat_id || !text) {
      return res.status(400).json({ ok: false, error: 'chat_id and text are required' });
    }

    const url = getBaleUrl('sendMessage');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: Number(chat_id),
          text,
          parse_mode: 'Markdown',
        }),
        signal: controller.signal,
      });
      clearTimeout(timeout);

      let data: any;
      try {
        data = await response.json();
      } catch {
        data = { ok: false, description: `Invalid JSON response (status ${response.status})` };
      }
      res.json(data);
    } catch (err: any) {
      clearTimeout(timeout);
      if (err.name === 'AbortError') {
        return res.status(504).json({ ok: false, error: 'Bale API request timed out' });
      }
      throw err;
    }
  } catch (err: any) {
    res.status(502).json({ ok: false, error: `Bale API error: ${err.message}` });
  }
});

// Get bot info (test connectivity)
baleRouter.get('/getMe', async (_req, res) => {
  try {
    const botToken = getBotToken();
    if (!botToken || botToken === 'your_bot_token_here') {
      return res.status(400).json({ ok: false, error: 'BALE_BOT_TOKEN not configured' });
    }

    const url = getBaleUrl('getMe');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    try {
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeout);

      let data: any;
      try {
        data = await response.json();
      } catch {
        data = { ok: false, description: `Invalid JSON response (status ${response.status})` };
      }
      res.json(data);
    } catch (err: any) {
      clearTimeout(timeout);
      if (err.name === 'AbortError') {
        return res.status(504).json({ ok: false, error: 'Bale API request timed out' });
      }
      throw err;
    }
  } catch (err: any) {
    res.status(502).json({ ok: false, error: `Bale API error: ${err.message}` });
  }
});
