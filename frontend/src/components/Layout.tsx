import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import UserMenu from './UserMenu';
import Chatbot from './Chatbot';
import { MessageSquare, Search, Bell, RefreshCw, X, Sun, Moon } from 'lucide-react';
import { useTheme } from '@/hooks/use-theme';
import { RefreshProvider } from '@/context/RefreshContext';

const TITLES: Record<string, string> = {
  '/': 'NexusAI Platform',
  '/ai-stack/data-plane': 'Data Plane',
  '/ai-stack/control-plane': 'Control Plane',
  '/ai-stack/reasoning': 'Reasoning',
  '/workspace/apps': 'Solutions',
  '/workspace/automation': 'AI Automation',
  '/workspace/tools': 'Tools Catalogue',
  '/workspace/ai-workspace': 'AI Workspace',
  '/operations/diagnostics': 'Diagnostics',
  '/operations/health': 'Health',
  '/settings': 'Settings',
  '/ai-analytics': 'AI Analytics',
  '/dashboards': 'AI Analytics',
  '/dashboard/builder': 'Dashboard Builder',
  '/dashboard/view': 'Dashboard',
  '/views': 'AI Analytics',
  '/views/builder': 'View Builder',
};

interface LayoutProps { children: React.ReactNode; }

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const loc = useLocation();
  const [chatOpen, setChatOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  const title = TITLES[loc.pathname] || Object.entries(TITLES).find(([k]) => k !== '/' && loc.pathname.startsWith(k))?.[1] || 'NexusAI Platform';

  return (
    <RefreshProvider>
      <div className="min-h-screen h-screen flex overflow-hidden bg-background text-foreground">
        <Sidebar />

        <div className="flex-1 flex flex-col overflow-hidden">
          <header className="flex items-center justify-between px-5 h-12 shrink-0 border-b border-border bg-card">
            <div className="flex items-center gap-3">
              <h1 className="text-[15px] font-semibold">{title}</h1>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={toggleTheme} title="Toggle theme"
                className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
              <button className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                <Search className="h-4 w-4" />
              </button>
              <button className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors relative">
                <Bell className="h-4 w-4" />
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500" />
              </button>
              <button className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                <RefreshCw className="h-4 w-4" />
              </button>
              <UserMenu />
            </div>
          </header>

          <main className="flex-1 overflow-auto relative">
            {children}

            {!chatOpen && (
              <button onClick={() => setChatOpen(true)}
                className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/25 flex items-center justify-center hover:scale-105 transition-transform">
                <MessageSquare className="h-5 w-5" />
              </button>
            )}
            {chatOpen && (
              <div className="fixed bottom-6 right-6 z-50 w-96 h-[500px] rounded-xl shadow-2xl flex flex-col overflow-hidden border border-border bg-card">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                  <h3 className="text-sm font-semibold">AI Assistant</h3>
                  <button onClick={() => setChatOpen(false)} className="text-muted-foreground hover:text-foreground">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="flex-1 overflow-hidden">
                  <Chatbot isOpen onClose={() => setChatOpen(false)} onNavigate={() => {}} />
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </RefreshProvider>
  );
};

export default Layout;
