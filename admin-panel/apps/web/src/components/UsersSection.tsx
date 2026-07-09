import { useState } from 'react';
import { Users, Search, User, Building2, MapPin, Phone } from 'lucide-react';
import type { User as UserType } from '@hamrakar/shared';
import useSWR from 'swr';
import { swrFetcher } from '../api';

export default function UsersSection() {
  const { data, error } = useSWR<{ users: UserType[] }>('/api/admin/users', swrFetcher, {
    refreshInterval: 10000,
  });
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'employer' | 'job_seeker'>('all');

  const users = data?.users ?? [];
  const filtered = users.filter(u => {
    if (roleFilter !== 'all' && u.role !== roleFilter) return false;
    if (!search) return true;
    const s = search.toLowerCase();
    const name = (u.emp_name || u.js_name || '').toLowerCase();
    const company = (u.emp_company || '').toLowerCase();
    const phone = (u.emp_phone || u.js_phone || '').toLowerCase();
    return name.includes(s) || company.includes(s) || phone.includes(s);
  });

  const roleLabel = (role: string | null) => {
    if (role === 'employer') return { text: 'کارفرما', color: 'bg-indigo-500/10 text-indigo-400' };
    if (role === 'job_seeker') return { text: 'کارجو', color: 'bg-emerald-500/10 text-emerald-400' };
    return { text: '—', color: 'bg-slate-500/10 text-slate-400' };
  };

  if (error) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Users className="w-4 h-4 text-indigo-400" />
          کاربران
        </h2>
        <span className="text-[11px] bg-slate-800 text-slate-400 px-2.5 py-1 rounded-full font-medium">
          {filtered.length !== users.length
            ? `${filtered.length} / ${users.length}`
            : `${users.length} نفر`}
        </span>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="جستجو..."
              className="w-44 bg-slate-800 border border-slate-700 rounded-lg pr-9 pl-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value as typeof roleFilter)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500/50 cursor-pointer"
          >
            <option value="all">همه</option>
            <option value="employer">کارفرما</option>
            <option value="job_seeker">کارجو</option>
          </select>
        </div>
      </div>

      {!data ? (
        <div className="p-8 animate-pulse space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-slate-800 rounded-lg" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-10 text-center">
          <User className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">
            {search ? 'کاربری با این مشخصات یافت نشد' : 'هنوز کاربری ثبت نشده'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500">
                <th className="text-right py-3 px-4 font-medium">کاربر</th>
                <th className="text-right py-3 px-4 font-medium">نقش</th>
                <th className="text-right py-3 px-4 font-medium hidden sm:table-cell">شرکت / استان</th>
                <th className="text-right py-3 px-4 font-medium hidden md:table-cell">تلفن</th>
                <th className="text-right py-3 px-4 font-medium hidden lg:table-cell">تاریخ ثبت</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {filtered.map((user) => {
                const rl = roleLabel(user.role);
                const name = user.emp_name || user.js_name || '—';
                const detail = user.role === 'employer'
                  ? (user.emp_company || '—')
                  : (user.js_province || '—');
                const phone = user.role === 'employer'
                  ? (user.emp_phone || '—')
                  : (user.js_phone || '—');

                return (
                  <tr key={user.chat_id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-400">
                          {(name[0] || '؟').toUpperCase()}
                        </div>
                        <div>
                          <p className="text-white font-medium">{name}</p>
                          <p className="text-slate-600 text-[10px]">ID: {user.chat_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${rl.color}`}>
                        {rl.text}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 hidden sm:table-cell">
                      {user.role === 'employer' ? (
                        <span className="flex items-center gap-1">
                          <Building2 className="w-3 h-3" />
                          {detail}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3" />
                          {detail}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 hidden md:table-cell font-mono text-[11px]">
                      <span className="flex items-center gap-1">
                        <Phone className="w-3 h-3" />
                        {phone}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500 hidden lg:table-cell">
                      {user.created_at?.slice(0, 10) || user.reg_date?.slice(0, 10) || '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
