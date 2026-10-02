import { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Send, Loader2, Sparkles, User } from 'lucide-react';
import { apiClient } from '@/services/apiClient';
import type { AppConfig } from '@/config/appRegistry';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Props { app: AppConfig; }

export function AppChat({ app }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const suggestions = [
    `What are the key ${app.useCase} KPIs?`,
    `Which entities are involved in ${app.name}?`,
    `What policies govern ${app.useCase}?`,
    `Show me the workflow for ${app.useCase}`,
  ];

  const send = async (text?: string) => {
    const q = text || input.trim();
    if (!q) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);

    try {
      const contextPrefix = `[Context: ${app.name} app, use case: ${app.useCase}, entities: ${app.entities.join(', ')}] `;
      const data = await apiClient.post('/api/v1/control-plane/agent', {
        question: contextPrefix + q, max_steps: 5,
      }, { timeout: 120000 }) as any;

      setMessages(prev => [...prev, { role: 'assistant', content: data.answer || 'No response' }]);
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-bold">AI Assistant</h2>
        <Badge variant="outline" className="text-[9px]">{app.shortName} scoped</Badge>
      </div>

      <Card className="flex-1 flex flex-col min-h-0">
        <CardContent className="flex-1 min-h-0 flex flex-col p-3">
          <ScrollArea className="flex-1">
            <div className="space-y-3 pr-2">
              {messages.length === 0 && (
                <div className="text-center py-8">
                  <Sparkles className="h-8 w-8 mx-auto mb-3 opacity-20" />
                  <p className="text-sm text-muted-foreground mb-4">Ask about {app.name}</p>
                  <div className="grid grid-cols-2 gap-2 max-w-md mx-auto">
                    {suggestions.map(s => (
                      <button key={s} onClick={() => send(s)}
                        className="text-xs text-left p-2 rounded border hover:bg-muted/30 transition-colors text-muted-foreground hover:text-foreground">
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && <Sparkles className="h-5 w-5 text-primary shrink-0 mt-1" />}
                  <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'
                  }`}>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  {msg.role === 'user' && <User className="h-5 w-5 text-muted-foreground shrink-0 mt-1" />}
                </div>
              ))}
              {loading && (
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  <div className="bg-muted rounded-lg px-3 py-2"><Loader2 className="h-4 w-4 animate-spin" /></div>
                </div>
              )}
              <div ref={scrollRef} />
            </div>
          </ScrollArea>

          <div className="flex gap-2 mt-3 pt-3 border-t">
            <Input value={input} onChange={e => setInput(e.target.value)} placeholder={`Ask about ${app.shortName}...`}
              onKeyDown={e => e.key === 'Enter' && send()} className="text-sm" disabled={loading} />
            <Button size="sm" onClick={() => send()} disabled={loading || !input.trim()}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
