/**
 * Chatbot Editor Component
 * 
 * Provides a chat interface for testing AI assistant interactions.
 * Allows sending messages, viewing responses, and testing navigation actions.
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Bot, User, Send, Loader2, MessageCircle, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { chatbotService } from '@/services/chatbotService';
import { toast } from 'sonner';

export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatbotEditorProps {
  onNavigate?: (tab: string) => void;
}

/**
 * Format timestamp for display
 */
export function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
}

/**
 * Count messages by sender type
 */
export function countMessagesBySender(messages: Message[], sender: 'user' | 'assistant'): number {
  return messages.filter(m => m.sender === sender).length;
}

export default function ChatbotEditor({ onNavigate }: ChatbotEditorProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: "Hey! 👋 I'm your AI assistant. I can help you navigate the app, explore schemas, view analytics, and more. What would you like to do?",
      sender: 'assistant',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue.trim(),
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Get current context including path and any URL parameters
      const context = {
        currentPath: location.pathname,
        currentSearch: location.search,
        timestamp: new Date().toISOString(),
        availableSchemas: [
          'Product Catalog Management',
          'Customer Management', 
          'Order Management',
          'Billing Management',
          'Service Catalog Management'
        ]
      };

      const response = await chatbotService.sendMessage(userMessage.content, context);
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.message,
        sender: 'assistant',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, assistantMessage]);

      // Handle navigation action if present
      if (response.action) {
        await handleNavigationAction(response.action);
      }

      toast.success('Message sent successfully');

    } catch (error) {
      console.error('Chatbot error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "Oops! 😅 I ran into an issue. Could you check your OpenAI API key? If that's good, try again!",
        sender: 'assistant',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      toast.error('Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  interface NavigationAction {
    type: string;
    target?: string;
    data?: Record<string, unknown>;
  }

  const handleNavigationAction = async (action: NavigationAction) => {
    try {
      console.log('Handling navigation action:', action);
      
      if (action.type === 'navigate' && action.target) {
        console.log(`Navigating to: ${action.target}`);
        
        // Handle different navigation targets
        if (onNavigate && ['interactive', 'hierarchical', 'mapping', 'analysis'].includes(action.target)) {
          onNavigate(action.target);
        } else {
          // Direct navigation
          navigate(action.target);
        }
      } else if (action.type === 'querySelect' && action.target && onNavigate) {
        // Handle dashboard section selection
        if (window.location.pathname !== '/') {
          navigate('/');
          setTimeout(() => onNavigate(action.target!), 200);
        } else {
          onNavigate(action.target);
        }
      }
    } catch (error) {
      console.error('Navigation action failed:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: '1',
        content: "Hey! 👋 I'm your AI assistant. I can help you navigate the app, explore schemas, view analytics, and more. What would you like to do?",
        sender: 'assistant',
        timestamp: new Date()
      }
    ]);
    toast.success('Chat cleared');
  };

  const messageCount = messages.length;
  const userMessageCount = countMessagesBySender(messages, 'user');

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MessageCircle className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Chatbot Editor</h1>
            <p className="text-muted-foreground">Test your AI assistant with MCP tool integration</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-sm" data-testid="message-count-badge">
            <MessageCircle className="h-3 w-3 mr-1" />
            <span data-testid="total-count">{messageCount}</span> messages (<span data-testid="user-count">{userMessageCount}</span> user)
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={clearChat}
            data-testid="clear-chat-button"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Clear Chat
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                AI Assistant Test Interface
              </CardTitle>
              <CardDescription>
                Chat with your AI assistant to test functionality, MCP tools, and navigation capabilities.
                This uses the same chatbotService as the Agent Instructions Editor.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="space-y-4">
            {/* Messages Container */}
            <div 
              ref={messagesContainerRef}
              className="h-[500px] p-4 border rounded-lg overflow-y-auto bg-muted/30"
              style={{ 
                scrollbarWidth: 'thin',
                scrollbarColor: 'rgba(155, 155, 155, 0.5) transparent'
              }}
              data-testid="messages-container"
            >
              <div className="space-y-3">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex gap-2",
                      message.sender === 'user' ? "justify-end" : "justify-start"
                    )}
                    data-testid={`message-${message.id}`}
                    data-sender={message.sender}
                  >
                    {message.sender === 'assistant' && (
                      <div className="flex-shrink-0 w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                        <Bot className="h-3 w-3 text-primary" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "max-w-[85%] p-3 rounded-lg text-sm",
                        message.sender === 'user'
                          ? "bg-primary text-primary-foreground"
                          : "bg-background text-foreground border border-border"
                      )}
                    >
                      <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                      <p className="text-xs opacity-70 mt-1" data-testid={`timestamp-${message.id}`}>
                        {formatTimestamp(message.timestamp)}
                      </p>
                    </div>
                    {message.sender === 'user' && (
                      <div className="flex-shrink-0 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                        <User className="h-3 w-3 text-primary-foreground" />
                      </div>
                    )}
                  </div>
                ))}
                
                {isLoading && (
                  <div className="flex gap-2 justify-start" data-testid="loading-indicator">
                    <div className="flex-shrink-0 w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                      <Bot className="h-3 w-3 text-primary" />
                    </div>
                    <div className="bg-background border border-border rounded-lg p-3 text-sm">
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span className="text-muted-foreground">Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* Input Area */}
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message here... (Press Enter to send)"
                disabled={isLoading}
                className="flex-1"
                data-testid="message-input"
              />
              <Button 
                onClick={handleSendMessage} 
                disabled={isLoading || !inputValue.trim()}
                size="icon"
                data-testid="send-button"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <div className="flex items-center gap-4">
                <span>🤖 OpenAI GPT-4 powered</span>
                <span>🔧 MCP tools enabled</span>
                <span>🧭 Navigation support</span>
              </div>
              
              <div className="text-xs">
                Uses: <code>chatbotService.ts</code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-success/25 bg-success/50 dark:border-success/25 dark:bg-success/20">
        <CardHeader>
          <CardTitle className="text-lg text-success dark:text-success">
            💡 Testing Tips
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2 text-success dark:text-success">
          <div>• <strong>Navigation:</strong> "Show me the Interactive Graph" or "Take me to analytics"</div>
          <div>• <strong>MCP Tools:</strong> "How is site CZA0021 performing?" or "Compare network sites"</div>
          <div>• <strong>Context:</strong> The assistant knows your current page and can provide relevant help</div>
          <div>• <strong>Debugging:</strong> Check console for detailed logs and error messages</div>
        </CardContent>
      </Card>
    </div>
  );
}
