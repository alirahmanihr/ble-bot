import { useState } from 'react';
import { Check, X, AlertCircle, FileText, User, Briefcase } from 'lucide-react';
import type { Application } from '@hamrakar/shared';
import useSWR from 'swr';
import { swrFetcher } from '../api';
import { approveApplication, rejectApplication } from '../api';

export default function PendingApplications() {
  const { data, error, mutate } = useSWR<{ applications: Application[] }>(
    '/api/admin/applications',
    swrFetcher,
    { refreshInterval: 5000 }
  );
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [reasons, setReasons] = useState<Record<number, string>>({});

  const pendingApps = data?.applications?.filter(a => a.status === 'pending_admin') ?? [];

  const handleApprove = async (appId: number) => {
    try {
      await approveApplication(appId);
      mutate();
    } catch { /* SWR handles error */ }
  };

  const handleReject = async (appId: number) => {
    try {
      await rejectApplication(appId, reasons[appId] || '');
      setRejecting(null);
      setReasons(prev => { const next = { ...prev }; delete next[appId]; return next; });
      mutate();
    } catch { /* SWR handles error */ }
  };

  if (error) return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
      <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-3" />
      <p className="text-slate-400 text-sm">خطا در دریافت رزومه‌ها</p>
    </div>
  );

  if (!data) return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
      <div className="animate-pulse space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-16 bg-slate-800 rounded-lg" />
        ))}
      </div>
    </div>
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <FileText className="w-4 h-4 text-amber-400" />
          رزومه‌های در انتظار تأیید
        </h2>
        <span className="text-[11px] bg-amber-500/10 text-amber-400 px-2.5 py-1 rounded-full font-medium">
          {pendingApps.length} مورد
        </span>
      </div>

      {pendingApps.length === 0 ? (
        <div className="p-10 text-center">
          <Check className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">همه رزومه‌ها بررسی شدن</p>
        </div>
      ) : (
        <div className="divide-y divide-slate-800">
          {pendingApps.slice(0, 20).map((app) => (
            <div key={app.app_id} className="p-4 hover:bg-slate-800/30 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="flex items-center gap-1 text-sm font-semibold text-white">
                      <User className="w-3.5 h-3.5 text-slate-500" />
                      {app.seeker_name || 'نامشخص'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 flex items-center gap-1">
                    <Briefcase className="w-3 h-3" />
                    {app.job_title || 'نامشخص'}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-1">
                    APP-{app.app_id}
                    {app.resume_text ? ' · رزومه متنی' : app.resume_file ? ' · فایل پیوست' : ''}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleApprove(app.app_id)}
                    className="p-2 rounded-lg bg-emerald-600/10 text-emerald-400 hover:bg-emerald-600/20 transition-colors cursor-pointer"
                    title="تأیید"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => { setRejecting(app.app_id); }}
                    className="p-2 rounded-lg bg-rose-600/10 text-rose-400 hover:bg-rose-600/20 transition-colors cursor-pointer"
                    title="رد"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {rejecting === app.app_id && (
                <div className="mt-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <input
                    type="text"
                    value={reasons[app.app_id] || ''}
                    onChange={(e) => setReasons(prev => ({ ...prev, [app.app_id]: e.target.value }))}
                    placeholder="علت رد رزومه (اختیاری)..."
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500/50 mb-2"
                    autoFocus
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleReject(app.app_id)}
                      className="px-3 py-1.5 bg-rose-600 text-white text-xs rounded-lg hover:bg-rose-500 transition-colors cursor-pointer"
                    >
                      رد رزومه
                    </button>
                    <button
                      onClick={() => setRejecting(null)}
                      className="px-3 py-1.5 text-slate-400 text-xs hover:text-white transition-colors cursor-pointer"
                    >
                      انصراف
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
