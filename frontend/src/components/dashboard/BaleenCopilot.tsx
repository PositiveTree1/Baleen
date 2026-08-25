'use client';
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  X, 
  Send, 
  Bot, 
  User as UserIcon, 
  Zap, 
  Cpu, 
  Layers, 
  RefreshCw, 
  TrendingUp, 
  ShieldCheck, 
  Wallet,
  ArrowRight,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { fetchCopilotChat } from '@/lib/api-client';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: { name: string; args: any; summary: string }[];
  timestamp: Date;
}

const STARTER_PROMPTS = [
  { label: '📊 Portfolio Overview', prompt: 'Give me an executive quantitative summary of our current portfolio balance, ROI, and total executions.' },
  { label: '🐋 Top Whales & Snipers', prompt: 'Who are our top performing whales and snipers by PnL and win rate? Give me their tiers and trading style.' },
  { label: '⚡ Active Consensus Signals', prompt: 'Are there any prediction markets where multiple basket whales currently agree on the same outcome?' },
  { label: '🛡️ Fee Drag & Gate Audits', prompt: 'Analyze our Polymarket taker fee expenses across Sports, Crypto, and Politics categories.' },
];

export function BaleenCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I'm the **Baleen AI Copilot**, powered by quantitative tool-calling models.\n\nI have direct read access to all **5,000+ live executions**, wallet baskets, consensus signals, and fee structures. Ask me anything about performance, specific whales, or risk attribution!",
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut: Cmd+K or Ctrl+K to toggle Copilot
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input.trim();
    if (!query || loading) return;

    const userMessage: Message = {
      id: String(Date.now()),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setActiveTool('Analyzing query and planning tools...');

    // Prepare API history
    const apiMessages = [...messages, userMessage].map(m => ({
      role: m.role,
      content: m.content
    }));

    try {
      const response = await fetchCopilotChat(apiMessages);
      if (response && response.message) {
        setMessages(prev => [
          ...prev,
          {
            id: String(Date.now() + 1),
            role: 'assistant',
            content: response.message,
            toolCalls: response.tool_calls_executed,
            timestamp: new Date(),
          }
        ]);
      } else {
        setMessages(prev => [
          ...prev,
          {
            id: String(Date.now() + 1),
            role: 'assistant',
            content: "Sorry, I couldn't reach the quantitative intelligence service. Please check backend connectivity.",
            timestamp: new Date(),
          }
        ]);
      }
    } catch (e) {
      setMessages(prev => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'assistant',
          content: "An error occurred while evaluating your request.",
          timestamp: new Date(),
        }
      ]);
    } finally {
      setLoading(false);
      setActiveTool(null);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: String(Date.now()),
        role: 'assistant',
        content: "Conversation history cleared. Ready for your next quantitative inquiry.",
        timestamp: new Date(),
      }
    ]);
  };

  // Simple Markdown text renderer with styling
  const renderMarkdown = (content: string) => {
    const lines = content.split('\n');
    return (
      <div className="space-y-2 text-xs sm:text-[13px] leading-relaxed text-slate-800">
        {lines.map((line, idx) => {
          if (!line.trim()) return <div key={idx} className="h-1.5" />;
          
          // Header 3 or 4
          if (line.startsWith('### ') || line.startsWith('#### ')) {
            return (
              <h4 key={idx} className="font-bold text-slate-950 text-sm mt-3 pt-1 border-t border-black/[0.04] first:border-0 first:mt-0">
                {line.replace(/^#{3,4}\s+/, '')}
              </h4>
            );
          }

          // Bullet list item
          if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
            const clean = line.trim().replace(/^[-*]\s+/, '');
            return (
              <div key={idx} className="flex items-start gap-2 pl-1">
                <span className="text-indigo-500 font-bold">•</span>
                <span dangerouslySetInnerHTML={{ __html: formatInline(clean) }} />
              </div>
            );
          }

          // Numbered list item
          if (/^\d+\.\s+/.test(line.trim())) {
            const num = line.trim().match(/^\d+\./)?.[0] || '1.';
            const clean = line.trim().replace(/^\d+\.\s+/, '');
            return (
              <div key={idx} className="flex items-start gap-2 pl-1">
                <span className="text-indigo-600 font-mono font-bold text-[11px]">{num}</span>
                <span dangerouslySetInnerHTML={{ __html: formatInline(clean) }} />
              </div>
            );
          }

          return (
            <p key={idx} dangerouslySetInnerHTML={{ __html: formatInline(line) }} />
          );
        })}
      </div>
    );
  };

  const formatInline = (text: string) => {
    // Bold
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-slate-950">$1</strong>');
    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-indigo-700 border border-black/[0.04]">$1</code>');
    return formatted;
  };

  return (
    <>
      {/* Floating Trigger Button (Discrete & Elegant) */}
      <div className="fixed bottom-5 right-5 z-40">
        <motion.button
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          onClick={() => setIsOpen(true)}
          className="w-10 h-10 rounded-full bg-white/95 backdrop-blur-md text-slate-800 shadow-md hover:shadow-lg border border-black/[0.08] hover:border-indigo-300 flex items-center justify-center transition-all cursor-pointer group"
          title="Open Baleen Copilot (⌘K / Ctrl+K)"
        >
          <Sparkles size={16} className="text-indigo-600 group-hover:rotate-12 transition-transform" />
        </motion.button>
      </div>

      {/* Slide-over Copilot Drawer / Modal */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-black/25 backdrop-blur-xs"
            />

            {/* Panel */}
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 280 }}
              className={`relative h-full bg-white border-l border-black/[0.08] shadow-2xl flex flex-col z-50 transition-all duration-300 ${
                isExpanded ? 'w-full max-w-2xl' : 'w-full max-w-lg'
              }`}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 px-5 border-b border-black/[0.06] bg-slate-50/80">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-500 flex items-center justify-center text-white shadow-xs">
                    <Sparkles size={16} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-900">Baleen Copilot</h3>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <Zap size={9} /> Groq LLaMA 3.3 70B
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 font-medium">Dynamic tool calling across 5,000+ executions</p>
                  </div>
                </div>

                <div className="flex items-center gap-1 text-slate-400">
                  <button
                    onClick={() => setIsExpanded(prev => !prev)}
                    className="p-1.5 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition-colors cursor-pointer"
                    title={isExpanded ? 'Collapse panel' : 'Expand panel'}
                  >
                    {isExpanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
                  </button>
                  <button
                    onClick={handleClear}
                    className="p-1.5 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition-colors cursor-pointer"
                    title="Clear conversation"
                  >
                    <RefreshCw size={15} />
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1.5 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition-colors cursor-pointer ml-1"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>

              {/* Chat Message Stream */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-slate-50/40">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`flex items-start gap-3 ${
                      m.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                    }`}
                  >
                    {/* Avatar */}
                    <div
                      className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
                        m.role === 'user'
                          ? 'bg-slate-900 text-white'
                          : 'bg-indigo-50 text-indigo-600 border border-indigo-200 shadow-2xs'
                      }`}
                    >
                      {m.role === 'user' ? <UserIcon size={14} /> : <Bot size={15} />}
                    </div>

                    {/* Bubble */}
                    <div className={`space-y-1.5 max-w-[85%]`}>
                      {/* Tool Execution Badges */}
                      {m.toolCalls && m.toolCalls.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-1.5">
                          {m.toolCalls.map((tc, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200"
                            >
                              <Zap size={9} /> {tc.name}()
                            </span>
                          ))}
                        </div>
                      )}

                      <div
                        className={`p-3.5 rounded-2xl shadow-2xs ${
                          m.role === 'user'
                            ? 'bg-slate-900 text-white rounded-tr-xs'
                            : 'bg-white text-slate-800 border border-black/[0.06] rounded-tl-xs'
                        }`}
                      >
                        {m.role === 'user' ? (
                          <p className="text-xs sm:text-[13px] leading-relaxed whitespace-pre-wrap">{m.content}</p>
                        ) : (
                          renderMarkdown(m.content)
                        )}
                      </div>

                      <div
                        className={`text-[9px] font-mono text-slate-400 px-1 ${
                          m.role === 'user' ? 'text-right' : 'text-left'
                        }`}
                      >
                        {m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Loading / Tool execution indicator */}
                {loading && (
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-200 flex items-center justify-center shrink-0">
                      <Bot size={15} />
                    </div>
                    <div className="p-3.5 rounded-2xl bg-white border border-black/[0.06] shadow-2xs space-y-2 max-w-[80%]">
                      <div className="flex items-center gap-2 text-xs font-mono font-semibold text-indigo-600">
                        <Zap size={13} className="animate-spin text-indigo-500" />
                        <span>{activeTool || 'Executing tools & synthesizing data...'}</span>
                      </div>
                      <div className="flex gap-1.5 pt-1">
                        <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Starter Prompts Carousel / Chips */}
              {messages.length <= 2 && (
                <div className="p-3 px-4 border-t border-black/[0.04] bg-white">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Suggested Inquiries</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                    {STARTER_PROMPTS.map((sp, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(sp.prompt)}
                        className="text-left p-2 rounded-xl bg-slate-50 hover:bg-indigo-50/60 border border-black/[0.04] hover:border-indigo-200 text-slate-700 hover:text-indigo-900 text-xs font-medium transition-all cursor-pointer flex items-center justify-between group"
                      >
                        <span className="truncate">{sp.label}</span>
                        <ArrowRight size={12} className="text-slate-400 group-hover:text-indigo-600 shrink-0 ml-1" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input Box */}
              <div className="p-3 sm:p-4 border-t border-black/[0.06] bg-white">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSend();
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about whales, trades, fees, PnL, consensus..."
                    disabled={loading}
                    className="flex-1 bg-slate-100 hover:bg-slate-100/80 focus:bg-white text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 px-3.5 py-2.5 rounded-xl border border-black/[0.06] focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || loading}
                    className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-white transition-all cursor-pointer shrink-0 shadow-xs"
                    title="Send message (Enter)"
                  >
                    <Send size={15} />
                  </button>
                </form>
                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2 px-1 font-mono">
                  <span>LLaMA 3.3 70B • Tool Calling Enabled</span>
                  <span>Press <kbd className="font-semibold text-slate-600">Enter</kbd> to submit</span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
