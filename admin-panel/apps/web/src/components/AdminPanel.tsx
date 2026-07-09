import { Wifi, WifiOff } from 'lucide-react';
import useSWR from 'swr';
import { swrFetcher } from '../api';
import type { Stats } from '@hamrakar/shared';
import StatsGrid from './StatsGrid';
import PendingJobs from './PendingJobs';
import PendingApplications from './PendingApplications';
import UsersSection from './UsersSection';
import BroadcastPanel from './BroadcastPanel';
import SettingsSection from './SettingsSection';

export default function AdminPanel() {
  const { error } = useSWR<Stats>('/api/admin/stats', swrFetcher, {
    refreshInterval: 5000,
  });

  const isOnline = !error;

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <div className="flex items-center justify-end">
        <div className={`flex items-center gap-1.5 text-[11px] font-medium px-3 py-1 rounded-full ${
          isOnline ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
        }`}>
          {isOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          {isOnline ? 'متصل به Railway' : 'قطع — تلاش مجدد'}
        </div>
      </div>

      {/* Stats */}
      <StatsGrid />

      {/* Main Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <PendingJobs />
        <PendingApplications />
      </div>

      {/* Users */}
      <UsersSection />

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BroadcastPanel />
        <SettingsSection />
      </div>
    </div>
  );
}
