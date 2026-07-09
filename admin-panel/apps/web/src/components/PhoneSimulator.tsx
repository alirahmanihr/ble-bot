import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Smartphone, ChevronDown, Loader2, Wifi } from 'lucide-react';
import useSWR from 'swr';
import { swrFetcher } from '../api';
import { sendBaleMessage, getMessages } from '../api';
import type { BotMessage } from '@hamrakar/shared';

interface ChatBubble {
  id: number;
  direction: 'in' | 'out';
  text: string;
  timestamp: string;
}

export default function PhoneSimulator() {
  const [chatId, setChatId] = useState('');
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [sending, setSending] = useState(false);
  const lastMsgIdRef = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: botInfo } = useSWR<{ ok: boolean; result?: { first_name?: string } }>(
    '/api/bale/getMe',
    swrFetcher,
    {
      refreshInterval: 0,
      revalidateOnFocus: false,
    }
  );

  const botName = botInfo?.result?.first_name || 'ربات همراکار';

  // Poll for new messages — uses ref for lastMsgId to avoid interval recreation
  const pollMessages = useCallback(async () => {
    if (!activeChatId) return;
    try {
      const data = await getMessages(activeChatId, lastMsgIdRef.current, 50);
      if (data?.messages?.length) {
        setMessages(prev => {
          const existing = new Set(prev.map(m => m.id));
          const newMsgs = data.messages.filter((m: BotMessage) => !existing.has(m.msg_id));
          if (newMsgs.length === 0) return prev;
          const all = [...prev, ...newMsgs.map((m: BotMessage) => ({
            id: m.msg_id,
            direction: m.direction,
            text: m.text,
            timestamp: m.created_at,
          }))];
          // Update last seen ID via ref
          const maxId = Math.max(...all.map(m => m.id));
          lastMsgIdRef.current = maxId;
          return all;
        });
      }
    } catch {
      // Silently fail — messages endpoint may not be available yet
    }
  }, [activeChatId]);

  useEffect(() => {
    if (!activeChatId) return;
    const interval = setInterval(pollMessages, 2000);
    return () => clearInterval(interval);
  }, [pollMessages, activeChatId]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleConnect = () => {
    const id = parseInt(chatId);
    if (isNaN(id)) return;
    setActiveChatId(id);
    setMessages([]);
    lastMsgIdRef.current = 0;
    inputRef.current?.focus();
  };

  const handleSend = async () => {
    if (!inputText.trim() || !activeChatId || sending) return;
    const text = inputText.trim();
    setInputText('');
    setSending(true);

    // Optimistically add outgoing message
    const tempId = Date.now();
    setMessages(prev => [...prev, {
      id: tempId,
      direction: 'out',
      text,
      timestamp: new Date().toISOString(),
    }]);

    try {
      await sendBaleMessage(activeChatId, text);
    } catch {
      // Mark as failed
      setMessages(prev => prev.map(m =>
        m.id === tempId ? { ...m, text: m.text + ' ⚠️ ارسال نشد' } : m
      ));
    }
    setSending(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="max-w-md mx-auto">
      {/* Phone Frame */}
      <div className="bg-slate-900 border-2 border-slate-700 rounded-3xl overflow-hidden shadow-2xl shadow-black/40">
        {/* Phone Header */}
        <div className="bg-slate-800 px-5 py-3 flex items-center gap-3 border-b border-slate-700">
          <Smartphone className="w-4 h-4 text-slate-400" />
          <div className="flex-1">
            <p className="text-xs font-bold text-white">{botName}</p>
            <p className="text-[10px] text-slate-400">پیام‌رسان بله</p>
          </div>
          {activeChatId ? (
            <div className="flex items-center gap-1 text-[10px] text-emerald-400">
              <Wifi className="w-3 h-3" />
              متصل
            </div>
          ) : (
            <span className="text-[10px] text-slate-500">قطع</span>
          )}
        </div>

        {!activeChatId ? (
          /* Connection Screen */
          <div className="p-6 space-y-4">
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 flex items-center justify-center mx-auto mb-3">
                <Smartphone className="w-8 h-8 text-indigo-400" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">اتصال به ربات بله</h3>
              <p className="text-[11px] text-slate-400">
                Chat ID ادمین را وارد کنید تا شبیه‌ساز فعال شود
              </p>
            </div>

            <div>
              <label className="block text-[10px] font-medium text-slate-500 mb-1.5">
                Chat ID
              </label>
              <input
                type="number"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                placeholder="مثال: 123456789"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 font-mono"
                onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
              />
            </div>

            <button
              onClick={handleConnect}
              disabled={!chatId}
              className="w-full py-2.5 bg-indigo-600 text-white text-sm rounded-xl hover:bg-indigo-500 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed font-medium"
            >
              اتصال به ربات
            </button>

            <p className="text-[10px] text-slate-600 text-center">
              Chat ID خود را از طریق @userinfobot در بله دریافت کنید
            </p>
          </div>
        ) : (
          <>
            {/* Messages Area */}
            <div className="h-96 overflow-y-auto p-4 space-y-3 bg-[#0f172a]" style={{
              backgroundImage: 'radial-gradient(ellipse at top, rgba(99,102,241,0.05) 0%, transparent 60%)',
            }}>
              {messages.length === 0 && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-2">
                      <Smartphone className="w-5 h-5 text-slate-600" />
                    </div>
                    <p className="text-xs text-slate-500">پیامی دریافت نشده</p>
                    <p className="text-[10px] text-slate-600 mt-1">یک پیام از طریق بله به ربات بفرستید</p>
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.direction === 'out' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                      msg.direction === 'out'
                        ? 'bg-indigo-600 text-white rounded-br-md'
                        : 'bg-slate-800 text-slate-200 rounded-bl-md border border-slate-700/50'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                    <p className={`text-[9px] mt-1 ${
                      msg.direction === 'out' ? 'text-indigo-300' : 'text-slate-500'
                    }`}>
                      {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('fa-IR', {
                        hour: '2-digit',
                        minute: '2-digit',
                      }) : ''}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 bg-slate-800 border-t border-slate-700 flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="پیام خود را بنویسید..."
                className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
                dir="auto"
              />
              <button
                onClick={handleSend}
                disabled={!inputText.trim() || sending}
                className="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-500 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {sending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Disconnect */}
            <div className="px-3 pb-3 bg-slate-800">
              <button
                onClick={() => setActiveChatId(null)}
                className="w-full py-1.5 text-[10px] text-slate-500 hover:text-slate-300 transition-colors cursor-pointer flex items-center justify-center gap-1"
              >
                <ChevronDown className="w-3 h-3" />
                قطع اتصال
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
