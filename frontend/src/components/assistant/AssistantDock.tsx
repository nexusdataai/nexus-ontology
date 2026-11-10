/**
 * Nexus assistant: a launcher docked at the bottom-right of every page that
 * opens a chat panel anchored to the same corner (a bottom sheet on phones).
 *
 * It talks to the same agent as the AI Copilot screen
 * (POST /api/v1/control-plane/agent/stream, server-sent events), shows the
 * steps the agent takes while it works, and keeps the conversation while the
 * user moves between pages. Mounted once in App.tsx, above the routes.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useLocation, useNavigate } from 'react-router-dom';
import { LogoMark } from '@/components/ds/Logo';
import { Icon } from '@/components/ds/Icon';
import { cn } from '@/lib/utils';

interface Step { tool: string; blocked?: boolean; durationMs?: number }
interface Msg {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  pending?: boolean;
  /** What the agent is doing right now (while pending). */
  status?: string;
  steps?: Step[];
  error?: boolean;
  /** Reveal the text gradually the first time it is shown. */
  fresh?: boolean;
}

const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);
const toolName = (t: string) => t.replace(/_/g, ' ');

/** Suggestions change with the page the user is on. */
function suggestionsFor(path: string): string[] {
  if (path.startsWith('/ai-stack/data-plane')) return ['Which source systems feed the Customer entity?', 'Which entities are still unmapped?', 'Show the mapping rule for AR invoices'];
  if (path.startsWith('/ai-stack/control-plane')) return ['Which policies apply to credit limit changes?', 'What depends on the Account entity?', 'Which workflows need approval?'];
  if (path.startsWith('/apps') || path.startsWith('/workspace/apps')) return ['Why is DSO above target?', 'Which orders have a quantity mismatch?', 'What should I act on first today?'];
  if (path.startsWith('/operations')) return ['Are any connectors unhealthy right now?', 'Which jobs failed in the last day?', 'Summarise the latest diagnostics run'];
  if (path.startsWith('/ai-analytics') || path.startsWith('/dashboard')) return ['Which suppliers carry the highest risk?', 'Which SKUs are below their reorder point?', 'Where is spend off contract?'];
  return ['What can I ask you?', 'Which SKUs are below their reorder point?', 'What are the approval steps for a credit limit change?'];
}

/** Types text out a few characters per frame. Skipped for reduced motion. */
function Reveal({ text, onDone }: { text: string; onDone: () => void }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) { setN(text.length); onDone(); return; }
    let i = 0;
    const stepSize = Math.max(2, Math.ceil(text.length / 90));
    const t = window.setInterval(() => {
      i = Math.min(text.length, i + stepSize);
      setN(i);
      if (i >= text.length) { window.clearInterval(t); onDone(); }
    }, 16);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);
  return <Markdown>{text.slice(0, n)}</Markdown>;
}

const MD =
  'text-sm leading-relaxed text-foreground [&_p]:mb-2.5 [&_p:last-child]:mb-0 [&_strong]:font-medium ' +
  '[&_ul]:mb-2.5 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_ol]:mb-2.5 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 ' +
  '[&_code]:rounded [&_code]:bg-surface-2 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs ' +
  '[&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 dark:[&_a]:text-brand-hi [&_h1]:mb-2 [&_h1]:font-medium [&_h2]:mb-2 [&_h2]:font-medium [&_h3]:mb-1.5 [&_h3]:font-medium';

function Markdown({ children }: { children: string }) {
  return <div className={MD}><ReactMarkdown>{children}</ReactMarkdown></div>;
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      {[0, 1, 2].map(i => (
        <span key={i} className="h-1.5 w-1.5 rounded-full bg-primary dark:bg-brand-hi" style={{ animation: 'typing-dot 1.1s ease-in-out infinite', animationDelay: `${i * 140}ms` }} />
      ))}
    </span>
  );
}

