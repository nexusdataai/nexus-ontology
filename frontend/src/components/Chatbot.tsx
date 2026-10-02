import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Bot, User, Send, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { chatbotService, ChatMessage } from '@/services/chatbotService';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatbotProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (tab: string) => void;
}

export default function Chatbot({ isOpen, onClose, onNavigate }: ChatbotProps) {
  const CHAT_DISABLED = true;
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: CHAT_DISABLED
        ? "This chat assistant is currently under development and will be available in a future release. Stay tuned!"
        : "Hey! 👋 I'm your AI assistant. I can help you navigate the app, explore schemas, view analytics, and more. What would you like to do?",
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

    } catch (error) {
      console.error('Chatbot error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "Oops! 😅 I ran into an issue. Could you check your OpenAI API key? If that's good, try again!",
        sender: 'assistant',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNavigationAction = async (action: any) => {
    try {
      switch (action.type) {
        case 'navigate':
          if (action.target === '/') {
            navigate('/');
          } else {
            // Only support navigation to main dashboard
            console.log('Unknown route requested:', action.target);
            navigate('/');
          }
          break;
        
        case 'querySelect':
          // Handle dashboard section selection
          if (action.target && onNavigate) {
            // Navigate to home first if not already there
            if (window.location.pathname !== '/') {
              navigate('/');
              // Wait a bit for navigation to complete before triggering query selection
              setTimeout(() => onNavigate(action.target), 200);
            } else {
              onNavigate(action.target);
            }
          }
          break;
        
        case 'discover':
        case 'show':
        default:
          // All other actions redirect to main dashboard
          navigate('/');
          break;
      }
    } catch (error) {
      console.error('Navigation action error:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="flex flex-col h-full bg-card">
      {/* Messages Container - Scrollable but no visible scrollbar */}
      <div 
        ref={messagesContainerRef}
        className="flex-1 p-4 overflow-y-auto scrollbar-hide"
        style={{ 
          maxHeight: 'calc(100vh - 280px)',
          scrollbarWidth: 'none', /* Firefox */
          msOverflowStyle: 'none' /* Internet Explorer 10+ */
        }}
      >
        <div className="space-y-3">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-2",
                message.sender === 'user' ? "justify-end" : "justify-start"
              )}
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
                    : "bg-muted text-foreground border border-border"
                )}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                <p className="text-xs opacity-70 mt-1">
                  {message.timestamp.toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
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
            <div className="flex gap-2 justify-start">
              <div className="flex-shrink-0 w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                <Bot className="h-3 w-3 text-primary" />
              </div>
              <div className="bg-muted border border-border p-3 rounded-lg">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">AI assistant is thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input - Fixed at bottom */}
      <div className="px-4 absolute bottom-3 left-0 right-0 pb-4 border-t border-border flex-shrink-0 bg-card">
        <div className="flex gap-2 pt-3">
          <Input
            value={inputValue}
            onChange={(e) => !CHAT_DISABLED && setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={CHAT_DISABLED ? "Chat coming soon..." : "What would you like to explore today?"}
            disabled={isLoading || CHAT_DISABLED}
            className="flex-1 text-sm h-10 bg-background border-border focus:border-primary"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading || CHAT_DISABLED}
            size="sm"
            className="h-10 w-10 p-0 bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            <Send className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
} 