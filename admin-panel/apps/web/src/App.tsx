import { useState } from 'react';
import { Layout, Smartphone } from 'lucide-react';
import AdminPanel from './components/AdminPanel';
import PhoneSimulator from './components/PhoneSimulator';

export default function App() {
  const [tab, setTab] = useState<'admin' | 'simulator'>('admin');

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col" dir="rtl">
      {/* Header */}
      <header className="bg-slate-950/80 border-b border-slate-800/40 backdrop-blur-md sticky top-0 z-50 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white font-extrabold text-sm shadow-lg shadow-indigo-600/20">
            هـ
          </div>
          <div>
            <h1 className="text-sm font-black text-white uppercase tracking-tight">پنل مدیریت همراکار</h1>
            <p className="text-[10px] text-slate-500">رسانه استخدامی — پیام‌رسان بله</p>
          </div>
        </div>

        <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs font-semibold gap-1">
          <button
            onClick={() => setTab('admin')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
              tab === 'admin'
                ? 'bg-slate-800 text-indigo-400 shadow-sm border border-slate-700/50'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layout className="w-3.5 h-3.5" />
            <span>کنسول ادمین</span>
          </button>

          <button
            onClick={() => setTab('simulator')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
              tab === 'simulator'
                ? 'bg-slate-800 text-indigo-400 shadow-sm border border-slate-700/50'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>شبیه‌ساز بله</span>
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {tab === 'admin' ? <AdminPanel /> : <PhoneSimulator />}
      </main>
    </div>
  );
}