function StepsLine({ steps }: { steps: Step[] }) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0) return null;
  const blocked = steps.filter(s => s.blocked).length;
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-md text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Icon name="route" className="h-3 w-3" />
        Used {steps.length} {steps.length === 1 ? 'tool' : 'tools'}{blocked > 0 && <span className="text-warning">, {blocked} blocked by policy</span>}
        <Icon name="chevron-down" className={cn('h-3 w-3 transition-transform duration-200', open && 'rotate-180')} />
      </button>
      {open && (
        <ol className="mt-2 space-y-1.5 border-l border-border pl-3">
          {steps.map((s, i) => (
            <li key={i} className="rise flex items-center gap-2 text-xs" style={{ ['--i' as any]: i }}>
              <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', s.blocked ? 'bg-warning' : 'bg-success')} aria-hidden="true" />
              <span className="font-mono text-foreground">{s.tool}</span>
              <span className="text-muted-foreground">{s.blocked ? 'blocked by policy' : s.durationMs ? `${(s.durationMs / 1000).toFixed(1)} s` : 'done'}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function AssistantDock({ userName }: { userName?: string }) {
  const loc = useLocation();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const patch = useCallback((id: string, p: Partial<Msg>) => setMessages(prev => prev.map(m => (m.id === id ? { ...m, ...p } : m))), []);

  // Keep the newest message in view.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages, open]);

  // Focus the composer when the panel opens; Escape closes; Ctrl/Cmd + J toggles.
  useEffect(() => {
    if (open) window.setTimeout(() => inputRef.current?.focus(), 180);
  }, [open]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') { e.preventDefault(); setOpen(o => !o); }
      else if (e.key === 'Escape' && open) setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // Grow the composer with its content.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = '0px';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [input, open]);

  const send = async (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || busy) return;
    setInput('');
    const botId = uid();
    setMessages(prev => [...prev, { id: uid(), role: 'user', text: question }, { id: botId, role: 'assistant', text: '', pending: true, status: 'Thinking', steps: [] }]);
    setBusy(true);
    const steps: Step[] = [];
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const resp = await fetch('/api/v1/control-plane/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        credentials: 'include',
        body: JSON.stringify({ question, max_steps: 10 }),
        signal: ctrl.signal,
      });
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let answered = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let evt: any;
          try { evt = JSON.parse(line.slice(6)); } catch { continue; }
          if (evt.type === 'status' && evt.message) patch(botId, { status: evt.message });
          else if (evt.type === 'tool_call' && evt.tool) patch(botId, { status: `Running ${toolName(evt.tool)}` });
          else if (evt.type === 'tool_result' && evt.tool) { steps.push({ tool: evt.tool, durationMs: evt.duration_ms }); patch(botId, { steps: [...steps] }); }
          else if (evt.type === 'tool_blocked' && evt.tool) { steps.push({ tool: evt.tool, blocked: true }); patch(botId, { steps: [...steps] }); }
          else if ((evt.type === 'answer' || evt.type === 'cache_hit') && evt.data) {
            answered = true;
            patch(botId, { text: String(evt.data.answer || ''), pending: false, fresh: true, steps: [...steps] });
          } else if (evt.type === 'error') {
            answered = true;
            patch(botId, { text: evt.message || 'The assistant could not answer that.', pending: false, error: true });
          }
        }
      }
      if (!answered) patch(botId, { text: 'No answer came back. Please try again.', pending: false, error: true });
    } catch (err: any) {
      if (err?.name === 'AbortError') patch(botId, { text: 'Stopped.', pending: false });
      else patch(botId, { text: 'The assistant is not reachable right now. Check the connection and try again.', pending: false, error: true });
    } finally {
      setBusy(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  };

  const stop = () => abortRef.current?.abort();
  const reset = () => { stop(); setMessages([]); setInput(''); inputRef.current?.focus(); };
  const openCopilot = () => { setOpen(false); nav('/ai-stack/reasoning'); };

  const first = (userName || '').trim().split(/\s+/)[0];
  const suggestions = suggestionsFor(loc.pathname);
  const iconBtn = 'flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

  return (
    <>
      {/* Launcher */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open the Nexus assistant"
        aria-expanded={open}
        title="Ask Nexus (Ctrl + J)"
        className={cn(
          'group fixed bottom-[76px] right-4 z-40 flex h-12 items-center gap-2.5 rounded-full border border-border-strong bg-card pl-3 pr-4 text-sm font-medium text-foreground shadow-lg md:bottom-6 md:right-6',
          'transition-all duration-300 ease-brand-out hover:-translate-y-0.5 hover:border-brand/60 hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          open ? 'pointer-events-none translate-y-3 scale-90 opacity-0' : 'opacity-100',
        )}
      >
        <span className="relative flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <LogoMark className="h-4 w-4" />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border-2 border-card bg-success" aria-hidden="true" />
        </span>
        <span>Ask Nexus</span>
      </button>

      {/* Panel */}
      <div
        role="dialog"
        aria-label="Nexus assistant"
        aria-hidden={!open}
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 flex h-[min(82dvh,640px)] origin-bottom flex-col overflow-hidden rounded-t-2xl border border-border-strong bg-popover text-popover-foreground shadow-xl',
          'md:inset-x-auto md:bottom-6 md:right-6 md:h-[min(640px,calc(100dvh-96px))] md:w-[420px] md:origin-bottom-right md:rounded-2xl',
          'transition-[opacity,transform] duration-300 ease-brand-out',
          open ? 'translate-y-0 scale-100 opacity-100' : 'pointer-events-none invisible translate-y-4 scale-95 opacity-0',
        )}
      >
        <header className="flex shrink-0 items-center gap-3 border-b border-border px-4 py-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <LogoMark className="h-[18px] w-[18px]" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-medium text-foreground">Nexus assistant</h2>
            <p className="flex items-center gap-1.5 truncate text-xs text-muted-foreground">
              <span className="dot-live text-success" aria-hidden="true" />
              Answers from your governed data
            </p>
          </div>
          {messages.length > 0 && (
            <button type="button" onClick={reset} className={iconBtn} aria-label="Start a new chat" title="New chat">
              <Icon name="edit" className="h-4 w-4" />
            </button>
          )}
          <button type="button" onClick={openCopilot} className={iconBtn} aria-label="Open the full Copilot" title="Open the full Copilot">
            <Icon name="expand" className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => setOpen(false)} className={iconBtn} aria-label="Close the assistant" title="Close (Esc)">
            <Icon name="chevron-down" className="h-4 w-4" />
          </button>
        </header>

        <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-4" aria-live="polite">
          {messages.length === 0 ? (
            <div className="flex min-h-full flex-col justify-end">
              <h3 className="text-xl font-medium tracking-tight text-foreground">{first ? `Hello ${first}.` : 'Hello.'}</h3>
              <p className="mt-1 text-sm text-muted-foreground">Ask about your data, policies and workflows. I show the steps I take to answer.</p>
              <div className="mt-5 space-y-2">
                {suggestions.map((q, i) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => send(q)}
                    style={{ ['--i' as any]: i }}
                    className="rise group flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-card px-3.5 py-2.5 text-left text-sm text-foreground transition-all duration-200 hover:border-brand/50 hover:bg-surface-2"
                  >
                    <span>{q}</span>
                    <Icon name="arrow-up-right" className="h-3.5 w-3.5 shrink-0 text-subtle-foreground transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <ul className="space-y-5">
              {messages.map(m => (
                <li key={m.id} className={cn('flex animate-fade-up', m.role === 'user' ? 'justify-end' : 'justify-start')}>
                  {m.role === 'user' ? (
                    <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-3.5 py-2 text-sm text-primary-foreground">{m.text}</p>
                  ) : (
                    <div className="min-w-0 max-w-full flex-1">
                      {m.pending ? (
                        <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
                          <TypingDots />
                          <span key={m.status} className="animate-fade-in">{m.status}</span>
                        </div>
                      ) : m.error ? (
                        <p className="flex items-start gap-2 text-sm text-foreground">
                          <Icon name="alert-triangle" className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                          <span>{m.text}</span>
                        </p>
                      ) : m.fresh ? (
                        <Reveal text={m.text} onDone={() => patch(m.id, { fresh: false })} />
                      ) : (
                        <Markdown>{m.text}</Markdown>
                      )}
                      {!m.pending && !m.fresh && m.steps && <StepsLine steps={m.steps} />}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <form
          className="shrink-0 border-t border-border p-3"
          onSubmit={(e) => { e.preventDefault(); send(); }}
        >
          <div className="flex items-end gap-2 rounded-xl border border-border-strong bg-background px-3 py-2 transition-colors focus-within:border-brand focus-within:ring-2 focus-within:ring-ring/30">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Ask about your data"
              aria-label="Message the assistant"
              className="scroll-thin max-h-[120px] min-h-[24px] flex-1 resize-none bg-transparent py-0.5 text-sm text-foreground placeholder:text-subtle-foreground focus:outline-none"
            />
            {busy ? (
              <button type="button" onClick={stop} aria-label="Stop" title="Stop" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-3 text-foreground transition-colors hover:bg-accent">
                <span className="h-2.5 w-2.5 rounded-[2px] bg-current" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                aria-label="Send"
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all duration-200 hover:scale-105 active:scale-95 disabled:scale-100 disabled:bg-surface-3 disabled:text-subtle-foreground"
              >
                <Icon name="send" className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          <p className="mt-1.5 px-1 text-xs text-subtle-foreground">Enter to send, Shift + Enter for a new line</p>
        </form>
      </div>
    </>
  );
}

export default AssistantDock;
