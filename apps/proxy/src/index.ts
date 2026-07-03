import dotenv from 'dotenv';
import { resolve } from 'path';
// Load .env from project root (three levels up from apps/proxy/src)
dotenv.config({ path: resolve(import.meta.dirname, '..', '..', '..', '.env') });

import cors from 'cors';
import express from 'express';
import { adminRouter } from './routes/admin.js';
import { baleRouter } from './routes/bale.js';

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT) : 3001;

app.use(cors());
app.use(express.json());

// Health check
app.get('/api/health', (_req, res) => {
  res.json({
    status: 'ok',
    railway_url: process.env.RAILWAY_API_URL || 'not set',
    has_bot_token: !!process.env.BALE_BOT_TOKEN,
  });
});

// Route handlers
app.use('/api/admin', adminRouter);
app.use('/api/bale', baleRouter);

app.listen(PORT, '0.0.0.0', () => {
  console.log(`🔐 Proxy running on http://localhost:${PORT}`);
  console.log(`   Railway: ${process.env.RAILWAY_API_URL || 'NOT SET'}`);
  console.log(`   Bale Token: ${process.env.BALE_BOT_TOKEN ? '✅ set' : '❌ NOT SET'}`);
  console.log(`   Admin Token: ${process.env.ADMIN_TOKEN ? '✅ set' : '❌ NOT SET'}`);
});
