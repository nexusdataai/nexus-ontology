import React, { useState } from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send } from 'lucide-react';

const ChatbotEditorPage: React.FC = () => {
  const [message, setMessage] = useState('');

  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen flex flex-col">
        <div className="mb-6">
          <h1 className="text-lg font-semibold">Chatbot Editor</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Test AI assistant interactions with configured agent instructions
          </p>
        </div>

        <Card className="flex-1 flex flex-col border-border bg-card/50 min-h-[500px]">
          <CardHeader className="shrink-0">
            <CardTitle className="text-base">Chat</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col p-0 min-h-0">
            <div className="flex-1 overflow-auto p-6 space-y-4">
              <div className="flex gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0 text-sm font-medium">
                  AI
                </div>
                <div className="rounded-lg bg-muted/30 border border-border px-4 py-3 max-w-[80%]">
                  <p className="text-sm">Welcome! I'm your enterprise AI assistant. Ask me anything about your data, workflows, or knowledge base.</p>
                </div>
              </div>
            </div>
            <div className="p-4 border-t border-border flex gap-2">
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type your message..."
                className="flex-1 border-border"
              />
              <Button size="icon" className="shrink-0">
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default ChatbotEditorPage;
