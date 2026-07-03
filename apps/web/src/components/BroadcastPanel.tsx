import { useState } from 'react';
import { Send, Radio, Users, Briefcase, Search, Loader2 } from 'lucide-react';
import useSWR from 'swr';
import { swrFetcher } from '../api';
import { broadcastMessage } from '../api';
import type { User as UserType } from '@hamrakar/shared';

export default function BroadcastPanel() {
  const { data } = useSWR<{ users: UserType[] }>('/api/admin/users', swrFetcher, {
    refreshInterval: 30000,
  });
  const [audience, setAudience] = useState<'all' | 'employer' | 'job_seeker'>('all');
  const [message, setMessage] = useState('');
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const users = data?.users ?? [];
  const employerCount = users.filter(u => u.role === 'employer').length;
  const seekerCount = users.filter(u => u.role === 'job_seeker').length;

  const targetCount =
    audience === 'all' ? users.length :
    audience === 'employer' ? employerCount :
    seekerCount;

  const handleSend = async () => {
    if (!message.trim() || sending) return;
    setSending(true);
    setError('');
    try {
      await broadcastMessage(audience, message.trim());
      setSent(true);
      setMessage('');
      setTimeout(() => setSent(false), 3000);
    } catch (err: any) {
      setError(err.message || 'خطا در ارسال پیام همگانی');
    }
    setSending(false);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-800">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Radio className="w-4 h-4 text-indigo-400" />
          ارسال پیام همگانی
        </h2>
      </div>

      <div className="p-5 space-y-4">
        {/* Audience Selector */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-2">مخاطب</label>
          <div className="flex gap-2">
            {([
              { value: 'all' as const, label: 'همه کاربران', icon: Users, count: users.length },
              { value: 'employer' as const, label: 'کارفرمایان', icon: Briefcase, count: employerCount },
              { value: 'job_seeker' as const, label: 'کارجویان', icon: Search, count: seekerCount },
            ]).map((opt) => (
              <button
                key={opt.value}
                onClick={() => setAudience(opt.value)}
                className={`flex-1 p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                  audience === opt.value
                    ? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-300'
                    : 'border-slate-700 bg-slate-800/30 text-slate-400 hover:border-slate-600'
                }`}
              >
                <opt.icon className="w-4 h-4 mx-auto mb-1" />
                <span className="block font-medium">{opt.label}</span>
                <span className="text-[10px] text-slate-500">{opt.count} نفر</span>
              </button>
            ))}
          </div>
        </div>

        {/* Message */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-2">متن پیام</label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            placeholder="پیام خود را بنویسید..."
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 resize-none font-sans"
            dir="rtl"
          />
        </div>

        {/* Send */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-slate-500">
            ارسال به <strong className="text-slate-300">{targetCount}</strong> کاربر
          </span>
          <button
            onClick={handleSend}
            disabled={!message.trim() || sending}
            className="px-5 py-2 bg-indigo-600 text-white text-xs rounded-lg hover:bg-indigo-500 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {sending ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /> در حال ارسال...</>
            ) : sent ? (
              '✓ ارسال شد!'
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                ارسال
              </>
            )}
          </button>
        </div>
        {error && (
          <p className="text-[11px] text-rose-400 mt-2">{error}</p>
        )}
      </div>
    </div>
  );
}
