import React, { createContext, useContext, useState, useRef, ReactNode, useEffect } from 'react';

interface ChatMessage {
  id: string;
  isUser: boolean;
  text: string;
  timestamp: Date;
  containsChartData?: boolean;
}

interface ChatContextType {
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  lastProcessedResponseId: React.MutableRefObject<string | null>;
  lastNavigatedRoute: React.MutableRefObject<string | null>;
  resetChat: () => void;
  updateProfileName: (name: string) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

interface ChatProviderProps {
  children: ReactNode;
  profileName?: string;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children, profileName }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      isUser: false,
      text: `Welcome ${profileName || 'to Nexus AI'}! How can I help you today?`,
      timestamp: new Date(),
      containsChartData: false,
    }
  ]);
  
  const lastProcessedResponseId = useRef<string | null>(null);
  const lastNavigatedRoute = useRef<string | null>(null);

  // Update welcome message when profile name changes
  useEffect(() => {
    if (profileName) {
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        // Update only the welcome message
        if (updatedMessages[0] && !updatedMessages[0].isUser) {
          updatedMessages[0] = {
            ...updatedMessages[0],
            text: `Welcome ${profileName}! How can I help you today?`,
          };
        }
        return updatedMessages;
      });
    }
  }, [profileName]);

  const resetChat = () => {
    setMessages([
      {
        id: Date.now().toString(),
        isUser: false,
        text: `Welcome ${profileName || 'to Nexus AI'}! How can I help you today?`,
        timestamp: new Date(),
        containsChartData: false,
      }
    ]);
    lastProcessedResponseId.current = null;
    lastNavigatedRoute.current = null;
  };

  const updateProfileName = (name: string) => {
    setMessages(prevMessages => {
      const updatedMessages = [...prevMessages];
      // Update only the welcome message
      if (updatedMessages[0] && !updatedMessages[0].isUser) {
        updatedMessages[0] = {
          ...updatedMessages[0],
          text: `Welcome ${name}! How can I help you today?`,
        };
      }
      return updatedMessages;
    });
  };

  const value = {
    messages,
    setMessages,
    lastProcessedResponseId,
    lastNavigatedRoute,
    resetChat,
    updateProfileName,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}; 