import { useState, useEffect, useRef } from 'react';
import { Settings, Save, RefreshCw } from 'lucide-react';
import useSWR from 'swr';
import { swrFetcher } from '../api';
import { setWelcomeText as apiSetWelcomeText } from '../api';
import type { WelcomeTextSetting } from '@hamrakar/shared';

interface HealthStatus {
  status: string;
  railway_url: string;
  has_bot_token: boolean;
}

export default function SettingsSection() {
  const { data, mutate } = useSWR<WelcomeTextSetting>(
    '/api/admin/settings/welcome-text',
    swrFetcher,
    { refreshInterval: 15000 }
  );
  const { data: health } = useSWR<HealthStatus>('/api/health', swrFetcher, {
    refreshInterval: 30000,
  });
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const dirtyRef = useRef(false);
  const loadedRef = useRef(false);

  // Sync from server only on initial load — never overwrite user edits
  useEffect(() => {
    if (data?.value && !loadedRef.current) {
      setText(data.value);
      loadedRef.current = true;
    }
  }, [data?.value]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiSetWelcomeText(text);
      setSaved(true);
      dirtyRef.current = false;
      mutate();
      setTimeout(() => setSaved(false), 2000);
    } catch { /* SWR handles */ }
    setSaving(false);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-800">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Settings className="w-4 h-4 text-slate-400" />
          تنظیمات ربات
        </h2>
      </div>

      <div className="p-5 space-y-5">
        {/* Welcome Text */}
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-2">
            پیام خوش‌آمدگویی
          </label>
          {!data ? (
            <div className="h-32 bg-slate-800 rounded-lg animate-pulse" />
          ) : (
            <>
              <textarea
                value={text}
                onChange={(e) => { setText(e.target.value); dirtyRef.current = true; }}
                rows={4}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 resize-y font-sans"
                dir="rtl"
              />
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2 bg-indigo-600 text-white text-xs rounded-lg hover:bg-indigo-500 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  {saving ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  {saved ? 'ذخیره شد ✓' : 'ذخیره'}
                </button>
                <span className="text-[10px] text-slate-500">
                  این متن به همه کاربران جدید نمایش داده میشه
                </span>
              </div>
            </>
          )}
        </div>

        {/* Bot Info */}
        <div className="pt-4 border-t border-slate-800">
          <h3 className="text-xs font-medium text-slate-400 mb-3">وضعیت اتصال</h3>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-800/50 rounded-lg p-3">
              <span className="text-slate-500">API Railway</span>
              <p className={`mt-1 font-mono ${health?.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {health ? (health.status === 'ok' ? '● متصل' : '⚠️ خطا') : '... در حال بررسی'}
              </p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3">
              <span className="text-slate-500">ربات بله</span>
              <p className={`mt-1 font-mono ${health?.has_bot_token ? 'text-emerald-400' : 'text-slate-400'}`}>
                {health?.has_bot_token ? '● متصل' : '— تنظیم نشده'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
