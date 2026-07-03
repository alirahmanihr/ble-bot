import { useState } from 'react';
import { Check, X, AlertCircle, Building2, Tag, Banknote, MapPin } from 'lucide-react';
import type { Job } from '@hamrakar/shared';
import useSWR from 'swr';
import { swrFetcher } from '../api';
import { approveJob, rejectJob } from '../api';

function formatSalary(s: number): string {
  if (!s) return 'توافقی';
  return `${s.toLocaleString('fa-IR')} تومان`;
}

export default function PendingJobs() {
  const { data, error, mutate } = useSWR<{ jobs: Job[] }>('/api/admin/jobs', swrFetcher, {
    refreshInterval: 5000,
  });
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [reasons, setReasons] = useState<Record<number, string>>({});

  const pendingJobs = data?.jobs?.filter(j => j.status === 'pending' || !j.admin_approved) ?? [];

  const handleApprove = async (jobId: number) => {
    try {
      await approveJob(jobId);
      mutate();
    } catch {
      // Error handled by SWR
    }
  };

  const handleReject = async (jobId: number) => {
    try {
      await rejectJob(jobId, reasons[jobId] || '');
      setRejecting(null);
      setReasons(prev => { const next = { ...prev }; delete next[jobId]; return next; });
      mutate();
    } catch {
      // Error handled by SWR
    }
  };

  if (error) return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
      <AlertCircle className="w-8 h-8 text-rose-400 mx-auto mb-3" />
      <p className="text-slate-400 text-sm">خطا در دریافت آگهی‌ها</p>
    </div>
  );

  if (!data) return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
      <div className="animate-pulse space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-20 bg-slate-800 rounded-lg" />
        ))}
      </div>
    </div>
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Building2 className="w-4 h-4 text-indigo-400" />
          آگهی‌های در انتظار تأیید
        </h2>
        <span className="text-[11px] bg-amber-500/10 text-amber-400 px-2.5 py-1 rounded-full font-medium">
          {pendingJobs.length} مورد
        </span>
      </div>

      {pendingJobs.length === 0 ? (
        <div className="p-10 text-center">
          <Check className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">همه آگهی‌ها بررسی شدن</p>
        </div>
      ) : (
        <div className="divide-y divide-slate-800">
          {pendingJobs.slice(0, 20).map((job) => (
            <div key={job.job_id} className="p-4 hover:bg-slate-800/30 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-white truncate">{job.title}</h3>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Building2 className="w-3 h-3" />
                      {job.employer_company || 'نامشخص'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Tag className="w-3 h-3" />
                      {job.category}
                    </span>
                    <span className="flex items-center gap-1">
                      <Banknote className="w-3 h-3" />
                      {formatSalary(job.salary)}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {job.location || 'نامشخص'}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-600 mt-1.5">
                    JOB-{job.job_id} · {job.emp_type}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleApprove(job.job_id)}
                    className="p-2 rounded-lg bg-emerald-600/10 text-emerald-400 hover:bg-emerald-600/20 transition-colors cursor-pointer"
                    title="تأیید"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => { setRejecting(job.job_id); }}
                    className="p-2 rounded-lg bg-rose-600/10 text-rose-400 hover:bg-rose-600/20 transition-colors cursor-pointer"
                    title="رد"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Reject reason popup */}
              {rejecting === job.job_id && (
                <div className="mt-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <input
                    type="text"
                    value={reasons[job.job_id] || ''}
                    onChange={(e) => setReasons(prev => ({ ...prev, [job.job_id]: e.target.value }))}
                    placeholder="علت رد آگهی (اختیاری)..."
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500/50 mb-2"
                    autoFocus
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleReject(job.job_id)}
                      className="px-3 py-1.5 bg-rose-600 text-white text-xs rounded-lg hover:bg-rose-500 transition-colors cursor-pointer"
                    >
                      رد آگهی
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
