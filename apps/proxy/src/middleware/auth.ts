import type { Request, Response, NextFunction } from 'express';

export function authMiddleware(req: Request, res: Response, next: NextFunction) {
  const token = req.headers['x-admin-token'] as string;
  const expectedToken = process.env.ADMIN_TOKEN;

  if (!expectedToken || expectedToken === 'your_admin_token_here') {
    // Token not configured — allow all (dev mode)
    console.warn('⚠️  ADMIN_TOKEN not configured — auth disabled');
    return next();
  }

  if (!token || token !== expectedToken) {
    return res.status(401).json({ ok: false, error: 'Unauthorized — invalid or missing X-Admin-Token' });
  }

  next();
}
