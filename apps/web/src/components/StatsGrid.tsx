import { Users, Briefcase, FileText, Clock } from 'lucide-react';
import type { Stats } from '@hamrakar/shared';
import useSWR from 'swr';
import { swrFetcher } from '../api';

function SkeletonCard() {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 animate-pulse">
      <div className="h-3 w-20 bg-slate-800 rounded mb-3" />
      <div className="h-8 w-16 bg-slate-800 rounded mb-2" />
      <div className="h-2 w-28 bg-slate-800 rounded" />
    </div>
  );
}

function StatCard({ icon: Icon, label, value, subtitle, color }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
  subtitle: string;
  color: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <span className="text-xs font-medium text-slate-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white tabular-nums">{value}</div>
      <div className="text-[11px] text-slate-500 mt-1">{subtitle}</div>
    </div>
  );
}

export default function StatsGrid() {
  const { data, error } = useSWR<Stats>('/api/admin/stats', swrFetcher, {
    refreshInterval: 5000,
  });

  if (error) return null; // Silently fail, parent shows error
  if (!data) return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
    </div>
  );

  const cards = [
    {
      icon: Users,
      label: 'کل کاربران',
      value: data.total,
      subtitle: `${data.employers} کارفرما · ${data.seekers} کارجو`,
      color: 'bg-indigo-600/20 text-indigo-400',
    },
    {
      icon: Briefcase,
      label: 'آگهی فعال',
      value: data.active,
      subtitle: `${data.pending} در انتظار تأیید`,
      color: 'bg-emerald-600/20 text-emerald-400',
    },
    {
      icon: FileText,
      label: 'رزومه جدید',
      value: data.pending_apps,
      subtitle: 'در انتظار بررسی',
      color: 'bg-amber-600/20 text-amber-400',
    },
    {
      icon: Clock,
      label: 'آگهی در انتظار',
      value: data.pending,
      subtitle: 'نیاز به اقدام',
      color: 'bg-rose-600/20 text-rose-400',
    },
  ];

  const allZero = cards.every(c => c.value === 0);

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>
      {allZero && (
        <div className="mt-4 bg-slate-900 border border-slate-800 rounded-xl p-6 text-center">
          <p className="text-slate-400 text-sm">هنوز داده‌ای ثبت نشده — کاربران ربات به مرور اضافه خواهند شد.</p>
        </div>
      )}
    </div>
  );
}
